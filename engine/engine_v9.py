"""
Kaggriculture v9.0 — 라이브 엔진 프로토타입 (2026-09-04, 미완)
================================================================
대본 재생이 아니라 매 스텝 관측을 보고 판단하는 에이전트.
매크로 계획은 13계열 공개 대본(솔로 146k)의 일정(고용·동물·작물·토지)을 본뜨고,
실행은 구역 배정(동물 담당 ≤3마리/유닛 + 작물 담당 스네이크 구역) + 타일별 작업 큐로 한다.
수요 규칙(Crop Dusta): 상점 공개 후 소/양/거위/딸기/토마토 목표 수정, 헐값 산물 급식 중단.

현재 수준 (2026-09-04): 솔로 평균 116k (16시드; 대본 146k) / 경쟁 vs v8.16 0/4 −45k.
미해결: 노동 효율(대본 대비 딸기·밀 산출 60~70%), 판매 시점(상대보다 늦게 팔아 가격 붕괴 후 매도),
초반 현금 흐름(딸기 파종이 대본보다 2~3일 늦음). 제출 금지 — 개발용.
도구: bench9.py(일별 요약) trace9.py(스텝 추적) solo.py(다시드 솔로) t13_agent.py(13대본 솔로 기준).
"""
import math

# ── 상수 ────────────────────────────────────────────────────────────────
CROPS = {
    "WHEAT": {"seed": 10, "first": 2, "maxday": 4, "ongoing": False, "max": 6},
    "CARROT": {"seed": 20, "first": 2, "maxday": 3, "ongoing": False, "max": 4},
    "TOMATO": {"seed": 50, "first": 8, "maxday": 8, "ongoing": True, "max": 4, "interval": 1},
    "STRAWBERRY": {"seed": 100, "first": 10, "maxday": 10, "ongoing": True, "max": 4, "interval": 2},
    "MELON": {"seed": 80, "first": 10, "maxday": 12, "ongoing": False, "max": 6},
}
ANIMALS = {"GOOSE": ("COOP", 300, "EGG"), "COW": ("PASTURE", 400, "MILK"), "SHEEP": ("PASTURE", 500, "WOOL")}
PRODUCTS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER"]
BASE = {"WHEAT": 25, "CARROT": 35, "TOMATO": 60, "STRAWBERRY": 120, "MELON": 250, "EGG": 50, "MILK": 160, "WOOL": 200, "FERTILIZER": 100}
SHOPS = {
    "BAKERY": ["EGG", "WHEAT"], "PIZZA_SHOP": ["MILK", "TOMATO", "WHEAT"], "BRUNCH_SPOT": ["EGG", "WHEAT", "STRAWBERRY"],
    "YARN_STORE": ["WOOL"], "ICE_CREAM_SHOP": ["STRAWBERRY", "MILK", "WHEAT"], "PET_CAFE": ["CARROT"],
    "SMOOTHIE_SHOP": ["STRAWBERRY", "MILK"], "FARMERS_MARKET": ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY"],
}
LAND_ORDER = ["NE", "SW", "SE"]
LAND_PRICES = [1000, 2000, 4000]
N = 10
SHED_TILES = [(4, 4), (5, 4), (4, 5), (5, 5)]


def fib(n):
    a, b = 1, 1
    for _ in range(n):
        a, b = b, a + b
    return a


def quadrant(x, y):
    return ("N" if y < 5 else "S") + ("W" if x < 5 else "E")


def dist(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def step_toward(pos, target):
    x, y = pos
    tx, ty = target
    if abs(tx - x) >= abs(ty - y):
        if tx > x: return ["EAST"]
        if tx < x: return ["WEST"]
    if ty > y: return ["SOUTH"]
    if ty < y: return ["NORTH"]
    if tx > x: return ["EAST"]
    if tx < x: return ["WEST"]
    return ["PASS"]


# ── 매크로 계획 (13계열 대본 모방) ─────────────────────────────────────────
# 일자별 목표 동물 수 (누적)
COW_TARGET = {0: 2, 2: 3, 3: 4, 6: 6, 7: 8, 8: 9}
SHEEP_TARGET = {0: 2, 8: 4, 9: 6, 10: 8, 11: 9}
HANDS_TARGET = {0: 5, 1: 4, 2: 4, 3: 5, 4: 4, 5: 5, 6: 8, 7: 8, 8: 10, 9: 9, 10: 11, 11: 11, 12: 9, 13: 10, 14: 10, 15: 11, 16: 12}
LAND_DAY = {"NE": 6, "SW": 11}
STRAW_TARGET = {5: 4, 6: 12, 7: 16, 8: 20, 9: 24, 11: 37}
MELON_D0 = 12
WHEAT_TILES_TARGET = {0: 7, 2: 10, 4: 13, 6: 16, 8: 18, 11: 28, 12: 34}


def target_at(table, day):
    v = 0
    for d in sorted(table):
        if d <= day: v = table[d]
    return v


class State:
    pass


_S = {0: None, 1: None}


def _get(o, k, d=None):
    if isinstance(o, dict): return o.get(k, d)
    g = getattr(o, "get", None)
    return g(k, d) if callable(g) else getattr(o, k, d)


# ── 농장 파싱 ─────────────────────────────────────────────────────────────
def parse(obs):
    seat = int(_get(obs, "player", 0) or 0)
    farm = _get(obs, "farms")[seat]
    tiles = _get(farm, "tiles")
    priv = _get(obs, "private", {}) or {}
    s = State()
    s.seat = seat
    s.step = int(_get(obs, "step", 0) or 0)
    s.day = s.step // 24
    s.hour = s.step % 24
    s.money = int(_get(farm, "money", 0) or 0)
    s.tiles = tiles
    s.all_farms = [dict(f) if isinstance(f, dict) else {"tiles": _get(f, "tiles")} for f in _get(obs, "farms")]
    s.unlocked = list(_get(farm, "unlocked_quadrants", []) or [])
    s.positions = [tuple(_get(farm, "farmer"))] + [tuple(p) for p in (_get(farm, "hands", []) or [])]
    s.invs = [dict(i or {}) for i in (_get(priv, "inventories", []) or [])]
    while len(s.invs) < len(s.positions): s.invs.append({})
    s.shed = {k: int(v or 0) for k, v in dict(_get(priv, "shed", {}) or {}).items()}
    s.seeds = {k: int(v or 0) for k, v in dict(_get(priv, "seeds", {}) or {}).items()}
    s.hires_today = int(_get(farm, "hires_today", 0) or 0)
    mk = _get(obs, "market", {}) or {}
    s.prices = {k: int(v) for k, v in dict(_get(mk, "prices", {}) or {}).items()}
    s.inv_mkt = {k: int(v) for k, v in dict(_get(mk, "inventory", {}) or {}).items()}
    s.shops = list(_get(_get(obs, "town", {}) or {}, "unlocked_shops", []) or [])
    # 타일 분류
    s.animal_tiles = []   # (x,y,tile)
    s.plant_tiles = []
    s.weed_tiles = []
    s.empty_tiles = []
    s.struct_empty = []   # 빈 목장/우리
    for y in range(N):
        for x in range(N):
            t = tiles[y][x]
            if t == "LOCKED": continue
            if t is None: s.empty_tiles.append((x, y)); continue
            k = t.get("kind")
            if k == "WEED": s.weed_tiles.append((x, y))
            elif k == "PLANT": s.plant_tiles.append((x, y, t))
            elif t.get("animal"): s.animal_tiles.append((x, y, t))
            else: s.struct_empty.append((x, y, t))
    s.n_animals = len(s.animal_tiles)
    s.cows = sum(1 for _, _, t in s.animal_tiles if t["animal"] == "COW")
    s.sheep = sum(1 for _, _, t in s.animal_tiles if t["animal"] == "SHEEP")
    s.geese = sum(1 for _, _, t in s.animal_tiles if t["animal"] == "GOOSE")
    return s


# ── 레이아웃: 목장 슬롯은 창고에 가까운 순, 작물은 바깥 ───────────────────────
def pasture_slots(s, need):
    """창고 중심에서 가까운 빈/구조물 타일 순으로 need개 반환 (이미 동물이 있는 타일 제외)."""
    cand = []
    for y in range(N):
        for x in range(N):
            t = s.tiles[y][x]
            if t == "LOCKED": continue
            if isinstance(t, dict) and (t.get("animal") or t.get("kind") == "WEED" or t.get("kind") == "PLANT"): continue
            cand.append((abs(x - 4.5) + abs(y - 4.5), x, y))
    cand.sort()
    return [(x, y) for _, x, y in cand[:need]]


# ── 수요/가격 기반 판단 (Crop Dusta 규칙) ─────────────────────────────────
CROP_CYCLE = {"WHEAT": (4, 5), "CARROT": (3, 4), "MELON": (6, 11), "TOMATO": (4, 12), "STRAWBERRY": (5, 17)}  # (units, days)


RATE = {"COW": ("MILK", 1.5), "SHEEP": ("WOOL", 1.33), "GOOSE": ("EGG", 2.0),
        "WHEAT": ("WHEAT", 0.8), "CARROT": ("CARROT", 0.75), "MELON": ("MELON", 0.55), "TOMATO": ("TOMATO", 0.36), "STRAWBERRY": ("STRAWBERRY", 0.3)}


def market_outlook(s):
    """상품별 기대가격. 수요(상점 소비/일)와 공급(양쪽 농장의 동물·작물 타일에서 추정)을 비교해
    공급 과잉이면 현재가를 D/S 비율로 깎는다. 프리미엄 상품은 과잉 시 바닥까지 가므로 더 세게."""
    dem = demand_counts(s)
    D = {p: 6 * dem.get(p, 0) + 1 for p in PRODUCTS}
    S = {p: 0.0 for p in PRODUCTS}
    for farm in s.all_farms:
        for row in farm.get("tiles", []):
            for t in row:
                if not isinstance(t, dict): continue
                key = t.get("animal") or t.get("crop")
                if key in RATE:
                    p, r = RATE[key]; S[p] += r
    out = {}
    for p in PRODUCTS:
        price = s.prices.get(p, BASE[p])
        if S[p] > D[p] and p != "FERTILIZER":
            ratio = D[p] / S[p]
            price = price * max(0.3, min(1.0, 0.5 + 0.5 * ratio))
        out[p] = price
    return out


def crop_values(s):
    """작물별 타일·일당 기대가치 = 산출×기대가/주기 − 씨앗/주기."""
    exp = market_outlook(s)
    v = {}
    for crop, (units, days) in CROP_CYCLE.items():
        price = exp.get(crop, BASE[crop])
        if crop == "WHEAT": price = max(price, 30)   # 급식 수요
        v[crop] = units * price / days - CROPS[crop]["seed"] / days
    return v


def feed_worth(s, animal):
    """동물 급식 가치: 산물 기대가×일산출 ≥ 밀값이면 급식."""
    price = market_outlook(s).get(ANIMALS[animal][2], 0)
    wheat = max(20, s.prices.get("WHEAT", 25))
    per_day = {"COW": 1.5, "SHEEP": 1.33, "GOOSE": 2.0}[animal]
    return price * per_day >= wheat * 1.1 or s.day < 8


def plan_targets(s, mem):
    """대본 기본 목표에 수요 수정치를 적용. (Crop Dusta 규칙: 상점 공개 후 동물·작물 구성 조정)"""
    day = s.day; dem = demand_counts(s)
    cow_t = target_at(COW_TARGET, day); sheep_t = target_at(SHEEP_TARGET, day); goose_t = 0
    straw_t = target_at(STRAW_TARGET, day); tomato_t = 0
    if day >= 6:
        milk_d = dem.get("MILK", 0); wool_d = dem.get("WOOL", 0); egg_d = dem.get("EGG", 0)
        straw_d = dem.get("STRAWBERRY", 0); tom_d = dem.get("TOMATO", 0)
        if milk_d == 0: cow_t = min(cow_t, 6)
        if wool_d == 0: sheep_t = min(sheep_t, 5)
        elif wool_d >= 4: sheep_t = max(sheep_t, min(12, sheep_t + 3))
        if egg_d >= 1: goose_t = 4 if egg_d < 3 else 6
        if straw_d == 0 and day >= 9: straw_t = min(straw_t, 24)
        elif straw_d >= 2: straw_t = max(straw_t, 44) if day >= 9 else straw_t
        if tom_d >= 2 and day <= 16: tomato_t = 10
        elif tom_d == 1 and day <= 14: tomato_t = 5
    return cow_t, sheep_t, goose_t, straw_t, tomato_t


def demand_counts(s):
    d = {}
    for sh in s.shops:
        prods = SHOPS.get(sh, [])
        mult = 2 if len(prods) == 1 else 1
        for p in prods: d[p] = d.get(p, 0) + mult
    return d


# ── 시장 (하루 시작) ─────────────────────────────────────────────────────
def daily_market(s, mem):
    orders = []
    day = s.day
    money = s.money
    # 1) 판매: 산물 전량, 비료는 필요분 남기고, 밀은 급식 예비분 남기고
    n_units_est = 1 + target_at(HANDS_TARGET, day)
    fert_need = sum(1 for _, _, t in s.plant_tiles if t["crop"] == "STRAWBERRY" and (day - t["planted_day"]) in (8, 9, 10, 12, 13, 14))
    fert_need += sum(1 for _, _, t in s.plant_tiles if t["crop"] == "WHEAT" and (day - t["planted_day"]) in (0, 1)) // 2
    fert_need = min(30, fert_need)
    for item in ("MILK", "WOOL", "STRAWBERRY", "MELON", "EGG", "CARROT", "TOMATO"):
        q = s.shed.get(item, 0)
        if q > 0: orders.append(["SELL", item, q])
    fq = s.shed.get("FERTILIZER", 0) - fert_need
    if fq > 0: orders.append(["SELL", "FERTILIZER", fq])
    wheat_reserve = s.n_animals * 2 + 2
    wq = s.shed.get("WHEAT", 0) - wheat_reserve
    if day >= 29: wq = s.shed.get("WHEAT", 0)
    if wq > 0 and day >= 1: orders.append(["SELL", "WHEAT", wq])
    # 예상 수입(보수적) → 현금
    est = 0
    for o in orders:
        est += int(s.prices.get(o[1], 1) * o[2] * 0.7)
    cash = money + est
    if day >= 29:
        cash = money
        n = 0
        while n < 8 and cash >= fib(n):
            cash -= fib(n); orders.append(["HIRE"]); n += 1
        h0 = orders[:10]; mem["h1_orders"] = orders[10:20]
        return h0
    # 2) 밀 구매: 오늘 급식 부족분
    have = max(0, s.shed.get("WHEAT", 0) - (wq if wq > 0 else 0))
    need_wheat = int(s.n_animals * 1.2) + 2 - have
    if need_wheat > 0 and s.n_animals > 0:
        cost = (s.prices.get("WHEAT", 30) + 3) * need_wheat
        n = need_wheat if cash >= cost else max(0, cash // (s.prices.get("WHEAT", 30) + 3))
        if n > 0:
            orders.append(["BUY_PRODUCT", "WHEAT", n]); cash -= (s.prices.get("WHEAT", 30) + 3) * n
    # 3) 토지
    for q, d in LAND_DAY.items():
        if day >= d and q not in s.unlocked:
            idx = len(s.unlocked) - 1
            if idx < len(LAND_PRICES) and LAND_ORDER[idx] == q:
                cost = LAND_PRICES[idx]
                if cash >= cost + 150:
                    orders.append(["BUY_LAND"]); cash -= cost
    # 4) 고용
    hands_target = target_at(HANDS_TARGET, day)
    hire_cost = sum(fib(i) for i in range(hands_target))
    if cash >= hire_cost:
        for _ in range(hands_target): orders.append(["HIRE"])
        cash -= hire_cost
    else:
        n = 0
        while n < hands_target and cash >= fib(n):
            cash -= fib(n); orders.append(["HIRE"]); n += 1
    # 5) 동물 구매 (목장 슬롯 여유 확인은 실행 단계에서)
    cow_t, sheep_t, goose_t, straw_t, tomato_t = plan_targets(s, mem)
    pending_cow = s.shed.get("COW", 0) + sum(i.get("COW", 0) for i in s.invs)
    pending_sheep = s.shed.get("SHEEP", 0) + sum(i.get("SHEEP", 0) for i in s.invs)
    pending_goose = s.shed.get("GOOSE", 0) + sum(i.get("GOOSE", 0) for i in s.invs)
    buy_cow = max(0, cow_t - s.cows - pending_cow)
    buy_sheep = max(0, sheep_t - s.sheep - pending_sheep)
    buy_goose = max(0, goose_t - s.geese - pending_goose)
    reserve = 60 if day <= 2 else 120
    if day >= 3:
        exp = market_outlook(s)
        if exp.get("MILK", 160) < 0.5 * BASE["MILK"]: buy_cow = 0
        if exp.get("WOOL", 200) < 0.5 * BASE["WOOL"]: buy_sheep = 0
    for kind, n in (("GOOSE", buy_goose), ("COW", buy_cow), ("SHEEP", buy_sheep)):
        cost = ANIMALS[kind][1]
        k = 0
        while k < n and cash - cost >= reserve:
            cash -= cost; k += 1
        if k > 0: orders.append(["BUY_ANIMAL", kind, k])
    # 6) 씨앗
    if day == 0:
        orders.append(["BUY_SEED", "MELON", MELON_D0]); cash -= 80 * MELON_D0
        orders.append(["BUY_SEED", "WHEAT", 7]); cash -= 70
    else:
        free = len(s.empty_tiles) + len(s.weed_tiles) - max(0, buy_cow + buy_sheep + buy_goose) - sum(s.seeds.values())
        def buy(crop, n):
            nonlocal cash, free
            cost = CROPS[crop]["seed"]
            n = min(n, free, max(0, (cash - reserve) // cost))
            if n > 0: orders.append(["BUY_SEED", crop, n]); cash -= cost * n; free -= n
        cur = lambda c: sum(1 for _, _, t in s.plant_tiles if t["crop"] == c) + s.seeds.get(c, 0)
        # 1) 딸기 (D13까지), 2) 토마토(수요 시), 3) 밀 목표, 4) 종반 당근
        if day <= 13: buy("STRAWBERRY", min(13, max(0, straw_t - cur("STRAWBERRY"))))
        if tomato_t > 0 and day <= 16: buy("TOMATO", max(0, tomato_t - cur("TOMATO")))
        wheat_t = target_at(WHEAT_TILES_TARGET, day)
        if day <= 26: buy("WHEAT", min(16, max(0, wheat_t - cur("WHEAT"))))
        if 23 <= day <= 26: buy("CARROT", min(12, free))
        if day >= 14 and s.prices.get("MELON", 0) >= 220 and day <= 17: buy("MELON", min(6, free))
    # 주문 10개 상한: 판매/밀/토지/고용 일부는 hour 0, 나머지 고용·동물·씨앗은 hour 1
    h0 = [o for o in orders if o[0] in ("SELL", "BUY_PRODUCT", "BUY_LAND")]
    rest = [o for o in orders if o not in h0]
    hires = [o for o in rest if o[0] == "HIRE"]; others = [o for o in rest if o[0] != "HIRE"]
    room = 10 - len(h0)
    h0 += hires[:room]; hires = hires[room:]
    h1 = hires + others
    mem["h1_orders"] = h1[:10]
    return h0[:10]


def midday_market(s, mem):
    """정오: 창고 산물 판매 + 그 돈으로 딸기 씨앗·동물 추가 구매 (하루 앞당김)."""
    orders = []; day = s.day
    for item in ("MILK", "WOOL", "STRAWBERRY", "MELON", "EGG", "CARROT", "TOMATO"):
        q = s.shed.get(item, 0)
        if q > 0: orders.append(["SELL", item, q])
    cash = s.money + sum(int(s.prices.get(o[1], 1) * o[2] * 0.7) for o in orders)
    reserve = 120
    # 토지
    for q, d in LAND_DAY.items():
        if day >= d and q not in s.unlocked:
            idx = len(s.unlocked) - 1
            if idx < len(LAND_PRICES) and LAND_ORDER[idx] == q and cash >= LAND_PRICES[idx] + 150:
                orders.append(["BUY_LAND"]); cash -= LAND_PRICES[idx]
    cow_t = target_at(COW_TARGET, day) + mem.get("cow_adj", 0)
    sheep_t = target_at(SHEEP_TARGET, day) + mem.get("sheep_adj", 0)
    pending_cow = s.shed.get("COW", 0) + sum(i.get("COW", 0) for i in s.invs)
    pending_sheep = s.shed.get("SHEEP", 0) + sum(i.get("SHEEP", 0) for i in s.invs)
    for kind, n in (("COW", max(0, cow_t - s.cows - pending_cow)), ("SHEEP", max(0, sheep_t - s.sheep - pending_sheep))):
        cost = ANIMALS[kind][1]; k = 0
        while k < n and cash - cost >= reserve: cash -= cost; k += 1
        if k > 0: orders.append(["BUY_ANIMAL", kind, k])
    if 1 <= day <= 13:
        straw_t = target_at(STRAW_TARGET, day)
        cur = sum(1 for _, _, t in s.plant_tiles if t["crop"] == "STRAWBERRY") + s.seeds.get("STRAWBERRY", 0)
        n = min(max(0, straw_t - cur), 13, max(0, (cash - reserve) // 100))
        if n > 0: orders.append(["BUY_SEED", "STRAWBERRY", n]); cash -= 100 * n
    return orders[:10]


# ── 작업 생성 ─────────────────────────────────────────────────────────────
def build_tasks(s, mem):
    """(priority, x, y, op, need_item) 목록. priority 낮을수록 먼저."""
    tasks = []
    day, step = s.day, s.step
    # 동물
    for x, y, t in s.animal_tiles:
        worth = feed_worth(s, t["animal"])
        if not worth and day >= 12:
            # 산물이 헐값이면 급식·관리 중단(탈출 허용). 산물·비료는 있으면 수거
            if t.get("yield_units", 0) > 0 and s.prices.get(ANIMALS[t["animal"]][2], 0) > 3: tasks.append((3, x, y, "HARVEST", None))
            if t.get("fertilizer_available") and s.prices.get("FERTILIZER", 0) > 5: tasks.append((4, x, y, "COLLECT_FERTILIZER", None))
            continue
        if not t.get("fed_today"): tasks.append((1, x, y, "FEED", "WHEAT"))
        if t.get("yield_units", 0) > 0: tasks.append((2, x, y, "HARVEST", None))
        if t.get("fertilizer_available") and s.prices.get("FERTILIZER", 0) > 5: tasks.append((3, x, y, "COLLECT_FERTILIZER", None))
        if not t.get("cared_today"): tasks.append((4, x, y, "CARE", None))
    # 작물
    for x, y, t in s.plant_tiles:
        crop = t["crop"]; cd = CROPS[crop]; age = day - t["planted_day"]
        yu = t.get("yield_units", 0)
        mls = t.get("max_lifespan_step", -1)
        if not cd["ongoing"]:
            ripe = age >= cd["maxday"] or yu >= cd["max"] or (mls >= 0 and step >= mls - 2)
            if crop == "MELON" and age >= 10: ripe = True
            if yu > 0 and ripe: tasks.append((2, x, y, "HARVEST", None))
            elif not t.get("watered_today") and age < cd["maxday"]: tasks.append((2, x, y, "WATER", None))
            elif not t.get("watered_today") and yu <= 0: tasks.append((2, x, y, "WATER", None))
        else:
            if yu > 0: tasks.append((2, x, y, "HARVEST", None))
            dying = mls >= 0 and step >= mls
            if dying and yu <= 0: tasks.append((2, x, y, "DIG", None))
            elif not t.get("watered_today"): tasks.append((2, x, y, "WATER", None))
            # 딸기 시비: 생산일(+10,+14) 에 비료 → 2번의 생산 2배 (하루 전에 해도 3일 유효)
            if crop == "STRAWBERRY" and age in (9, 10, 13, 14) and t.get("fertilized_until_day", -1) < day + (1 if age in (9, 13) else 0):
                tasks.append((2, x, y, "FERTILIZE", "FERTILIZER"))
        if not cd["ongoing"] and crop == "WHEAT" and age <= 1 and t.get("fertilized_until_day", -1) < day and s.prices.get("FERTILIZER", 100) < 70:
            tasks.append((5, x, y, "FERTILIZE", "FERTILIZER"))
    # 잡초 (타일을 막으므로 우선)
    for x, y in s.weed_tiles:
        tasks.append((3, x, y, "DIG", None))
    # 동물 배치: 빈 구조물 + 소지 동물
    carried_any = sum(i.get(k, 0) for i in s.invs for k in ("COW", "SHEEP", "GOOSE")) + sum(s.shed.get(k, 0) for k in ("COW", "SHEEP", "GOOSE"))
    for x, y, t in s.struct_empty:
        kind = t.get("kind")
        if carried_any > 0: tasks.append((1, x, y, "PLACE_" + kind, None))
        elif day >= 12: tasks.append((3, x, y, "DIG", None))   # 빈 목장은 작물용으로 회수
    # 건설/파종: 필요한 목장 수 = 창고+소지 동물 수 − 빈 목장
    carried = {"COW": 0, "SHEEP": 0, "GOOSE": 0}
    for i in s.invs:
        for k in carried: carried[k] += i.get(k, 0)
    for k in carried: carried[k] += s.shed.get(k, 0)
    need_pasture = carried["COW"] + carried["SHEEP"] - sum(1 for _, _, t in s.struct_empty if t.get("kind") == "PASTURE")
    need_coop = carried["GOOSE"] - sum(1 for _, _, t in s.struct_empty if t.get("kind") == "COOP")
    slots = pasture_slots(s, max(0, need_pasture) + max(0, need_coop))
    empty_set = set(s.empty_tiles)
    used = set()
    k = 0
    for (x, y) in slots:
        if (x, y) not in empty_set: continue
        if k < need_pasture: tasks.append((1, x, y, "BUILD_PASTURE", None)); used.add((x, y)); k += 1
        elif k < need_pasture + max(0, need_coop): tasks.append((1, x, y, "BUILD_COOP", None)); used.add((x, y)); k += 1
    # 파종: 씨앗 있는 작물을 빈 타일에 (창고에서 먼 순)
    seeds = dict(s.seeds)
    free = [(x, y) for (x, y) in s.empty_tiles if (x, y) not in used]
    # 목장 예약 타일(가까운 슬롯) 은 미래 동물용으로 비워둔다
    future_pasture = max(0, target_at(COW_TARGET, 12) + target_at(SHEEP_TARGET, 12) + mem.get("cow_adj", 0) + mem.get("sheep_adj", 0) - s.n_animals - carried["COW"] - carried["SHEEP"])
    cap = 0 if len(s.unlocked) == 1 else 18
    reserved = set(pasture_slots(s, min(future_pasture, cap))) if day < 12 else set()
    free = [p for p in free if p not in reserved]
    free.sort(key=lambda p: -(abs(p[0] - 4.5) + abs(p[1] - 4.5)))
    for crop in ("MELON", "TOMATO", "STRAWBERRY", "CARROT", "WHEAT"):
        n = seeds.get(crop, 0)
        while n > 0 and free:
            x, y = free.pop(0)
            tasks.append((3, x, y, "PLANT_" + crop, None)); n -= 1
    return tasks


# ── 경로(구역) 배정 ───────────────────────────────────────────────────────
def snake_tiles(s):
    out = []
    for y in range(N):
        xs = range(N) if y % 2 == 0 else range(N - 1, -1, -1)
        for x in xs:
            if s.tiles[y][x] != "LOCKED": out.append((x, y))
    return out


def tile_weight(s, x, y):
    t = s.tiles[y][x]
    if isinstance(t, dict) and t.get("animal"): return 3.0
    if isinstance(t, dict) and t.get("kind") == "PLANT": return 1.2
    if isinstance(t, dict): return 1.0   # 잡초/빈 구조물
    return 0.6                            # 빈 타일(파종 후보)


def make_routes(s, n_units):
    """동물 담당(유닛당 최대 3마리)과 작물 담당으로 나눈다. 둘 다 스네이크 순서로 연속 구역."""
    tiles = snake_tiles(s)
    animals = [(x, y) for (x, y) in tiles if isinstance(s.tiles[y][x], dict) and s.tiles[y][x].get("animal")]
    others = [(x, y) for (x, y) in tiles if (x, y) not in set(animals)]
    n_an_units = min(n_units - 1, max(1, math.ceil(len(animals) / 3))) if animals and n_units > 1 else (1 if animals else 0)
    if n_units == 1: n_an_units = 1 if animals else 0
    routes = [[] for _ in range(n_units)]
    # 동물 구역
    if n_an_units > 0:
        per = math.ceil(len(animals) / n_an_units)
        for k in range(n_an_units):
            routes[k] = animals[k * per:(k + 1) * per]
    # 작물 구역 (나머지 유닛). 유닛이 동물 담당뿐이면 동물 담당도 작물을 나눠 맡는다
    crop_units = list(range(n_an_units, n_units)) if n_an_units < n_units else list(range(n_units))
    w = [tile_weight(s, x, y) for x, y in others]
    total = sum(w); per = total / max(1, len(crop_units))
    k = 0; acc = 0.0
    for (x, y), wi in zip(others, w):
        if acc >= per * (k + 1) and k < len(crop_units) - 1: k += 1
        routes[crop_units[k]].append((x, y)); acc += wi
    return routes


def pending_ops(s, x, y, inv, tasks_by_tile):
    """해당 타일에서 지금 할 수 있는 작업 목록 (우선순위순)."""
    ops = []
    for pr, op, need in tasks_by_tile.get((x, y), []):
        if need and inv.get(need, 0) <= 0: continue
        if op.startswith("PLACE_"):
            kind = op[6:]
            ok = (kind == "PASTURE" and (inv.get("COW", 0) > 0 or inv.get("SHEEP", 0) > 0)) or (kind == "COOP" and inv.get("GOOSE", 0) > 0)
            if not ok: continue
        ops.append((pr, op))
    ops.sort()
    return ops


def to_action(op, inv):
    if op.startswith("PLANT_"): return ["PLANT", op[6:]]
    if op.startswith("PLACE_"):
        kind = op[6:]
        animal = "GOOSE" if kind == "COOP" else ("COW" if inv.get("COW", 0) > 0 else "SHEEP")
        return ["PLACE", animal]
    return [op]


def pickups(s, mem, i, route, tasks_by_tile):
    inv = s.invs[i]; pos = s.positions[i]
    if pos not in SHED_TILES or s.hour < 2 or s.hour > 10: return None
    claimed = mem.setdefault("claim", {})
    day = s.day
    n_an = sum(1 for (x, y) in route if isinstance(s.tiles[y][x], dict) and s.tiles[y][x].get("animal"))
    # 1) 동물 담당: 밀 먼저 (구역 동물 수 + 1)
    if n_an > 0 and inv.get("WHEAT", 0) < n_an and not claimed.get((day, "w", i)):
        left = s.shed.get("WHEAT", 0) - claimed.get((day, "wheat"), 0)
        take = min(n_an + 1 - inv.get("WHEAT", 0), left)
        claimed[(day, "w", i)] = True
        if take > 0:
            claimed[(day, "wheat")] = claimed.get((day, "wheat"), 0) + take
            return ["PICKUP", "WHEAT", take]
    # 2) 작물 담당: 창고의 동물을 1마리씩 가져다 배치
    if n_an == 0:
        for kind in ("COW", "SHEEP", "GOOSE"):
            avail = s.shed.get(kind, 0) - claimed.get((day, kind), 0)
            if avail > 0 and not any(inv.get(k, 0) for k in ("COW", "SHEEP", "GOOSE")):
                claimed[(day, kind)] = claimed.get((day, kind), 0) + 1
                return ["PICKUP", kind, 1]
    # 3) 비료: 내 구역 시비 수
    n_f = sum(1 for (x, y) in route for pr, op, need in tasks_by_tile.get((x, y), []) if op == "FERTILIZE")
    if n_f > 0 and inv.get("FERTILIZER", 0) < n_f and not claimed.get((day, "f", i)):
        left = s.shed.get("FERTILIZER", 0) - claimed.get((day, "fert"), 0)
        take = min(n_f - inv.get("FERTILIZER", 0), left)
        claimed[(day, "f", i)] = True
        if take > 0:
            claimed[(day, "fert")] = claimed.get((day, "fert"), 0) + take
            return ["PICKUP", "FERTILIZER", take]
    return None


def assign(s, mem, tasks):
    n = len(s.positions)
    tasks_by_tile = {}
    for pr, x, y, op, need in tasks:
        tasks_by_tile.setdefault((x, y), []).append((pr, op, need))
    routes = mem.get("routes")
    if not routes or len(routes) != n or mem.get("routes_day") != s.day or s.hour == 2:
        routes = make_routes(s, n); mem["routes"] = routes; mem["routes_day"] = s.day
    actions = [["PASS"] for _ in range(n)]
    claimed_tiles = set()
    for i in range(n):
        pos = s.positions[i]; inv = s.invs[i]; route = routes[i]
        # 0) 동물을 들고 있으면 배치가 최우선: 빈 구조물로 가서 PLACE, 없으면 가장 가까운 슬롯에 BUILD
        carrying = [k for k in ("COW", "SHEEP", "GOOSE") if inv.get(k, 0) > 0]
        if carrying:
            kind = "COOP" if carrying[0] == "GOOSE" else "PASTURE"
            targets = [(x, y) for x, y, t in s.struct_empty if t.get("kind") == kind and (x, y) not in claimed_tiles]
            if not targets:
                targets = [(x, y) for (x, y) in pasture_slots(s, 30) if s.tiles[y][x] is None and (x, y) not in claimed_tiles][:1]
                build = True
            else:
                build = False
            if targets:
                tgt = min(targets, key=lambda p: dist(pos, p)); claimed_tiles.add(tgt)
                if pos == tgt:
                    actions[i] = ["BUILD_" + kind] if build else ["PLACE", carrying[0]]
                else:
                    actions[i] = step_toward(pos, tgt)
                continue
        pk = pickups(s, mem, i, route, tasks_by_tile)
        if pk: actions[i] = pk; continue
        # 저녁 하역: hour>=20 이면 산물을 든 유닛은 창고로 가서 DROP (당일 판매용)
        prod_items = [(inv.get(k, 0), k) for k in ("MILK", "WOOL", "STRAWBERRY", "MELON", "EGG", "CARROT", "TOMATO") if inv.get(k, 0) > 0]
        produce = sum(q for q, _ in prod_items)
        near = min(dist(pos, p) for p in SHED_TILES)
        if (s.day >= 29 and s.hour >= 20):
            if pos in SHED_TILES:
                actions[i] = ["DROP"] if any(v > 0 for v in inv.values()) else ["PASS"]
            else:
                actions[i] = step_toward(pos, min(SHED_TILES, key=lambda p: dist(pos, p)))
            continue
        # 1) 내 구역: 현재 위치에 할 일이 있으면 즉시
        ops = pending_ops(s, pos[0], pos[1], inv, tasks_by_tile) if pos in route or pos in tasks_by_tile else []
        if ops and pos not in claimed_tiles:
            pr, op = ops[0]; actions[i] = to_action(op, inv); claimed_tiles.add(pos)
            tasks_by_tile[pos] = [t for t in tasks_by_tile[pos] if t[1] != op]
            continue
        # 2) 내 구역에서 가장 가까운 미처리 타일
        best = None; bd = None
        for (x, y) in route:
            if (x, y) in claimed_tiles: continue
            if pending_ops(s, x, y, inv, tasks_by_tile):
                d = dist(pos, (x, y))
                if bd is None or d < bd: best, bd = (x, y), d
        # 2b) 내 구역이 끝났고 산물을 들고 있으면 창고에 하역 (당일 판매)
        if best is None and produce >= 2 and s.hour >= 8:
            tgt = min(SHED_TILES, key=lambda p: dist(pos, p))
            if pos in SHED_TILES:
                q, k = max(prod_items); actions[i] = ["PLACE", k, q]
            else: actions[i] = step_toward(pos, tgt)
            continue
        # 3) 없으면 전역에서 가장 가까운 타일
        if best is None:
            for (x, y), lst in tasks_by_tile.items():
                if (x, y) in claimed_tiles or not lst: continue
                if pending_ops(s, x, y, inv, tasks_by_tile):
                    d = dist(pos, (x, y)) + 2
                    if bd is None or d < bd: best, bd = (x, y), d
        if best is None: continue
        claimed_tiles.add(best)
        if pos == best:
            pr, op = pending_ops(s, best[0], best[1], inv, tasks_by_tile)[0]
            actions[i] = to_action(op, inv)
            tasks_by_tile[best] = [t for t in tasks_by_tile[best] if t[1] != op]
        else:
            actions[i] = step_toward(pos, best)
    return actions


def agent(obs, cfg=None):
    try:
        s = parse(obs)
        mem = _S.get(s.seat)
        if mem is None or s.step == 0 or s.step < mem.get("last", -1):
            mem = {"last": s.step}; _S[s.seat] = mem
        mem["last"] = s.step
        market = []
        if s.hour == 0:
            market = daily_market(s, mem)
        elif s.hour == 1:
            market = mem.pop("h1_orders", [])
        elif s.hour >= 22:
            # 저녁 판매: 산물 전량 (밀·비료는 하루 시작에 예비분 계산 후 판매)
            items = PRODUCTS if s.day >= 29 else ("MILK", "WOOL", "STRAWBERRY", "MELON", "EGG", "CARROT", "TOMATO")
            for item in items:
                q = s.shed.get(item, 0)
                if q > 0: market.append(["SELL", item, q])
        # 창고 과밀 방지: 낮에 창고 80 이상이면 산물 즉시 판매
        elif sum(s.shed.values()) >= 80:
            for item in ("MILK", "WOOL", "STRAWBERRY", "MELON", "EGG", "CARROT", "FERTILIZER"):
                q = s.shed.get(item, 0)
                if q > 0: market.append(["SELL", item, q])
        # 새 유닛 스폰: 고용 스텝 다음 스텝부터 존재
        tasks = build_tasks(s, mem)
        acts = assign(s, mem, tasks)
        # 파종 원자성: 같은 작물 PLANT 수가 씨앗보다 많으면 초과분 PASS
        cnt = {}
        for i, a in enumerate(acts):
            if a[0] == "PLANT":
                cnt[a[1]] = cnt.get(a[1], 0) + 1
                if cnt[a[1]] > s.seeds.get(a[1], 0): acts[i] = ["PASS"]
        return {"farmer": acts[0], "hands": acts[1:], "market": market[:10]}
    except Exception:
        try:
            hands = list(_get(_get(obs, "farms")[int(_get(obs, "player", 0) or 0)], "hands", []) or [])
        except Exception:
            hands = []
        return {"farmer": ["PASS"], "hands": [["PASS"] for _ in hands], "market": []}


_submission_agent = agent
