"""
Kaggriculture v9.0 — 라이브 엔진 (2026-09-04)
==============================================
대본 재생이 아니라 매 스텝 관측을 보고 판단하는 에이전트.
매크로 계획은 13계열 공개 대본(솔로 153k)의 일정(고용·동물·작물·토지)을 본뜨고,
실행은 그리디 작업 배정(가까운 작업부터)으로 한다. 수요 규칙(Crop Dusta)은 2단계에서 추가.
"""
import math
import os

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
STRAW_TARGET = {4: 4, 5: 8, 6: 12, 7: 16, 8: 20, 9: 24, 11: 37} if int(os.environ.get("KG_STNEW","0")) else {5: 4, 6: 12, 7: 16, 8: 20, 9: 24, 11: 37}
MELON_D0 = 12
RESERVE_MODE = int(os.environ.get("KG_RES","0"))
APU = int(os.environ.get("KG_APU","3"))
WATER_ECON = int(os.environ.get("KG_WE","0"))
UNI = int(os.environ.get("KG_UNI","0"))
PRW = float(os.environ.get("KG_PRW","4"))
BAND = int(os.environ.get("KG_BAND","1"))
PLANT_LAST_HOUR = int(os.environ.get("KG_PLH","21"))
ONSPOT_FIRST = int(os.environ.get("KG_OSF","1"))
FEED_GATE = int(os.environ.get("KG_FG","0"))
HARV_PR = int(os.environ.get("KG_HPR","2"))
HAUL_V = int(os.environ.get("KG_HAUL","999999"))
DEMAND_RULES = int(os.environ.get("KG_DEM","1"))
SMART_SELL = int(os.environ.get("KG_SMART","0"))
SELL_THR = float(os.environ.get("KG_THR","0.6"))
HOLD_DAYS = float(os.environ.get("KG_HOLD","3"))
FERT_K = float(os.environ.get("KG_FK","0"))
MELON_RUSH = int(os.environ.get("KG_MR","0"))
ONSPOT_MAXPR = int(os.environ.get("KG_OMP","9"))
RUSH_GLOBAL = int(os.environ.get("KG_RG","0"))
RUSH_ONSPOT = int(os.environ.get("KG_RO","1"))
RUSH_LAST_HOUR = int(os.environ.get("KG_RLH","12"))
SHED_DROP = int(os.environ.get("KG_SD","0"))
PREBUILD = int(os.environ.get("KG_PB","0"))
D0_WHEAT = int(os.environ.get("KG_D0W","0"))
COW_LAST_DAY = int(os.environ.get("KG_CLD","16"))
SHEEP_LAST_DAY = int(os.environ.get("KG_SLD","18"))
FC_SEEDS = int(os.environ.get("KG_FC","0"))
FC_START = int(os.environ.get("KG_FCS","1"))
FC_DAMP = float(os.environ.get("KG_FCD","1.0"))
OWN_W = float(os.environ.get("KG_OWN","1.0"))
HOURLY_FERT = int(os.environ.get("KG_HF","0"))
HOURLY_WHEAT = int(os.environ.get("KG_HW","0"))
FETCH = int(os.environ.get("KG_FETCH","0"))
WHEAT_MIN_EXTRA = int(os.environ.get("KG_WME","4"))
ROUTE_ON_ANIMAL = int(os.environ.get("KG_ROA","0"))
FERT_HAUL = int(os.environ.get("KG_FH","0"))
OPENING_SCRIPT = {"0":[["BUY_PRODUCT","WHEAT",13]],"1":[["BUY_SEED","WHEAT",7],["BUY_SEED","MELON",12],["HIRE"],["HIRE"],["HIRE"],["HIRE"],["HIRE"],["BUY_ANIMAL","COW",2],["BUY_ANIMAL","SHEEP",2]],"3":[["BUY_PRODUCT","WHEAT",1]],"4":[["BUY_PRODUCT","WHEAT",1]],"5":[["BUY_PRODUCT","WHEAT",1]],"6":[["BUY_PRODUCT","WHEAT",1]],"7":[["BUY_PRODUCT","WHEAT",1]],"8":[["BUY_PRODUCT","WHEAT",1]],"9":[["BUY_PRODUCT","WHEAT",1]],"10":[["BUY_PRODUCT","WHEAT",1]],"11":[["BUY_PRODUCT","WHEAT",1]],"24":[["HIRE"],["HIRE"],["HIRE"],["HIRE"]],"30":[["BUY_PRODUCT","WHEAT",3]],"31":[["BUY_PRODUCT","WHEAT",4]],"32":[["BUY_PRODUCT","WHEAT",2]],"48":[["HIRE"],["HIRE"],["HIRE"],["HIRE"],["BUY_SEED","WHEAT",5]],"65":[["BUY_ANIMAL","COW",1]],"72":[["HIRE"],["HIRE"],["HIRE"],["HIRE"],["HIRE"],["BUY_SEED","WHEAT",5]],"88":[["BUY_ANIMAL","COW",1]],"96":[["HIRE"],["HIRE"],["HIRE"],["HIRE"],["BUY_SEED","WHEAT",5],["BUY_SEED","CARROT",3]],"100":[["BUY_SEED","STRAWBERRY",1]],"108":[["BUY_PRODUCT","WHEAT",1]],"110":[["BUY_PRODUCT","WHEAT",1]],"112":[["BUY_PRODUCT","WHEAT",1]],"114":[["BUY_PRODUCT","WHEAT",1]],"116":[["BUY_PRODUCT","WHEAT",1]],"118":[["BUY_PRODUCT","WHEAT",1],["BUY_SEED","STRAWBERRY",3]],"120":[["HIRE"],["HIRE"],["HIRE"],["BUY_SEED","WHEAT",4]],"121":[["HIRE"],["HIRE"]],"123":[["BUY_SEED","STRAWBERRY",1]],"131":[["BUY_SEED","STRAWBERRY",1]],"141":[["BUY_SEED","STRAWBERRY",2]],"144":[["HIRE"],["HIRE"],["HIRE"],["HIRE"],["HIRE"],["HIRE"],["HIRE"],["BUY_SEED","WHEAT",2],["BUY_SEED","CARROT",1],["BUY_SEED","STRAWBERRY",1]],"145":[["HIRE"],["BUY_SEED","STRAWBERRY",1]],"150":[["BUY_PRODUCT","WHEAT",2],["BUY_SEED","STRAWBERRY",2],["BUY_LAND"],["BUY_ANIMAL","COW",2],["BUY_PRODUCT","FERTILIZER",1]],"151":[["BUY_PRODUCT","FERTILIZER",1]],"152":[["BUY_PRODUCT","WHEAT",2]],"154":[["BUY_PRODUCT","WHEAT",1]],"156":[["BUY_PRODUCT","WHEAT",3]],"158":[["BUY_PRODUCT","WHEAT",2]],"168":[["HIRE"],["HIRE"],["HIRE"],["HIRE"],["HIRE"],["HIRE"],["BUY_SEED","WHEAT",4],["BUY_SEED","STRAWBERRY",4]],"169":[["HIRE"],["HIRE"],["BUY_ANIMAL","COW",1]],"174":[["BUY_PRODUCT","FERTILIZER",1]],"176":[["BUY_ANIMAL","COW",1]],"192":[["HIRE"],["HIRE"],["HIRE"],["HIRE"],["HIRE"],["BUY_SEED","WHEAT",4],["BUY_SEED","STRAWBERRY",1]],"193":[["HIRE"],["HIRE"],["HIRE"],["HIRE"],["BUY_SEED","STRAWBERRY",1]],"195":[["HIRE"],["BUY_PRODUCT","WHEAT",3],["BUY_SEED","STRAWBERRY",2],["BUY_ANIMAL","COW",1],["BUY_ANIMAL","SHEEP",2]],"196":[["BUY_PRODUCT","WHEAT",3]],"198":[["BUY_PRODUCT","WHEAT",3]],"200":[["BUY_PRODUCT","WHEAT",3]],"202":[["BUY_PRODUCT","WHEAT",3]],"204":[["BUY_PRODUCT","WHEAT",3]],"206":[["BUY_PRODUCT","WHEAT",3]],"216":[["BUY_SEED","WHEAT",4],["BUY_SEED","STRAWBERRY",4],["HIRE"],["HIRE"],["HIRE"],["HIRE"],["HIRE"],["HIRE"],["HIRE"],["HIRE"]],"217":[["HIRE"],["BUY_ANIMAL","SHEEP",1],["BUY_PRODUCT","FERTILIZER",1]],"218":[["BUY_PRODUCT","WHEAT",3]],"220":[["BUY_PRODUCT","WHEAT",3]],"222":[["BUY_PRODUCT","WHEAT",3]],"224":[["BUY_PRODUCT","WHEAT",3]],"226":[["BUY_PRODUCT","WHEAT",3],["BUY_ANIMAL","SHEEP",1]],"228":[["BUY_PRODUCT","WHEAT",3]],"230":[["BUY_PRODUCT","WHEAT",3]],"240":[["BUY_SEED","WHEAT",4],["HIRE"],["HIRE"],["HIRE"],["HIRE"],["HIRE"],["HIRE"],["HIRE"],["HIRE"],["HIRE"]],"241":[["HIRE"],["HIRE"],["BUY_ANIMAL","SHEEP",2],["BUY_PRODUCT","FERTILIZER",3]],"242":[["BUY_PRODUCT","WHEAT",5]],"244":[["BUY_PRODUCT","WHEAT",1]],"249":[["BUY_PRODUCT","WHEAT",14],["BUY_PRODUCT","FERTILIZER",5]],"250":[["BUY_PRODUCT","WHEAT",5]],"252":[["BUY_PRODUCT","WHEAT",5]],"254":[["BUY_PRODUCT","WHEAT",5]],"256":[["BUY_PRODUCT","WHEAT",5]],"264":[["BUY_SEED","WHEAT",11],["BUY_SEED","CARROT",1],["BUY_SEED","STRAWBERRY",9],["HIRE"],["HIRE"],["HIRE"],["HIRE"],["HIRE"]],"265":[["HIRE"],["HIRE"],["HIRE"],["HIRE"],["HIRE"],["HIRE"],["BUY_LAND"],["BUY_ANIMAL","SHEEP",1],["BUY_PRODUCT","FERTILIZER",1]],"266":[["BUY_PRODUCT","WHEAT",3]],"268":[["BUY_PRODUCT","WHEAT",3]],"270":[["BUY_PRODUCT","WHEAT",3]],"272":[["BUY_PRODUCT","WHEAT",3]],"274":[["BUY_PRODUCT","WHEAT",3]],"276":[["BUY_PRODUCT","WHEAT",3]],"278":[["BUY_PRODUCT","WHEAT",3]]}
OPENING_END = int(os.environ.get("KG_OPEN","0"))   # 이 스텝 전까지 대본 구매 일정 사용 (0이면 비활성)

GEESE = int(os.environ.get("KG_GEESE","0"))
SHEEP_PLUS = int(os.environ.get("KG_SHP","0"))
WHEAT_FERT = int(os.environ.get("KG_WF","1"))
MELON_FERT = int(os.environ.get("KG_MF","0"))
WHEAT_FERT_DAY = int(os.environ.get("KG_WFD","10"))
TOMATO_FERT = int(os.environ.get("KG_TF","1"))
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
    if day >= 6 and DEMAND_RULES:
        milk_d = dem.get("MILK", 0); wool_d = dem.get("WOOL", 0); egg_d = dem.get("EGG", 0)
        straw_d = dem.get("STRAWBERRY", 0); tom_d = dem.get("TOMATO", 0)
        if milk_d == 0: cow_t = min(cow_t, 6)
        if wool_d == 0: sheep_t = min(sheep_t, 5)
        elif wool_d >= 4 and SHEEP_PLUS: sheep_t = max(sheep_t, min(12, sheep_t + 3))
        if GEESE and egg_d >= 1: goose_t = 4 if egg_d < 3 else 6
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
    fert_need = fert_reserve(s)
    if SMART_SELL and day < 29:
        orders += smart_sells(s, mem)
    else:
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
    # 3) 고용 (토지·동물·씨앗은 buy_plan 이 매시간 실제 현금으로 판단)
    hands_target = target_at(HANDS_TARGET, day)
    hire_cost = sum(fib(i) for i in range(hands_target))
    if cash >= hire_cost:
        for _ in range(hands_target): orders.append(["HIRE"])
        cash -= hire_cost
    else:
        n = 0
        while n < hands_target and cash >= fib(n):
            cash -= fib(n); orders.append(["HIRE"]); n += 1
    h0 = [o for o in orders if o[0] in ("SELL", "BUY_PRODUCT")]
    hires = [o for o in orders if o[0] == "HIRE"]
    room = 10 - len(h0)
    h0 += hires[:room]
    mem["h1_orders"] = hires[room:]
    mem["hire_cost_h1"] = sum(fib(len(hires[:room]) + i) for i in range(len(hires[room:])))
    return h0[:10]


def order_cost(s, o, hires_so_far):
    op = o[0]
    if op == "HIRE": return fib(s.hires_today + hires_so_far)
    if op == "BUY_LAND":
        idx = len(s.unlocked) - 1
        return LAND_PRICES[idx] if idx < len(LAND_PRICES) else 10 ** 9
    if op == "BUY_SEED": return CROPS[o[1]]["seed"] * int(o[2])
    if op == "BUY_ANIMAL": return ANIMALS[o[1]][1] * int(o[2])
    if op == "BUY_PRODUCT": return (s.prices.get(o[1], 30) + 3) * int(o[2])
    return 0


def opening_orders(s, mem, cash):
    """대본(13계열)의 구매 일정을 현금 가드와 함께 재생. 못 산 주문은 다음 스텝으로 이월."""
    queue = mem.pop("defer", []) + [list(o) for o in OPENING_SCRIPT.get(str(s.step), [])]
    out = []; defer = []; hires = 0
    for o in queue:
        if o[0] == "BUY_LAND" and len(s.unlocked) >= 4: continue
        c = order_cost(s, o, hires)
        if len(out) >= 10: defer.append(o); continue
        if cash >= c:
            out.append(o); cash -= c
            if o[0] == "HIRE": hires += 1
        else:
            # 부분 구매: 수량 주문은 살 수 있는 만큼만
            if o[0] in ("BUY_SEED", "BUY_ANIMAL", "BUY_PRODUCT") and int(o[2]) > 1:
                unit = c / int(o[2]); k = int(cash // unit) if unit > 0 else 0
                if k > 0:
                    out.append([o[0], o[1], k]); cash -= unit * k
                    defer.append([o[0], o[1], int(o[2]) - k]); continue
            defer.append(o)
    mem["defer"] = defer
    return out


def buy_plan(s, mem, cash):
    """매시간: 실제 현금으로 토지·동물·씨앗 구매 (주문 목록 반환)."""
    orders = []; day = s.day
    if day >= 29: return orders
    reserve = 60 if day <= 2 else 120
    if HOURLY_WHEAT and s.n_animals > 0 and s.hour <= 16:
        # 오늘 급식 부족분: 아직 안 먹인 동물 수 − (창고 밀 + 유닛이 든 밀)
        unfed = sum(1 for _, _, t in s.animal_tiles if not t.get("fed_today"))
        have = s.shed.get("WHEAT", 0) + sum(i.get("WHEAT", 0) for i in s.invs)
        need = unfed - have
        if need > 0:
            price = s.prices.get("WHEAT", 30) + 3
            n = min(need, max(0, cash // price))
            if n > 0: orders.append(["BUY_PRODUCT", "WHEAT", n]); cash -= price * n
    if day >= 3 and RESERVE_MODE:
        # 내일 아침 급식 밀 구매비 + 고용비를 남겨둔다
        feed_need = max(0, int(s.n_animals * 1.2) + 2 - s.shed.get("WHEAT", 0)) * (s.prices.get("WHEAT", 30) + 3)
        hire_need = sum(fib(i) for i in range(target_at(HANDS_TARGET, day + 1)))
        reserve = max(reserve, feed_need + (hire_need if RESERVE_MODE >= 2 else 0))
    # 토지
    for q, d in LAND_DAY.items():
        if day >= d and q not in s.unlocked:
            idx = len(s.unlocked) - 1
            if idx < len(LAND_PRICES) and LAND_ORDER[idx] == q:
                cost = LAND_PRICES[idx]
                if cash >= cost + 150:
                    orders.append(["BUY_LAND"]); cash -= cost
    # 동물 구매 (목장 슬롯 여유 확인은 실행 단계에서)
    cow_t, sheep_t, goose_t, straw_t, tomato_t = plan_targets(s, mem)
    pending_cow = s.shed.get("COW", 0) + sum(i.get("COW", 0) for i in s.invs)
    pending_sheep = s.shed.get("SHEEP", 0) + sum(i.get("SHEEP", 0) for i in s.invs)
    pending_goose = s.shed.get("GOOSE", 0) + sum(i.get("GOOSE", 0) for i in s.invs)
    buy_cow = max(0, cow_t - s.cows - pending_cow)
    buy_sheep = max(0, sheep_t - s.sheep - pending_sheep)
    buy_goose = max(0, goose_t - s.geese - pending_goose)
    if day >= 3 and DEMAND_RULES:
        exp = market_outlook(s)
        if exp.get("MILK", 160) < 0.5 * BASE["MILK"]: buy_cow = 0
        if exp.get("WOOL", 200) < 0.5 * BASE["WOOL"]: buy_sheep = 0
    if day > COW_LAST_DAY: buy_cow = 0
    if day > SHEEP_LAST_DAY: buy_sheep = 0
    for kind, n in (("GOOSE", buy_goose), ("COW", buy_cow), ("SHEEP", buy_sheep)):
        cost = ANIMALS[kind][1]
        k = 0
        while k < n and cash - cost >= reserve:
            cash -= cost; k += 1
        if k > 0: orders.append(["BUY_ANIMAL", kind, k])
    # 씨앗
    if day == 0:
        if not mem.get("d0_seeds"):
            orders.append(["BUY_SEED", "MELON", MELON_D0]); cash -= 80 * MELON_D0
            orders.append(["BUY_SEED", "WHEAT", 7]); cash -= 70
            if D0_WHEAT > 0: orders.append(["BUY_PRODUCT", "WHEAT", D0_WHEAT]); cash -= 28 * D0_WHEAT
            mem["d0_seeds"] = True
    else:
        free = len(s.empty_tiles) + len(s.weed_tiles) - max(0, buy_cow + buy_sheep + buy_goose) - sum(s.seeds.values())
        def buy(crop, n):
            nonlocal cash, free
            cost = CROPS[crop]["seed"]
            n = min(n, free, max(0, (cash - reserve) // cost))
            if n > 0: orders.append(["BUY_SEED", crop, n]); cash -= cost * n; free -= n
        cur = lambda c: sum(1 for _, _, t in s.plant_tiles if t["crop"] == c) + s.seeds.get(c, 0)
        if FC_SEEDS and day >= FC_START:
            # 예측 가격 기반 작물 선택: 타일·일당 가치 높은 순으로 빈 타일을 채운다 (딸기는 목표 상한)
            vals = sorted(((crop_value_fc(s, mem, c), c) for c in ("WHEAT", "STRAWBERRY", "TOMATO", "CARROT", "MELON")), reverse=True)
            wheat_min = min(target_at(WHEAT_TILES_TARGET, day), s.n_animals + WHEAT_MIN_EXTRA)
            if cur("WHEAT") < wheat_min and day <= 26: buy("WHEAT", min(16, wheat_min - cur("WHEAT")))
            want = {"STRAWBERRY": min(13, max(0, straw_t - cur("STRAWBERRY"))) if day <= 13 else 0,
                    "TOMATO": min(6, max(0, 10 - cur("TOMATO"))) if day <= 17 else 0,
                    "MELON": min(6, free) if day <= 17 else 0,
                    "CARROT": min(12, free) if day <= 26 else 0, "WHEAT": min(16, free) if day <= 26 else 0}
            for v, c in vals:
                if v <= 0 or free <= 0 or want.get(c, 0) <= 0: continue
                before = free
                buy(c, want[c])
                # 최고 가치 작물을 현금 부족으로 못 샀으면 더 싼 하위 작물로 대체하지 않는다 (현금은 다음 시간에 다시 시도)
                if free == before and cash < reserve + CROPS[c]["seed"]: break
        else:
            # 1) 딸기 (D13까지), 2) 토마토(수요 시), 3) 밀 목표, 4) 종반 당근
            if day <= 13: buy("STRAWBERRY", min(13, max(0, straw_t - cur("STRAWBERRY"))))
            if tomato_t > 0 and day <= 16: buy("TOMATO", max(0, tomato_t - cur("TOMATO")))
            wheat_t = target_at(WHEAT_TILES_TARGET, day)
            if day <= 26: buy("WHEAT", min(16, max(0, wheat_t - cur("WHEAT"))))
            if 23 <= day <= 26: buy("CARROT", min(12, free))
            if day >= 14 and s.prices.get("MELON", 0) >= 220 and day <= 17: buy("MELON", min(6, free))
    return orders


MARKET_PARAMS = {
    "WHEAT": (25, 400, "sqrt", 0.80, "log", 0.20), "CARROT": (35, 450, "hinge", 1.00, "sqrt", 0.70),
    "TOMATO": (60, 200, "hinge", 0.40, "sqrt", 0.60), "STRAWBERRY": (120, 100, "sqrt", 0.70, "linear", 1.60),
    "MELON": (250, 300, "log", 0.20, "sq", 3.60), "EGG": (50, 332, "hinge", 0.40, "log", 0.20),
    "MILK": (160, 122, "sqrt", 0.60, "linear", 1.60), "WOOL": (200, 105, "log", 0.20, "sq", 3.20),
    "FERTILIZER": (100, 200, "linear", 0.40, "linear", 0.40),
}


def _shape(func, x, T):
    x = max(0.0, x)
    if func == "linear": return x
    if func == "sq": return x * x
    if func == "sqrt": return math.sqrt(x)
    if func == "log": return math.log(1.0 + x)
    if func == "hinge":
        u = x / T
        return u + 8.0 * max(0.0, u - 1.0) ** 2
    return x


def price_at(item, inv):
    """시장 재고 inv 일 때 1단위 판매가 (환경 기본 가격모형)."""
    base, T, fb, tb, fa, ta = MARKET_PARAMS[item]
    x = inv - 10000
    if x < 0:
        amp = tb * base / _shape(fb, T, T); p = base + amp * _shape(fb, -x, T)
    else:
        amp = ta * base / _shape(fa, T, T); p = base - amp * _shape(fa, x, T)
    return max(1, int(round(p)))


def update_hist(s, mem):
    """하루 한 번(hour 0) 시장 재고 기록 → 최근 추세로 미래 가격 예측."""
    if s.hour != 0: return
    h = mem.setdefault("inv_hist", {})
    for p in PRODUCTS:
        h.setdefault(p, []).append((s.day, s.inv_mkt.get(p, 10000)))
        h[p] = h[p][-6:]


def own_supply(s, item):
    """우리 농장이 앞으로 시장에 내놓을 같은 상품 수량(심긴 타일·씨앗 기준, 대략)."""
    per = {"WHEAT": 4, "STRAWBERRY": 6, "TOMATO": 6, "CARROT": 3, "MELON": 6}.get(item, 0)
    n = sum(1 for _, _, t in s.plant_tiles if t["crop"] == item) + s.seeds.get(item, 0)
    return per * n


def supply_fc(s, item, d):
    """양쪽 농장 타일에서 추정한 향후 d일간 시장 유입량 (둘 다 전량 판매 가정)."""
    tot = 0.0
    for farm in s.all_farms:
        for row in farm.get("tiles", []):
            for t in row:
                if not isinstance(t, dict): continue
                a = t.get("animal"); c = t.get("crop")
                if a:
                    prod = ANIMALS[a][2]
                    if prod == item:
                        first = t.get("placed_day", 0) + {"COW": 8, "SHEEP": 6, "GOOSE": 4}[a]
                        eff = max(0.0, min(d, s.day + d - first))
                        tot += eff * {"COW": 1.5, "SHEEP": 1.33, "GOOSE": 2.0}[a]
                    elif item == "FERTILIZER": tot += d
                elif c == item:
                    age = s.day - t.get("planted_day", s.day)
                    if c == "MELON": tot += 5.5 if age + d >= 10 else 0
                    elif c == "WHEAT": tot += 0.7 * d
                    elif c == "CARROT": tot += 0.75 * d
                    elif c == "STRAWBERRY": tot += 1.5 * sum(1 for k in (9, 11, 13, 15) if age <= k < age + d)
                    elif c == "TOMATO": tot += 1.5 * sum(1 for k in (7, 8, 9, 10) if age <= k < age + d)
    return tot


SHOP_P = {}   # 상품별: 상점 1개 추첨 시 기대 소비 배수 (단일상품 상점은 ×2)
for _sh, _prods in SHOPS.items():
    for _p in _prods: SHOP_P[_p] = SHOP_P.get(_p, 0) + (2 if len(_prods) == 1 else 1) / 8.0


def expected_drain(s, item, days_ahead):
    """향후 days_ahead 일간 상점 소비 기대량: 현재 상점 + 앞으로 추첨될 상점(3일마다, 총 8개)의 기대치."""
    if item == "FERTILIZER": return 0.0
    cur = demand_counts(s).get(item, 0)
    n_shops = len(s.shops); tot = 0.0
    for k in range(1, days_ahead + 1):
        day = s.day + k
        draws = max(0, min(8, day // 3) - n_shops)     # day 까지 이뤄질 추가 추첨 수
        tot += 6 * (cur + draws * SHOP_P.get(item, 0)) + 1
    return tot


def price_fc(s, mem, item, days_ahead, extra=0):
    """days_ahead 일 뒤 예상 가격 = 현재 재고 + 양쪽 농장 예상 유입 − 상점 기대 소비 로 가격모형 평가."""
    inv = s.inv_mkt.get(item, 10000) + extra
    fut = inv + supply_fc(s, item, days_ahead) * FC_DAMP - expected_drain(s, item, days_ahead)
    return price_at(item, int(fut))


def crop_value_fc(s, mem, crop):
    """작물별 타일·일당 기대가치 (예측 가격, 시비 포함 산출)."""
    day = s.day
    # 우리 덤핑의 중간 지점 가격으로 평가 (예정 공급의 절반 + 이번 구매분)
    ex = (own_supply(s, crop) * 0.5 + {"WHEAT": 20, "STRAWBERRY": 24, "TOMATO": 24, "CARROT": 18, "MELON": 36}.get(crop, 0)) * OWN_W
    if crop == "WHEAT":
        units = 6 if (WHEAT_FERT and day + 2 >= WHEAT_FERT_DAY) else 3
        return (units * price_fc(s, mem, "WHEAT", 4, ex) - 10) / 5.0
    if crop == "STRAWBERRY":
        if day > 13: return -1
        v = sum(2 * price_fc(s, mem, "STRAWBERRY", d, ex) for d in (10, 12, 14, 16) if day + d <= 29)
        return (v - 100) / 17.0
    if crop == "TOMATO":
        if day > 17: return -1
        v = sum(2 * price_fc(s, mem, "TOMATO", d, ex) for d in (8, 9, 10, 11) if day + d <= 29)
        return (v - 50) / 12.0
    if crop == "CARROT":
        return (3 * price_fc(s, mem, "CARROT", 3, ex) - 20) / 4.0
    if crop == "MELON":
        if day > 17: return -1
        return (6 * price_fc(s, mem, "MELON", 10, ex) - 80) / 11.0
    return -1


def smart_sells(s, mem):
    """한계가격이 기준(base×THR) 이상인 수량만 판매. 창고 압박·종반엔 기준을 낮춘다."""
    orders = []; day = s.day
    thr = SELL_THR
    if day >= 29: thr = 0.0
    elif day == 28: thr = min(thr, 0.25)
    elif day == 27: thr = min(thr, 0.4)
    total = sum(s.shed.values())
    if total >= 85: thr = min(thr, 0.15)
    for item in ("MILK", "WOOL", "STRAWBERRY", "MELON", "EGG", "CARROT", "TOMATO"):
        q = s.shed.get(item, 0)
        if q <= 0: continue
        inv = s.inv_mkt.get(item, 10000); base = MARKET_PARAMS[item][0]
        k = 0
        while k < q and price_at(item, inv + k) >= thr * base: k += 1
        # 보유 상한: 상점 소비(일 6×상점수+1)가 며칠 안에 흡수할 수 있는 양만 들고 간다
        drain = 6 * demand_counts(s).get(item, 0) + 1
        hold_cap = int(drain * min(29 - day, HOLD_DAYS))
        k = max(k, q - hold_cap)
        if k > 0: orders.append(["SELL", item, k])
    return orders


def fert_reserve(s):
    """비료 예비분: 내일까지 시비할 타일 수 (딸기 9/13, 밀 창 첫날, 멜론 8, 토마토 7/10)."""
    day = s.day; fert_need = 0
    for _, _, t in s.plant_tiles:
        age = day - t["planted_day"]; c = t["crop"]
        if c == "STRAWBERRY" and age in (8, 9, 12, 13): fert_need += 1
        elif c == "WHEAT" and WHEAT_FERT and day + 1 >= WHEAT_FERT_DAY and age in (1, 2): fert_need += 1
        elif c == "MELON" and MELON_FERT and age in (7, 8): fert_need += 1
        elif c == "TOMATO" and TOMATO_FERT and age in (6, 7, 9, 10): fert_need += 1
    fert_need += s.seeds.get("WHEAT", 0) if (WHEAT_FERT and day + 1 >= WHEAT_FERT_DAY) else 0
    return min(30, fert_need)


def hourly_sells(s):
    """창고에 들어온 산물은 즉시 판매. 비료도 예비분 초과분은 즉시 (초반 현금)."""
    orders = []
    for item in ("MILK", "WOOL", "STRAWBERRY", "MELON", "EGG", "CARROT", "TOMATO"):
        q = s.shed.get(item, 0)
        if q > 0: orders.append(["SELL", item, q])
    if HOURLY_FERT:
        fq = s.shed.get("FERTILIZER", 0) - fert_reserve(s)
        if fq > 0: orders.append(["SELL", "FERTILIZER", fq])
    return orders


# ── 작업 생성 ─────────────────────────────────────────────────────────────
def build_tasks(s, mem):
    """(priority, x, y, op, need_item) 목록. priority 낮을수록 먼저."""
    tasks = []
    day, step = s.day, s.step
    # 동물
    for x, y, t in s.animal_tiles:
        worth = feed_worth(s, t["animal"]) if FEED_GATE else True
        if not worth and day >= 12:
            # 산물이 헐값이면 급식·관리 중단(탈출 허용). 산물·비료는 있으면 수거
            if t.get("yield_units", 0) > 0 and s.prices.get(ANIMALS[t["animal"]][2], 0) > 3: tasks.append((3, x, y, "HARVEST", None))
            if t.get("fertilizer_available") and s.prices.get("FERTILIZER", 0) > 5: tasks.append((4, x, y, "COLLECT_FERTILIZER", None))
            continue
        if not t.get("fed_today"): tasks.append((1, x, y, "FEED", "WHEAT"))
        if t.get("yield_units", 0) > 0: tasks.append((HARV_PR, x, y, "HARVEST", None))
        if t.get("fertilizer_available") and s.prices.get("FERTILIZER", 0) > 5: tasks.append((3, x, y, "COLLECT_FERTILIZER", None))
        if not t.get("cared_today"): tasks.append((4, x, y, "CARE", None))
    # 작물
    for x, y, t in s.plant_tiles:
        crop = t["crop"]; cd = CROPS[crop]; age = day - t["planted_day"]
        yu = t.get("yield_units", 0)
        mls = t.get("max_lifespan_step", -1)
        cu = t.get("consecutive_unwatered", 0)
        watered = t.get("watered_today")
        fert_until = t.get("fertilized_until_day", -1)
        fert_price = s.prices.get("FERTILIZER", 100)
        if not cd["ongoing"]:
            # 산출은 수확창(window_start..maxday) 안에서 급수할 때만 +1(시비 시 +2). 그 외 날은 잡초 방지용으로만 격일 급수.
            wstart = (cd["maxday"] + 1) // 2
            in_window = wstart <= age <= cd["maxday"]
            done = yu >= cd["max"] or age > cd["maxday"] or (age == cd["maxday"] and watered) or (mls >= 0 and step >= mls - 2)
            if crop == "MELON" and age >= 10 and (watered or yu >= cd["max"] or age >= 11): done = True
            if crop == "MELON" and age >= 12: done = True
            rush = MELON_RUSH and crop == "MELON" and age >= 10
            if yu > 0 and done: tasks.append((0 if rush else HARV_PR, x, y, "HARVEST", None))
            elif not watered and (in_window or cu >= 1): tasks.append((0 if rush else (1 if cu >= 1 else 2), x, y, "WATER", None))
            # 시비: 수확창 첫날에 → 창 전체 2배. 밀은 비료가 밀 3개 값보다 쌀 때만, 멜론은 8일차(8,9,10 → 6개 확보)
            if WHEAT_FERT and day >= WHEAT_FERT_DAY and crop == "WHEAT" and age == wstart and fert_until < day and fert_price < 3 * max(20, s.prices.get("WHEAT", 25)):
                tasks.append((2, x, y, "FERTILIZE", "FERTILIZER"))
            if MELON_FERT and crop == "MELON" and age == 8 and fert_until < day:
                tasks.append((2, x, y, "FERTILIZE", "FERTILIZER"))
        else:
            if yu > 0: tasks.append((HARV_PR, x, y, "HARVEST", None))
            dying = mls >= 0 and step >= mls
            # 생산은 생산일 저녁에 급수와 무관하게 일어나고, 시비 보너스만 그날 급수를 요구한다
            if crop == "STRAWBERRY": prod_today = age >= 9 and (age - 9) % 2 == 0
            else: prod_today = 7 <= age <= 10
            need_water = cu >= 1 or (prod_today and fert_until >= day) or not WATER_ECON
            if dying and yu <= 0: tasks.append((2, x, y, "DIG", None))
            elif not watered and need_water and not dying: tasks.append((1 if cu >= 1 else 2, x, y, "WATER", None))
            if crop == "STRAWBERRY" and age in (9, 10, 13, 14) and fert_until < day + (1 if age in (9, 13) else 0) and 2 * s.prices.get("STRAWBERRY", 120) > fert_price * FERT_K:
                tasks.append((2, x, y, "FERTILIZE", "FERTILIZER"))
            if TOMATO_FERT and crop == "TOMATO" and age in (7, 10) and fert_until < day and 3 * s.prices.get("TOMATO", 60) > fert_price * FERT_K:
                tasks.append((2, x, y, "FERTILIZE", "FERTILIZER"))
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
    # 선제 건설: 내일까지 살 예정인 동물 수만큼 빈 목장을 미리 지어둔다 (낮은 우선순위, 여유 유닛이)
    pre = 0
    if PREBUILD and day < 12:
        cow_t, sheep_t, _, _, _ = plan_targets(s, mem)
        planned = max(0, cow_t - s.cows - carried["COW"]) + max(0, sheep_t - s.sheep - carried["SHEEP"])
        pre = max(0, min(PREBUILD, planned) - max(0, -need_pasture))
    slots = pasture_slots(s, max(0, need_pasture) + max(0, need_coop) + pre)
    empty_set = set(s.empty_tiles)
    used = set()
    k = 0
    for (x, y) in slots:
        if (x, y) not in empty_set: continue
        if k < need_pasture: tasks.append((1, x, y, "BUILD_PASTURE", None)); used.add((x, y)); k += 1
        elif k < need_pasture + max(0, need_coop): tasks.append((1, x, y, "BUILD_COOP", None)); used.add((x, y)); k += 1
        elif k < max(0, need_pasture) + max(0, need_coop) + pre: tasks.append((5, x, y, "BUILD_PASTURE", None)); used.add((x, y)); k += 1
    # 파종: 씨앗 있는 작물을 빈 타일에 (창고에서 먼 순)
    seeds = dict(s.seeds)
    free = [(x, y) for (x, y) in s.empty_tiles if (x, y) not in used]
    # 목장 예약 타일(가까운 슬롯) 은 미래 동물용으로 비워둔다
    future_pasture = max(0, target_at(COW_TARGET, 12) + target_at(SHEEP_TARGET, 12) + mem.get("cow_adj", 0) + mem.get("sheep_adj", 0) - s.n_animals - carried["COW"] - carried["SHEEP"])
    cap = 0 if len(s.unlocked) == 1 else 18
    reserved = set(pasture_slots(s, min(future_pasture, cap))) if day < 12 else set()
    free = [p for p in free if p not in reserved]
    free.sort(key=lambda p: -(abs(p[0] - 4.5) + abs(p[1] - 4.5)))
    # 파종일도 '미급수 1일'로 세므로 심은 당일 급수 못 하면 밤에 잡초가 된다 → 늦은 시간 파종 금지
    if s.hour > PLANT_LAST_HOUR: seeds = {}
    for crop in ("MELON", "TOMATO", "STRAWBERRY", "CARROT", "WHEAT"):
        n = seeds.get(crop, 0)
        while n > 0 and free:
            x, y = free.pop(0)
            tasks.append((3, x, y, "PLANT_" + crop, None)); n -= 1
    return tasks


# ── 경로(구역) 배정 ───────────────────────────────────────────────────────
def snake_tiles(s):
    """BAND 행 높이의 띠를 지그재그로 훑는 순서 (BAND=2 면 2행 폭의 띠 → 구간이 정사각형에 가까움)."""
    out = []
    for b in range(0, N, BAND):
        ys = list(range(b, min(N, b + BAND)))
        xs = range(N) if (b // BAND) % 2 == 0 else range(N - 1, -1, -1)
        for x in xs:
            for y in (ys if x % 2 == 0 else ys[::-1]):
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
    if UNI:
        # 단일 크루: 모든 타일을 작업량 가중 스네이크 구간으로 n등분 (동물 4, 작물 1.2, 빈 타일 0.6)
        w = [4.0 if (isinstance(s.tiles[y][x], dict) and s.tiles[y][x].get("animal")) else tile_weight(s, x, y) for x, y in tiles]
        total = sum(w); per = total / max(1, n_units)
        routes = [[] for _ in range(n_units)]; k = 0; acc = 0.0
        for (x, y), wi in zip(tiles, w):
            if acc >= per * (k + 1) and k < n_units - 1: k += 1
            routes[k].append((x, y)); acc += wi
        return routes
    animals = [(x, y) for (x, y) in tiles if isinstance(s.tiles[y][x], dict) and s.tiles[y][x].get("animal")]
    others = [(x, y) for (x, y) in tiles if (x, y) not in set(animals)]
    n_an_units = min(n_units - 1, max(1, math.ceil(len(animals) / APU))) if animals and n_units > 1 else (1 if animals else 0)
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
    if pos not in SHED_TILES or s.hour < 2 or s.hour > 18: return None
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
    rkey = (s.day, n, s.n_animals if ROUTE_ON_ANIMAL else 0)
    if not routes or len(routes) != n or mem.get("routes_key") != rkey or s.hour == 2:
        routes = make_routes(s, n); mem["routes"] = routes; mem["routes_key"] = rkey
    actions = [["PASS"] for _ in range(n)]
    claimed_tiles = set()
    done_units = set()
    step_claims = {}
    rush_on = RUSH_GLOBAL and s.hour <= RUSH_LAST_HOUR and any(t[0] == 0 for lst in tasks_by_tile.values() for t in lst)
    # 0단계: 제자리에 할 일이 있는 유닛은 먼저 확정 (멀리서 이 타일을 목표로 잡는 유닛에게 뺏기지 않도록)
    if ONSPOT_FIRST:
        for i in range(n):
            pos = s.positions[i]; inv = s.invs[i]
            if any(inv.get(k, 0) > 0 for k in ("COW", "SHEEP", "GOOSE")): continue
            if pos in SHED_TILES and s.hour >= 2 and s.hour <= 18: continue   # 픽업 판단이 먼저
            if s.day >= 29 and s.hour >= 20: continue
            if pos in claimed_tiles: continue
            ops = pending_ops(s, pos[0], pos[1], inv, tasks_by_tile)
            maxpr = RUSH_ONSPOT if rush_on else ONSPOT_MAXPR
            if ops and ops[0][0] <= maxpr:
                pr, op = ops[0]; actions[i] = to_action(op, inv); claimed_tiles.add(pos); done_units.add(i)
                tasks_by_tile[pos] = [t for t in tasks_by_tile[pos] if t[1] != op]
    for i in range(n):
        if i in done_units: continue
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
        # 창고 타일 위에서 산물을 들고 있으면 공짜로 하역 (즉시 판매 가능)
        if SHED_DROP and pos in SHED_TILES:
            pi = [(inv.get(k, 0), k) for k in ("MILK", "WOOL", "STRAWBERRY", "MELON", "EGG", "CARROT", "TOMATO") if inv.get(k, 0) > 0]
            if FERT_HAUL and inv.get("FERTILIZER", 0) > 0 and not any(t[1] == "FERTILIZE" for (x, y) in route for t in tasks_by_tile.get((x, y), [])):
                pi.append((inv["FERTILIZER"], "FERTILIZER"))
            if pi:
                q, k = max(pi); actions[i] = ["PLACE", k, q]; continue
        pk = pickups(s, mem, i, route, tasks_by_tile)
        if pk: actions[i] = pk; continue
        # 저녁 하역: hour>=20 이면 산물을 든 유닛은 창고로 가서 DROP (당일 판매용)
        prod_items = [(inv.get(k, 0), k) for k in ("MILK", "WOOL", "STRAWBERRY", "MELON", "EGG", "CARROT", "TOMATO") if inv.get(k, 0) > 0]
        if FERT_HAUL and inv.get("FERTILIZER", 0) > 0 and not any(t[1] == "FERTILIZE" for (x, y) in route for t in tasks_by_tile.get((x, y), [])):
            prod_items.append((inv["FERTILIZER"], "FERTILIZER"))
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
        if ops and pos not in claimed_tiles and ops[0][0] <= (RUSH_ONSPOT if rush_on else ONSPOT_MAXPR):
            pr, op = ops[0]; actions[i] = to_action(op, inv); claimed_tiles.add(pos)
            tasks_by_tile[pos] = [t for t in tasks_by_tile[pos] if t[1] != op]
            continue
        # 2) 내 구역에서 가장 가까운 미처리 타일
        best = None; bd = None
        cand = list(route)
        if RUSH_GLOBAL:
            cand += [xy for xy, lst in tasks_by_tile.items() if xy not in route and any(t[0] == 0 for t in lst)]
        for (x, y) in cand:
            if (x, y) in claimed_tiles: continue
            po = pending_ops(s, x, y, inv, tasks_by_tile)
            if po:
                d = dist(pos, (x, y)) + PRW * po[0][0]
                if bd is None or d < bd: best, bd = (x, y), d
        # 2a) 밀이 없는 유닛에게 '창고에서 밀 가져오기'를 FEED 우선순위(1)의 가상 작업으로 경쟁시킨다
        if FETCH and s.hour <= 22 and inv.get("WHEAT", 0) == 0:
            n_unfed = sum(1 for lst in tasks_by_tile.values() for t in lst if t[1] == "FEED")
            carried_w = sum(iv.get("WHEAT", 0) for iv in s.invs)
            avail = s.shed.get("WHEAT", 0) - step_claims.get("WHEAT", 0)
            if n_unfed > carried_w and avail > 0:
                shed_t = min(SHED_TILES, key=lambda p: dist(pos, p))
                fscore = dist(pos, shed_t) + PRW * 1 + 1
                if bd is None or fscore < bd:
                    if pos in SHED_TILES:
                        take = min(n_unfed - carried_w, avail)
                        step_claims["WHEAT"] = step_claims.get("WHEAT", 0) + take
                        actions[i] = ["PICKUP", "WHEAT", take]
                    else:
                        actions[i] = step_toward(pos, shed_t)
                    continue
        # 2b) 구역이 끝났거나, 든 산물 가치가 크면(아침 판매→당일 재투자) 창고에 하역
        pval = sum(q * s.prices.get(k, 0) for q, k in prod_items)
        if (best is None and produce >= 2 and s.hour >= 8) or (pval >= HAUL_V and s.hour <= 16) or (MELON_RUSH and inv.get("MELON", 0) >= 3):
            tgt = min(SHED_TILES, key=lambda p: dist(pos, p))
            if pos in SHED_TILES:
                q, k = max(prod_items); actions[i] = ["PLACE", k, q]
            else: actions[i] = step_toward(pos, tgt)
            continue
        # 3) 없으면 전역에서 가장 가까운 타일
        if best is None:
            for (x, y), lst in tasks_by_tile.items():
                if (x, y) in claimed_tiles or not lst: continue
                po = pending_ops(s, x, y, inv, tasks_by_tile)
                if po:
                    d = dist(pos, (x, y)) + 2 + PRW * po[0][0]
                    if bd is None or d < bd: best, bd = (x, y), d
        if best is None:
            # 할 일이 없고, 아직 못 먹인 동물이 있는데 창고에 밀이 있으면 밀을 가지러 간다
            if FETCH and s.hour <= 22 and inv.get("WHEAT", 0) == 0:
                n_unfed = sum(1 for lst in tasks_by_tile.values() for t in lst if t[1] == "FEED")
                carried_w = sum(iv.get("WHEAT", 0) for iv in s.invs)
                avail = s.shed.get("WHEAT", 0) - step_claims.get("WHEAT", 0)
                if n_unfed > carried_w and avail > 0:
                    if pos in SHED_TILES:
                        take = min(n_unfed - carried_w, avail)
                        step_claims["WHEAT"] = step_claims.get("WHEAT", 0) + take
                        actions[i] = ["PICKUP", "WHEAT", take]
                    else:
                        actions[i] = step_toward(pos, min(SHED_TILES, key=lambda p: dist(pos, p)))
            continue
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
        update_hist(s, mem)
        if OPENING_END and s.step < OPENING_END:
            sells = hourly_sells(s)
            if s.hour == 0:
                wq = s.shed.get("WHEAT", 0) - (s.n_animals * 2 + 2)
                if wq > 0 and s.day >= 1: sells.append(["SELL", "WHEAT", wq])
            cash = s.money + sum(int(s.prices.get(o[1], 1) * o[2] * 0.7) for o in sells)
            market = sells + opening_orders(s, mem, cash)
            # 급식 부족분 안전망
            if s.n_animals > 0 and s.hour <= 16:
                unfed = sum(1 for _, _, t in s.animal_tiles if not t.get("fed_today"))
                have = s.shed.get("WHEAT", 0) + sum(i.get("WHEAT", 0) for i in s.invs) + sum(int(o[2]) for o in market if o[0] == "BUY_PRODUCT" and o[1] == "WHEAT")
                need = unfed - have
                left = cash - sum(order_cost(s, o, 0) for o in market if o[0] != "HIRE")
                if need > 0 and left > 0:
                    n = min(need, int(left // (s.prices.get("WHEAT", 30) + 3)))
                    if n > 0: market.append(["BUY_PRODUCT", "WHEAT", n])
        elif s.hour == 0:
            market = daily_market(s, mem)
        else:
            if s.hour == 1:
                market = list(mem.pop("h1_orders", []))
                pending_hire = mem.pop("hire_cost_h1", 0)
            else:
                pending_hire = 0
            if s.day >= 29 and s.hour >= 22:
                for item in PRODUCTS:
                    q = s.shed.get(item, 0)
                    if q > 0: market.append(["SELL", item, q])
            else:
                sells = smart_sells(s, mem) if SMART_SELL else hourly_sells(s)
                if sum(s.shed.values()) >= 80 and s.shed.get("FERTILIZER", 0) > 0:
                    sells.append(["SELL", "FERTILIZER", s.shed["FERTILIZER"]])
                market += sells
                cash = s.money - pending_hire + sum(int(s.prices.get(o[1], 1) * o[2] * 0.7) for o in sells)
                market += buy_plan(s, mem, cash)
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
    except Exception as e:
        _S.setdefault("errs", []).append((int(_get(obs, "step", -1) or -1), repr(e)[:200]))
        try:
            hands = list(_get(_get(obs, "farms")[int(_get(obs, "player", 0) or 0)], "hands", []) or [])
        except Exception:
            hands = []
        return {"farmer": ["PASS"], "hands": [["PASS"] for _ in hands], "market": []}


_submission_agent = agent
