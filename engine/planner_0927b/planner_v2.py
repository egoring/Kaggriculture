# kaggriculture planner v2 (9/26) — self-written farm planner (no recorded routes).
# Engine: every tile has a daily to-do (animal: FEED/CARE/COLLECT/HARVEST; plant: WATER/FERTILIZE/HARVEST; empty: PLANT);
# tiles are clustered into per-unit circuits by proximity with a step budget; the shed is visited to pick up wheat
# and drop produce; everything in the shed is sold the same step (wheat feed reserve excepted).
# Farm plan: cows + sheep + geese for fertilizer/product, melons for the day-10 cash jump, wheat for feed, carrots later.
import math

P = dict(
    max_hands=12,
    min_hands=3,              # fib hire cost: 12 hands = $376/day, 13 = $609, 14 = $986
    wheat_reserve_days=1.5,
    fert_sell_floor=15,
    steps_per_unit=22,
    fert_buy_max=60,           # buy fertilizer for the bonus window when cheaper than this
    use_fert=True,         # planning budget per unit per day (23 available after the hour-0 hire)
)
ANIMALS = {"GOOSE": dict(cost=300, structure="COOP", first=4, interval=1, product="EGG"),
           "COW": dict(cost=400, structure="PASTURE", first=8, interval=2, product="MILK"),
           "SHEEP": dict(cost=500, structure="PASTURE", first=6, interval=3, product="WOOL")}
CROPS = {"WHEAT": dict(seed=10, first=2, maxday=4, ongoing=False, maxy=6),
         "CARROT": dict(seed=20, first=2, maxday=3, ongoing=False, maxy=4),
         "TOMATO": dict(seed=50, first=8, maxday=8, ongoing=True, interval=1, maxy=4),
         "STRAWBERRY": dict(seed=100, first=10, maxday=10, ongoing=True, interval=2, maxy=4),
         "MELON": dict(seed=80, first=10, maxday=12, ongoing=False, maxy=6)}
PRODUCTS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER"]
SHED_TILES = [(4, 4), (5, 4), (4, 5), (5, 5)]
_STATE = {}


def _dist(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _step_toward(pos, tgt):
    dx, dy = tgt[0] - pos[0], tgt[1] - pos[1]
    if abs(dx) >= abs(dy) and dx != 0:
        return ["EAST"] if dx > 0 else ["WEST"]
    if dy != 0:
        return ["SOUTH"] if dy > 0 else ["NORTH"]
    return ["PASS"]


def _nearest_shed(pos):
    return min(SHED_TILES, key=lambda t: _dist(pos, t))


# ---------------- farm plan (targets by day) ----------------
def plan_targets_mhw(day, money, n_tiles, n_tom_shops=0):
    """Calendar reconstructed from mhw's 100 winning games (9/27, medians by day)."""
    t = dict(COW=0, SHEEP=0, GOOSE=0, MELON=0, WHEAT=0, CARROT=0, STRAWBERRY=0, TOMATO=0)
    t["COW"] = 2 if day < 6 else (6 if day < 9 else (7 if day < 12 else 8))
    t["SHEEP"] = 3 if day < 9 else (4 if day < 12 else (5 if day < 20 else 6))
    t["GOOSE"] = 0 if day < 6 else (2 if day < 9 else (3 if day < 10 else (5 if day < 12 else 6)))
    t["MELON"] = 6 if day < 1 else (9 if day < 2 else (11 if day <= 9 else 0))
    t["WHEAT"] = 2 if day < 1 else (6 if day < 7 else (7 if day < 8 else (12 if day < 10 else (17 if day < 11 else (26 if day < 12 else (20 if day < 13 else (16 if day < 17 else (12 if day < 20 else (18 if day < 22 else (24 if day <= 25 else (22 if day <= 26 else (18 if day <= 27 else 0))))))))))))
    t["STRAWBERRY"] = 0 if day < 2 else (2 if day < 3 else (3 if day < 4 else (5 if day < 5 else (8 if day < 6 else (10 if day < 8 else (12 if day < 9 else (13 if day < 10 else (16 if day < 12 else (21 if day < 13 else (25 if day <= 17 else 0))))))))))
    tom_full = min(26, 6 + 4 * n_tom_shops)
    t["TOMATO"] = 0 if day < 10 else (min(2, tom_full) if day < 11 else (min(5, tom_full) if day < 12 else (min(8, tom_full) if day < 17 else (min(10, tom_full) if day < 18 else (tom_full if day <= 19 else 0)))))
    t["CARROT"] = 0 if day < 19 else (2 if day < 24 else (3 if day < 25 else (6 if day < 26 else (11 if day < 27 else (17 if day < 28 else 0)))))
    return t


def plan_targets(day, money, n_tiles):
    if P.get("calendar") == "mhw":
        return plan_targets_mhw(day, money, n_tiles, P.get("n_tom_shops", 0))
    """Target counts of animals and crop tiles, modelled on the public stack's build (6-49 reference dump)."""
    t = dict(COW=0, SHEEP=0, GOOSE=0, MELON=0, WHEAT=0, CARROT=0, STRAWBERRY=0, TOMATO=0)
    t["COW"] = 2 if day < 2 else (3 if day < 4 else (4 if day < 6 else 6))
    t["SHEEP"] = 2 if day < 8 else (4 if day < 9 else (5 if day < 10 else 6))
    t["GOOSE"] = 0 if day < 10 else (2 if day < 11 else (3 if day < 12 else 5))
    t["MELON"] = 12 if day <= 9 else 0
    t["WHEAT"] = 8 if day < 10 else (12 if day < 11 else (21 if day < 12 else (24 if day <= 25 else (30 if day <= 26 else 0))))
    t["STRAWBERRY"] = 0 if day < 5 else (4 if day < 6 else (12 if day < 7 else (15 if day < 8 else (19 if day < 11 else (32 if day <= 21 else (26 if day <= 23 else (13 if day <= 25 else 0)))))))
    t["CARROT"] = 0 if day < 15 else (2 if day < 21 else (6 if day < 23 else (14 if day < 25 else (25 if day < 26 else (33 if day < 28 else 0)))))
    t["TOMATO"] = 0
    return t


class Planner:
    def __init__(self, player):
        self.player = player
        self.scripts = []; self.script_pos = []; self.script_day = -1

    # ---------- parsing ----------
    def parse(self, obs):
        self.obs = obs
        self.step = int(obs["step"]); self.day = self.step // 24; self.hour = self.step % 24
        farm = obs["farms"][self.player]
        self.farm = farm; self.money = float(farm["money"]); self.tiles = farm["tiles"]
        self.private = obs["private"]; self.shed = dict(self.private.get("shed") or {})
        self.seeds = dict(self.private.get("seeds") or {})
        self.invs = [dict(x) for x in (self.private.get("inventories") or [{}])]
        self.units = [tuple(farm["farmer"])] + [tuple(h) for h in farm["hands"]]
        while len(self.invs) < len(self.units):
            self.invs.append({})
        self.market = obs["market"]; self.prices = dict(self.market.get("prices") or {})
        self.quads = list(farm.get("unlocked_quadrants") or ["NW"])
        self.shops = list((obs.get("town") or {}).get("unlocked_shops") or [])
        P["n_tom_shops"] = sum(sh in ("PIZZA_SHOP", "FARMERS_MARKET") for sh in self.shops)
        self.animals = []; self.empty = []; self.weeds = []; self.plants = []; self.structs = []
        for y in range(10):
            for x in range(10):
                t = self.tiles[y][x]
                if t == "LOCKED":
                    continue
                if t is None:
                    self.empty.append((x, y))
                elif isinstance(t, dict):
                    if "animal" in t:
                        self.animals.append(((x, y), t))
                    elif t.get("kind") == "PLANT":
                        self.plants.append(((x, y), t))
                    elif t.get("kind") == "WEED":
                        self.weeds.append((x, y))
                    elif t.get("kind") in ("COOP", "PASTURE"):
                        self.structs.append(((x, y), t["kind"]))
        self.n_tiles = 25 * len(self.quads)

    def counts(self):
        c = {}
        for _, t in self.animals:
            c[t["animal"]] = c.get(t["animal"], 0) + 1
        for k in ANIMALS:
            c[k] = c.get(k, 0) + int(self.shed.get(k, 0)) + sum(int(inv.get(k, 0)) for inv in self.invs)
        for _, t in self.plants:
            c[t["crop"]] = c.get(t["crop"], 0) + 1
        return c

    def animals_total(self):
        return len(self.animals) + sum(int(self.shed.get(k, 0)) for k in ANIMALS) + sum(int(inv.get(k, 0)) for inv in self.invs for k in ANIMALS)

    # ---------- tile to-do ----------
    def plant_ready(self, t):
        c = CROPS[t["crop"]]; age = self.day - int(t.get("planted_day", self.day)); y = int(t.get("yield_units", 0))
        if y <= 0 or age < c["first"]:
            return False
        if c["ongoing"]:
            k = age + 1 - c["first"]      # production tonight if k % interval == 0 and k // interval < maxy
            last_done = (age - c["first"]) // c["interval"] >= c["maxy"] - 1
            gain = 2 if int(t.get("fertilized_until_day", -1)) >= self.day else 1
            prod_tonight = k >= 0 and k % c["interval"] == 0 and k // c["interval"] < c["maxy"]
            return y >= 4 or last_done or self.day >= 27 or (prod_tonight and y + gain > 4)
        return y >= c["maxy"] or age >= c["maxday"] or (t["crop"] == "WHEAT" and y >= 5)

    def tile_todo(self, pos):
        """Ops still to do today on this tile, in execution order."""
        t = self.tiles[pos[1]][pos[0]]
        ops = []
        if isinstance(t, dict) and "animal" in t:
            if not t["fed_today"]:
                ops.append("FEED")
            if not t["cared_today"]:
                ops.append("CARE")
            if t.get("fertilizer_available") and int(self.prices.get("FERTILIZER", 100)) >= P.get("collect_min_price", 25):
                ops.append("COLLECT_FERTILIZER")
            if t.get("yield_units", 0) > 0:
                ops.append("HARVEST")
        elif isinstance(t, dict) and t.get("kind") == "PLANT":
            c = CROPS[t["crop"]]; age = self.day - int(t.get("planted_day", self.day))
            cu = int(t.get("consecutive_unwatered", 0))
            if c["ongoing"]:
                # production nights: age+1-first >= 0 and divisible by interval, at most maxy productions
                k = age + 1 - c["first"]
                prod_tonight = k >= 0 and k % c["interval"] == 0 and k // c["interval"] < c["maxy"]
                fwin = c["first"] - 1 <= age <= c["first"] - 1 + c["interval"] * (c["maxy"] - 1)
                need_water = cu >= 1 or prod_tonight
            else:
                win0 = (c["maxday"] + 1) // 2
                fwin = win0 <= age <= c["maxday"] and (t["crop"] == "CARROT" or (t["crop"] == "WHEAT" and self.day >= 4 and int(self.prices.get("FERTILIZER", 100)) <= P.get("wheat_fert_max", 70)))
                need_water = cu >= 1 or (win0 <= age <= c["maxday"] and int(t.get("yield_units", 0)) < c["maxy"])
            if fwin and int(t.get("fertilized_until_day", -1)) < self.day and P.get("use_fert", True):
                ops.append("FERTILIZE")
            if not t["watered_today"] and need_water:
                ops.append("WATER")
            if self.plant_ready(t) or (t["crop"] == "MELON" and age >= c["first"] and int(t.get("yield_units", 0)) >= c["maxy"] - 1 and not t["watered_today"]):
                ops.append("HARVEST")
        return ops

    # ---------- daily circuits ----------
    def make_day_scripts(self, extra=0):
        n = len(self.units) + extra
        units_all = list(self.units) + [(4, 4)] * extra
        self._units_backup = self.units; self.units = units_all
        todo = {}
        for pos, t in self.animals:
            todo[pos] = self.tile_todo(pos)
        for pos, t in self.plants:
            todo[pos] = self.tile_todo(pos)
        # planting plan for empty tiles
        cnt = self.counts(); tgt = plan_targets(self.day, self.money, self.n_tiles)
        reserve_tiles = int(sum(self.shed.get(k, 0) for k in ANIMALS)) + sum(int(inv.get(k, 0)) for inv in self.invs for k in ANIMALS)
        empties = sorted(self.empty, key=lambda p: _dist(p, (4, 4)))
        plant_list = []
        seeds = dict(self.seeds)
        for crop in ("MELON", "STRAWBERRY", "TOMATO", "WHEAT", "CARROT"):
            need = tgt.get(crop, 0) - cnt.get(crop, 0)
            while need > 0 and seeds.get(crop, 0) > 0 and len(empties) > reserve_tiles:
                p = empties.pop(reserve_tiles) if crop == "MELON" else empties.pop()   # melons near the shed (day-10 race), other crops far
                plant_list.append((p, crop)); seeds[crop] -= 1; need -= 1
        for p, crop in plant_list:
            todo[p] = ["PLANT:" + crop, "WATER"]   # a plant unwatered on its planting day becomes a weed at midnight
        for p in self.weeds[: (len(self.weeds) if len(self.empty) < 6 else 4)]:
            todo[p] = ["DIG"]
        tiles = [p for p, ops in todo.items() if ops]
        def value(p):
            ops = todo[p]; t = self.tiles[p[1]][p[0]]
            v = 0
            if "HARVEST" in ops:
                if isinstance(t, dict) and "animal" in t:
                    v += 60
                else:
                    crop = t.get("crop") if isinstance(t, dict) else ""
                    v += {"MELON": 250, "STRAWBERRY": 150, "WHEAT": 60, "CARROT": 60, "TOMATO": 80}.get(crop, 50)
            if "FEED" in ops:
                v += 120 if (isinstance(t, dict) and int(t.get("consecutive_unfed", 0)) >= 1) else 90
            if "WATER" in ops:
                v += 100 if (isinstance(t, dict) and int(t.get("consecutive_unwatered", 0)) >= 1) else 40
            if any(o.startswith("PLANT") for o in ops):
                v += 30
            if "CARE" in ops:
                v += 15
            if "COLLECT_FERTILIZER" in ops:
                v += 15
            if "DIG" in ops:
                v += 5
            return v
        tiles.sort(key=lambda p: -value(p))
        # capacity-limited tile set (highest value first), then proximity round-robin clustering
        cap_total = n * P["steps_per_unit"] - 3 * n
        chosen = []; acc = 0
        for p in tiles:
            c = len(todo[p]) + 2
            if False:
                continue
            chosen.append(p); acc += c
        cur = [self.units[i] for i in range(n)]; used = [0] * n; chunks = [[] for _ in range(n)]
        wheat_need = [0] * n; fert_need = [0] * n
        if P.get("zones", True) and n > 1 and chosen:
            # two tiers: animal units (small groups near the shed, deliver early) + crop units (row bands)
            def is_anim(p):
                t = self.tiles[p[1]][p[0]]
                return isinstance(t, dict) and "animal" in t
            anim = [p for p in chosen if is_anim(p)] if P.get("two_tier", False) else []
            crops = [p for p in chosen if p not in anim]
            self.anim_units = 0
            if anim and n >= 3:
                per = P.get("animals_per_unit", 3)
                A = min(n - 1, max(1, math.ceil(len(anim) / per)))
                self.anim_units = A
                anim_order = sorted(anim, key=lambda p: (p[1] // 2, p[0] if (p[1] // 2) % 2 == 0 else -p[0], p[1]))
                size = math.ceil(len(anim_order) / A)
                for i in range(A):
                    grp = anim_order[i * size:(i + 1) * size]
                    hv = [p for p in grp if "HARVEST" in todo[p]]
                    chunks[i] = ([("HV", p) for p in hv] + ["DROP"] if hv else []) + grp
                    if grp:
                        chunks[i].append("DROP")
                units_c = list(range(A, n))
            else:
                units_c = list(range(n))
            order = sorted(crops, key=lambda p: (p[1] // 2, p[0] if (p[1] // 2) % 2 == 0 else -p[0], p[1]))
            cost = {p: len(todo[p]) + 1.5 for p in order}
            nc = len(units_c); total = sum(cost.values()); target = total / max(1, nc)
            gi = 0; acc = 0.0
            for p in order:
                if gi < nc - 1 and acc + cost[p] / 2 > target * (gi + 1):
                    gi += 1
                chunks[units_c[gi]].append(p); acc += cost[p]
            for i in range(n):
                for p in chunks[i]:
                    if p == "DROP" or (isinstance(p, tuple) and len(p) == 2 and p[0] == "HV"):
                        continue
                    if "FEED" in todo[p]:
                        wheat_need[i] += 1
                    if "FERTILIZE" in todo[p]:
                        fert_need[i] += 1
            self.dropped = 0
        else:
            crit = set(p for p in chosen if value(p) >= 90)
            for phase in (crit, set(chosen) - crit):
                left = set(phase); progress = True
                while left and progress:
                    progress = False
                    for i in range(n):
                        if not left:
                            break
                        p = min(left, key=lambda q: (_dist(cur[i], q), q))
                        cost = _dist(cur[i], p) + len(todo[p])
                        if used[i] + cost + 2 > P["steps_per_unit"] and chunks[i]:
                            continue
                        left.remove(p); chunks[i].append(p); used[i] += cost; cur[i] = p; progress = True
                        if "FEED" in todo[p]:
                            wheat_need[i] += 1
                        if "FERTILIZE" in todo[p]:
                            fert_need[i] += 1
                self.dropped = len(left)
        for i in range(n):
            pts = chunks[i]
            def ripe_today(p):
                t = self.tiles[p[1]][p[0]]
                if isinstance(t, dict) and "animal" in t:
                    return int(t.get("consecutive_unfed", 0)) >= 1 or int(t.get("yield_units", 0)) >= 3
                if not (isinstance(t, dict) and t.get("kind") == "PLANT"):
                    return False
                c = CROPS[t["crop"]]; age = self.day - int(t.get("planted_day", self.day)); y = int(t.get("yield_units", 0))
                if int(t.get("consecutive_unwatered", 0)) >= 1:
                    return True
                if t["crop"] == "MELON":
                    return age >= 6
                return "HARVEST" in todo[p] and t["crop"] in ("STRAWBERRY", "TOMATO")
            self._ripe = ripe_today
            if any(isinstance(p, tuple) and len(p) == 2 and p[0] == "HV" for p in pts) or (pts and pts[0] == "DROP"):
                pass   # animal unit: keep the sweep structure
            else:
                has_drop = "DROP" in pts
                plain = [p for p in pts if p != "DROP"]
                r = self._route(plain, self.units[i])
                hv_n = sum(1 for p in r if self._ripe(p))
                if hv_n and len(r) > hv_n and P.get("drop_after_ripe", False):
                    r = r[:hv_n] + ["DROP"] + r[hv_n:]
                chunks[i] = r + (["DROP"] if has_drop else [])
        # rebalance: move tiles from overloaded routes to the lightest ones
        def rcost(i):
            r = [p for p in chunks[i] if p != "DROP" and not (isinstance(p, tuple) and len(p) == 2 and p[0] == "HV")]; c = 0; cur = self.units[i]
            for p in r:
                c += _dist(cur, p) + len(todo[p]); cur = p
            return c + _dist(cur, _nearest_shed(cur)) + 2 + (1 if wheat_need[i] else 0) + (1 if fert_need[i] else 0)
        A0 = getattr(self, "anim_units", 0)
        for _ in range(30):
            costs = [rcost(i) for i in range(n)]
            cu = list(range(A0, n)) if n - A0 >= 2 else list(range(n))
            hi = max(cu, key=lambda i: costs[i]); lo = min(cu, key=lambda i: costs[i])
            hi_t = [p for p in chunks[hi] if p != "DROP"]; lo_t = [p for p in chunks[lo] if p != "DROP"]
            if costs[hi] <= P["steps_per_unit"] or costs[lo] >= P["steps_per_unit"] - 5 or len(hi_t) <= 1:
                break
            # move the tile of hi that is closest to lo's route (or the shed)
            anchor = lo_t[-1] if lo_t else self.units[lo]
            p = min(hi_t, key=lambda q: _dist(anchor, q))
            chunks[hi].remove(p); chunks[lo].append(p)
            for i in (hi, lo):
                chunks[i] = self._route([q for q in chunks[i] if q != "DROP"], self.units[i])
                wheat_need[i] = sum(1 for q in chunks[i] if q != "DROP" and "FEED" in todo[q]); fert_need[i] = sum(1 for q in chunks[i] if q != "DROP" and "FERTILIZE" in todo[q])
        self.scripts = []
        shed_animals = int(sum(int(self.shed.get(k, 0)) for k in ANIMALS))
        fetch_order = sorted(range(n), key=lambda i: _dist(self.units[i], (4, 4)))
        fetch = {}
        for i in fetch_order:
            if shed_animals <= 0 or self.day >= 29:
                break
            fetch[i] = min(2, shed_animals); shed_animals -= fetch[i]
        for i in range(n):
            sc = []
            if i in fetch:
                sc.append(("FETCH_ANIMAL", fetch[i]))
            hv_first = bool(chunks[i]) and isinstance(chunks[i][0], tuple) and len(chunks[i][0]) == 2 and chunks[i][0][0] == "HV"
            if not hv_first:
                if wheat_need[i] > 0:
                    sc.append(("PICKUP_WHEAT", wheat_need[i]))
                if fert_need[i] > 0:
                    sc.append(("PICKUP_FERT", fert_need[i]))
            first_drop_done = False
            for p in chunks[i]:
                if p == "DROP":
                    sc.append(("DROP",))
                    if hv_first and not first_drop_done:
                        first_drop_done = True
                        if wheat_need[i] > 0:
                            sc.append(("PICKUP_WHEAT", wheat_need[i]))
                        if fert_need[i] > 0:
                            sc.append(("PICKUP_FERT", fert_need[i]))
                    continue
                if isinstance(p, tuple) and len(p) == 2 and p[0] == "HV":
                    sc.append(("VISIT", p[1], ["HARVEST"])); continue
                sc.append(("VISIT", p, [o for o in todo[p] if not (o == "HARVEST" and any(q == ("HV", p) for q in chunks[i]))]))
            sc.append(("DROP",))
            self.scripts.append(sc)
        self.script_pos = [0] * n; self.script_day = self.day
        self.units = self._units_backup

    def _route(self, pts, start):
        def is_anim(p):
            t = self.tiles[p[1]][p[0]]
            return isinstance(t, dict) and "animal" in t
        an = [p for p in pts if is_anim(p)] if P.get("animals_first", False) else []
        hv = [p for p in pts if p not in an and self._ripe(p)]
        rest = [p for p in pts if p not in an and p not in hv]
        order = []; c = start
        for group in (an, hv, rest):
            while group:
                p = min(group, key=lambda q: _dist(c, q)); group.remove(p); order.append(p); c = p
            if group is an and an is not None and order and P.get("animals_first", False) and (hv or rest):
                order.append("DROP")   # deliver animal produce before the crop leg (early sales win the lockstep)
        return order

    def assign(self):
        n = len(self.units)
        plan_hour = 2 if (self.day == 0 and any(int(v) > 0 for v in self.seeds.values()) is False) else 1
        if self.hour < plan_hour:
            self.scripts = [[("DROP",)] for _ in range(n)]; self.script_pos = [0] * n; self.script_day = -1
        elif self.script_day != self.day or len(self.scripts) < n:
            extra = getattr(self, "hire_more", 0) if (self.hour == 1 and getattr(self, "hire_more_day", -1) == self.day) else 0
            self.make_day_scripts(extra)
        acts = [None] * n
        taken = set()
        wheat = [int(inv.get("WHEAT", 0)) for inv in self.invs]
        fert = [int(inv.get("FERTILIZER", 0)) for inv in self.invs]
        carry = [sum(v for k, v in inv.items() if k in PRODUCTS and k != "WHEAT") for inv in self.invs]
        animals_carried = [{k: int(inv.get(k, 0)) for k in ANIMALS if inv.get(k, 0)} for inv in self.invs]
        shed_wheat = int(self.shed.get("WHEAT", 0)); shed_fert = int(self.shed.get("FERTILIZER", 0))
        for i in range(n):
            pos = self.units[i]; sh = _nearest_shed(pos); dsh = _dist(pos, sh)
            # carrying an animal: place it (build a structure first if needed)
            if animals_carried[i]:
                kind = next(iter(animals_carried[i])); st = ANIMALS[kind]["structure"]
                free_structs = [p for p, k in self.structs if k == st and p not in taken]
                if free_structs:
                    tgt = min(free_structs, key=lambda p: _dist(pos, p)); taken.add(tgt)
                    acts[i] = ["PLACE", kind] if pos == tgt else _step_toward(pos, tgt)
                    continue
                empties = [p for p in self.empty if p not in taken]
                if empties:
                    tgt = min(empties, key=lambda p: (_dist(p, (4, 4)), _dist(pos, p))); taken.add(tgt)
                    acts[i] = ["BUILD_" + st] if pos == tgt else _step_toward(pos, tgt)
                    continue
            sc = self.scripts[i]; k = self.script_pos[i]
            hi_val = sum(int(self.invs[i].get(x, 0)) * int(self.prices.get(x, 0)) for x in PRODUCTS if x != "WHEAT")
            # end of day: bring the produce home before the midnight auto-drop (shed cap 100 discards the overflow)
            if hi_val >= 300 and self.hour >= 23 - dsh and (k >= len(sc) or sc[k][0] != "DROP"):
                acts[i] = ["DROP"] if dsh == 0 else _step_toward(pos, sh)
                continue
            feeds_left = any(it[0] == "VISIT" and "FEED" in it[2] for it in sc[k:])
            if hi_val >= P.get("detour_value", 900) and (k >= len(sc) or sc[k][0] != "DROP") and dsh <= 4 and not feeds_left:
                acts[i] = ["DROP"] if dsh == 0 else _step_toward(pos, sh)
                continue
            while k < len(sc) and acts[i] is None:
                item = sc[k]
                if item[0] in ("PICKUP_WHEAT", "PICKUP_FERT"):
                    if item[0] == "PICKUP_WHEAT":
                        have, avail, name = wheat[i], shed_wheat, "WHEAT"
                    else:
                        have, avail, name = fert[i], shed_fert, "FERTILIZER"
                    need = min(item[1] - have, avail)
                    if need <= 0:
                        k += 1; continue
                    if dsh == 0:
                        acts[i] = ["PICKUP", name, need]; k += 1
                        if name == "WHEAT":
                            shed_wheat -= need
                        else:
                            shed_fert -= need
                    else:
                        acts[i] = _step_toward(pos, sh)
                elif item[0] == "FETCH_ANIMAL":
                    kinds = [kk for kk in ANIMALS if int(self.shed.get(kk, 0)) > 0]
                    if not kinds or animals_carried[i]:
                        k += 1; continue
                    if dsh == 0:
                        kind = kinds[0]; q = min(int(self.shed.get(kind, 0)), item[1])
                        acts[i] = ["PICKUP", kind, q]; self.shed[kind] = int(self.shed.get(kind, 0)) - q; k += 1
                    else:
                        acts[i] = _step_toward(pos, sh)
                elif item[0] == "VISIT":
                    tgt, ops = item[1], item[2]
                    if pos != tgt:
                        acts[i] = _step_toward(pos, tgt); break
                    # execute the next applicable op on this tile
                    live = self.tile_todo(tgt)
                    t = self.tiles[tgt[1]][tgt[0]]
                    op = None
                    for o in list(ops):
                        if o.startswith("PLANT:"):
                            crop = o.split(":")[1]
                            if t is None and int(self.seeds.get(crop, 0)) > 0:
                                op = ["PLANT", crop]; self.seeds[crop] = int(self.seeds.get(crop, 0)) - 1
                            ops.remove(o); break
                        if o == "DIG":
                            ops.remove(o)
                            if isinstance(t, dict) and t.get("kind") == "WEED":
                                op = ["DIG"]
                            break
                        if o not in live and not (o == "WATER" and t is None):
                            ops.remove(o); continue
                        if o == "FEED" and wheat[i] <= 0:
                            ops.remove(o); continue
                        if o == "FERTILIZE" and fert[i] <= 0:
                            ops.remove(o); continue
                        op = [o]; ops.remove(o)
                        if o == "FEED":
                            wheat[i] -= 1
                        if o == "FERTILIZE":
                            fert[i] -= 1
                        break
                    if op is None:
                        k += 1; continue
                    acts[i] = op
                elif item[0] == "DROP":
                    if carry[i] <= 0 and wheat[i] <= 0:
                        k += 1; continue
                    if dsh == 0:
                        acts[i] = ["DROP"]; k += 1
                    else:
                        acts[i] = _step_toward(pos, sh)
                else:
                    k += 1
            self.script_pos[i] = k
            if acts[i] is not None:
                continue
            # extras after the script: fetch animals from the shed, otherwise idle near the shed
            if any(int(self.shed.get(kk, 0)) > 0 for kk in ANIMALS) and self.day < 29:
                if dsh == 0:
                    kind = next(kk for kk in ANIMALS if int(self.shed.get(kk, 0)) > 0)
                    q = min(int(self.shed.get(kind, 0)), 2)
                    acts[i] = ["PICKUP", kind, q]; self.shed[kind] = int(self.shed.get(kind, 0)) - q
                else:
                    acts[i] = _step_toward(pos, sh)
                continue
            acts[i] = ["DROP"] if (dsh == 0 and (carry[i] > 0 or wheat[i] > 0)) else (_step_toward(pos, sh) if dsh > 1 else ["PASS"])
        return acts

    def fert_reserve(self):
        """Fertilizer to keep for tomorrow's FERTILIZE ops: plants entering/inside their bonus window."""
        n = 0
        for _, t in self.plants:
            c = CROPS[t["crop"]]; age = self.day + 1 - int(t.get("planted_day", self.day))
            if c["ongoing"]:
                fwin = c["first"] - 1 <= age <= c["first"] - 1 + c["interval"] * (c["maxy"] - 1)
            else:
                fwin = (c["maxday"] + 1) // 2 <= age <= c["maxday"] and (t["crop"] == "CARROT" or (t["crop"] == "WHEAT" and self.day >= 4 and int(self.prices.get("FERTILIZER", 100)) <= P.get("wheat_fert_max", 70)))
            if fwin and int(t.get("fertilized_until_day", -1)) < self.day + 1:
                n += 1
        return min(n, 12) if (P.get("use_fert", True) and self.money >= 500 and self.day >= 12) else 0

    # ---------- market ----------
    def market_orders(self):
        orders = []
        cnt = self.counts(); tgt = plan_targets(self.day, self.money, self.n_tiles)
        n_anim = self.animals_total()
        if self.hour == 0:
            # workload = today's tile ops (+2 travel each) + plantings; hands = ceil(work / steps_per_unit) - farmer
            work = 6
            for pos, _ in self.animals + self.plants:
                k = len(self.tile_todo(pos))
                if k:
                    work += k + P.get("travel_est", 2.5)
            tg = plan_targets(self.day, self.money, self.n_tiles)
            for crop in ("MELON", "STRAWBERRY", "WHEAT", "CARROT", "TOMATO"):
                work += 4 * max(0, min(tg.get(crop, 0) - cnt.get(crop, 0), int(self.seeds.get(crop, 0)) + (12 if self.hour == 0 and self.day == 0 else 0)))
            short = getattr(self, "shortfall", 0)
            want = math.ceil(work / P["steps_per_unit"]) - 1 + (1 if short > 0 else 0) + (1 if short > 4 else 0)
            cap = P["max_hands"] + (1 if self.day >= 12 and self.money > 4000 else 0) + (1 if self.day >= 18 and self.money > 12000 else 0)
            minh = max(3 if self.day < 4 else (5 if self.day < 8 else P.get("min_hands_late", 9)), math.ceil(n_anim / P.get("animals_per_unit", 3)) + 2)
            if P.get("calendar") == "mhw":
                minh = 4 if self.day < 10 else 11; cap = min(cap, 5 if self.day < 10 else 12)
            want = int(min(cap, max(minh, want)))
            if self.day == 0:
                want = 4
            self.dbg_hire = (work, want, cap, minh, short)
            self.hire_more = max(0, want - 9)
            if self.hire_more > 0:
                self.hire_more_day = self.day
            orders += [["HIRE"]] * min(want, 9)
        elif self.hour == 1 and getattr(self, "hire_more", 0) > 0:
            orders += [["HIRE"]] * self.hire_more; self.hire_more = 0
        reserve = int(n_anim * P["wheat_reserve_days"])
        carried_total = sum(int(v) for inv in self.invs for k, v in inv.items() if k in PRODUCTS)
        if self.hour >= 21 and sum(int(self.shed.get(k, 0)) for k in PRODUCTS) + carried_total > 92:
            reserve = n_anim   # make room for the midnight auto-drop
        sells = []
        for item in PRODUCTS:
            q = int(self.shed.get(item, 0))
            if item == "WHEAT":
                q -= (0 if self.step >= 716 else reserve + 3)
            if item == "FERTILIZER":
                q -= (0 if self.step >= 716 else self.fert_reserve())
                if int(self.prices.get(item, 0)) < P["fert_sell_floor"] and self.step < 716 and sum(self.shed.values()) < 70:
                    q = 0
            if q > 0:
                sells.append(["SELL", item, q])
        sells.sort(key=lambda o: -int(self.prices.get(o[1], 0)) * o[2])
        n_sells0 = len(orders); orders += sells
        money = self.money + sum(int(self.prices.get(o[1], 0)) * o[2] for o in sells) * 0.9
        money -= 0 if self.day == 0 else 100
        # wheat feed
        need_wheat = reserve + (1 if self.day > 0 else 0) - int(self.shed.get("WHEAT", 0))
        wp = int(self.prices.get("WHEAT", 25)) + 3
        cheap = int(self.prices.get("WHEAT", 25)) <= 32
        unfed = sum(1 for _, t in self.animals if not t["fed_today"])
        deficit = unfed + (2 if self.hour == 0 else 0) - int(self.shed.get("WHEAT", 0)) - sum(int(inv.get("WHEAT", 0)) for inv in self.invs)
        if self.day > 0 and self.hour in (0, 1, 12) and deficit > 0 and money > wp:
            q = min(deficit, int(money // wp))
            if q > 0:
                orders.append(["BUY_PRODUCT", "WHEAT", q]); money -= q * wp
                need_wheat -= q
        if need_wheat > 0 and money > wp and self.hour in (0, 12) and self.day > 0 and (cheap or self.day >= 20):
            q = min(need_wheat, 30, int(money // wp))
            if q > 0:
                orders.append(["BUY_PRODUCT", "WHEAT", q]); money -= q * wp
        fr = self.fert_reserve(); fp = int(self.prices.get("FERTILIZER", 100))
        if self.hour in (0, 12) and fr > int(self.shed.get("FERTILIZER", 0)) and fp <= P["fert_buy_max"] and money > 800 and self.day < 28:
            q = min(fr - int(self.shed.get("FERTILIZER", 0)), 20, int((money - 500) // (fp + 3)))
            if q > 0:
                orders.append(["BUY_PRODUCT", "FERTILIZER", q]); money -= q * (fp + 3)
        if (self.hour in (1, 12) or (self.day == 0 and self.hour == 0)) and self.day < 28:
            money -= 30 * n_anim   # tomorrow's feed
            # seeds for the planting plan
            free = len(self.empty) - int(sum(self.shed.get(k, 0) for k in ANIMALS))
            for crop in ("MELON", "STRAWBERRY", "TOMATO", "WHEAT", "CARROT"):
                need = tgt.get(crop, 0) - cnt.get(crop, 0) - int(self.seeds.get(crop, 0))
                need = min(need, free)
                if need > 0 and money > CROPS[crop]["seed"] * need:
                    orders.append(["BUY_SEED", crop, need]); money -= CROPS[crop]["seed"] * need; free -= need
            # land
            for i, qn in enumerate(["NE", "SW", "SE"]):
                if qn in self.quads:
                    continue
                price = [1000, 2000, 4000][i]
                if P.get("v2_land", True) and ((i == 0 and self.day >= 6) or (i == 1 and self.day >= 11) or (i == 2 and self.day >= 17)) and money > price + (1500 if i == 2 else 300) and self.day <= 19:
                    orders.append(["BUY_LAND"]); money -= price
                break
            # animals
            room = len(self.structs) + max(0, len(self.empty) - 4) - int(sum(self.shed.get(k, 0) for k in ANIMALS))
            for kind in ("COW", "SHEEP", "GOOSE"):
                need = tgt.get(kind, 0) - cnt.get(kind, 0)
                q = 0
                marg = 0 if self.day == 0 else 30
                while need > 0 and room > 0 and money > ANIMALS[kind]["cost"] + 2 * marg and q < 4:
                    q += 1; need -= 1; room -= 1; money -= ANIMALS[kind]["cost"] + marg
                if q > 0:
                    orders.append(["BUY_ANIMAL", kind, q])
            if self.day == 0 and self.hour == 0:
                q = min(5, int(money // wp))
                if q > 0:
                    orders.append(["BUY_PRODUCT", "WHEAT", q])
        if len(orders) > 10:
            # purchases first (they only happen at a few hours); sells continue on the next steps anyway
            buys = [o for o in orders if o[0] != "SELL"]; sl = [o for o in orders if o[0] == "SELL"]
            orders = buys + sl
        return orders[:10]

    def act(self, obs):
        self.parse(obs)
        if self.hour == 23:
            self.shortfall = sum(1 for _, t in self.plants if not t["watered_today"] and int(t.get("consecutive_unwatered", 0)) >= 1) + sum(1 for _, t in self.animals if not t["fed_today"])
        acts = self.assign()
        for i, a in enumerate(acts):
            if a and a[0] == "DROP" and self.units[i] in SHED_TILES:
                for k, v in self.invs[i].items():
                    self.shed[k] = int(self.shed.get(k, 0)) + int(v)
        market = self.market_orders()
        return {"farmer": acts[0], "hands": acts[1:], "market": market}


def kaggle_submission_agent(observation, configuration=None):
    player = int(observation.get("player", 0))
    st = _STATE.get(player)
    if st is None or int(observation.get("step", 0)) == 0:
        st = _STATE[player] = Planner(player)
    try:
        return st.act(observation)
    except Exception:
        return {"farmer": ["PASS"], "hands": [], "market": []}


agent = kaggle_submission_agent
