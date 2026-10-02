# kaggriculture planner v3 (9/26): v2 execution engine + market-projection planning (mktmodel).
# Crops / animals / land / holds are chosen daily from projected prices instead of a fixed calendar.
import math
import planner_v2 as V2
from planner_v2 import ANIMALS, CROPS, PRODUCTS, SHED_TILES, _dist, P
import mktmodel as MM

P.update(dict(
    lab=4.0,            # $ per unit-step of labour in valuations
    min_value=6.0,      # $/tile-day floor for planting
    opp_mirror=0.5,     # prior: opponent adds this fraction of our planned supply
    hold_from=18,       # day from which hinge products may be held for the final dump
    hold_gain=1.4,      # hold if projected dump price > hold_gain * price now
    shed_soft=88,       # keep held stock under this (shed cap 100, wheat/fert reserve on top)
    feed_days=5,
    last_day_hands=14,
    v2_land=False,
))

_CUR = {}
HOLD = ("CARROT", "TOMATO")


def _targets_hook(day, money, n_tiles):
    return _CUR.get("targets") or V2._plan_targets_orig(day, money, n_tiles)


V2._plan_targets_orig = V2.plan_targets
V2.plan_targets = _targets_hook


class Planner3(V2.Planner):
    def __init__(self, player):
        super().__init__(player)
        self.mm = MM.MarketModel(); self.last_sells = {}; self.plan_day = -1
        self.targets = None; self.hold = set()

    # ---------- expected future supply from what we already own ----------
    def ledger_existing(self):
        led = {k: [] for k in PRODUCTS}   # item -> list of (sale_day, units)
        d = self.day
        for pos, t in self.plants:
            c = CROPS[t["crop"]]; pd = int(t.get("planted_day", d)); crop = t["crop"]
            if not c["ongoing"]:
                hd = max(d, pd + (10 if crop == "MELON" else c["maxday"]))
                if hd <= 29:
                    led[crop].append((29 if crop in HOLD else hd, 4 if crop == "CARROT" else (6 if crop == "MELON" else 4)))
            else:
                for k in range(c["maxy"]):
                    hd = pd + c["first"] + k * c["interval"]
                    if d <= hd <= 29:
                        led[crop].append((29 if crop in HOLD else hd, 2))
        for pos, t in self.animals:
            a = ANIMALS[t["animal"]]; pd = int(t.get("placed_day", d)); prod = a["product"]
            k = 0
            while True:
                hd = pd + a["first"] + k * a["interval"]; k += 1
                if hd > 29:
                    break
                if hd >= d:
                    led[prod].append((29 if prod in HOLD else hd, 1 + a["interval"]))
            led["FERTILIZER"].append((d, 29 - d))
        for k in led:
            led[k].sort()
        return led

    def _extra(self, led, item, sday):
        u = sum(n for sd, n in led[item] if sd <= sday)
        return u * (1.0 + (P["opp_mirror"] if self.day < 4 else 0.2))

    # ---------- valuations ----------
    def crop_value(self, crop, led, d):
        """(value per tile-day, sales list, occupancy days) for planting `crop` today (day d)."""
        c = CROPS[crop]; sales = []
        if not c["ongoing"]:
            hd = d + (10 if crop == "MELON" else c["maxday"])
            if hd > 29:
                return None
            sales.append((hd, 4 if crop == "CARROT" else (6 if crop == "MELON" else 4)))
            L = hd - d + 1; labor = {"WHEAT": 5, "CARROT": 5, "MELON": 9}[crop]
        else:
            for k in range(c["maxy"]):
                hd = d + c["first"] + k * c["interval"]
                if hd <= 29:
                    sales.append((hd, 2))
            if not sales:
                return None
            L = min(sales[-1][0], 29) - d + 1; labor = (L + 1) // 2 + 2 * len(sales) + 2
        rev = 0
        for hd, n in sales:
            sd = 29 if crop in HOLD else hd
            rev += self.mm.revenue_at(crop, sd, d, n, extra=self._extra(led, crop, sd))
        val = (rev - c["seed"] - labor * P["lab"]) / L
        return val, [(29 if crop in HOLD else hd, n) for hd, n in sales], L

    def animal_value(self, kind, led, d):
        a = ANIMALS[kind]; prod = a["product"]; sales = []
        k = 0
        while True:
            hd = d + a["first"] + k * a["interval"]; k += 1
            if hd > 29:
                break
            sales.append((29 if prod in HOLD else hd, 1 + a["interval"]))
        if not sales:
            return None
        rev = sum(self.mm.revenue_at(prod, sd, d, n, extra=self._extra(led, prod, sd)) for sd, n in sales)
        days = 29 - d
        fert = self.mm.price_at("FERTILIZER", d + days // 2, d, extra=self._extra(led, "FERTILIZER", 29)) * days * 0.6
        feed = (int(self.prices.get("WHEAT", 30)) + 5) * days
        val = rev + fert - feed - 4 * P["lab"] * days - a["cost"]
        return val, sales

    # ---------- daily plan ----------
    def decide(self):
        d = self.day; led = self.ledger_existing(); cnt = self.counts()
        money = self.money + sum(int(self.prices.get(k, 0)) * int(self.shed.get(k, 0)) for k in PRODUCTS if k not in self.hold) * 0.8
        n_anim = self.animals_total()
        tg = {k: cnt.get(k, 0) for k in list(CROPS) + list(ANIMALS)}
        # feed wheat: keep enough wheat tiles for the animals
        feed_tiles = 0 if d > 23 else min(14, max(8 if d < 20 else 0, math.ceil(n_anim * P["feed_days"] / 4)))
        empties = len(self.empty) - sum(int(self.shed.get(k, 0)) for k in ANIMALS)
        budget = money - (150 if d == 0 else 60 * n_anim + 100)
        # animals first (structures near the shed), limited per day; static floors like the public build, model adds above
        bought = 0
        floors = dict(COW=2 if d < 2 else (3 if d < 4 else (4 if d < 6 else 6)), SHEEP=2 if d < 8 else (4 if d < 9 else (5 if d < 10 else 6)), GOOSE=0 if d < 10 else (2 if d < 11 else 3))
        for _ in range(4):
            best = None
            for kind in ANIMALS:
                if tg[kind] >= 6:
                    continue
                av = self.animal_value(kind, led, d)
                if av is None:
                    continue
                if d < 12 and tg[kind] >= floors[kind]:
                    continue
                v = av[0] + (100000 if tg[kind] < floors[kind] and d <= 14 else 0)
                if best is None or v > best[2]:
                    best = (kind, av, v)
            if best is None or best[2] < ANIMALS[best[0]]["cost"] * 0.5 or budget < ANIMALS[best[0]]["cost"] + 60 or empties <= 1 or d > 22:
                break
            kind, (val, sales), _v = best
            tg[kind] += 1; budget -= ANIMALS[kind]["cost"] + 40; empties -= 1; bought += 1
            for sd, n in sales:
                led[ANIMALS[kind]["product"]].append((sd, n))
            led["FERTILIZER"].append((d, 29 - d))
        # crops for empty tiles
        wheat_need = max(0, feed_tiles - tg["WHEAT"])
        plan = []
        while empties > 0:
            best = None
            for crop in CROPS:
                if crop == "WHEAT" and wheat_need > 0:
                    cv = self.crop_value(crop, led, d)
                    if cv:
                        best = (crop, (cv[0] + 1000, cv[1], cv[2])); break
                cv = self.crop_value(crop, led, d)
                if cv and budget >= CROPS[crop]["seed"] and (best is None or cv[0] > best[1][0]):
                    best = (crop, cv)
            if best is None or best[1][0] < P["min_value"]:
                break
            crop, (val, sales, L) = best
            if crop == "WHEAT" and wheat_need > 0:
                wheat_need -= 1
            tg[crop] += 1; budget -= CROPS[crop]["seed"]; empties -= 1; plan.append((crop, round(val)))
            for sd, n in sales:
                led[crop].append((sd, n))
        # land: worth it if the best crop value on 25 more tiles beats the price
        self.want_land = False
        if empties <= 2 and d <= 22:
            nxt = [q for q in ["NE", "SW", "SE"] if q not in self.quads]
            if nxt:
                price = {"NE": 1000, "SW": 2000, "SE": 4000}[nxt[0]]
                bestv = max([cv[0] for cv in (self.crop_value(c, led, d + 1) for c in CROPS) if cv] or [0])
                if bestv * 20 * min(29 - d, 12) > price * 1.3 and budget > price + 200:
                    self.want_land = True
        # holds for the final dump
        self.hold = set()
        if d >= P["hold_from"]:
            for item in HOLD:
                pnow = int(self.prices.get(item, 0))
                pend = self.mm.price_at(item, 29, d, extra=self._extra(led, item, 29) + int(self.shed.get(item, 0)))
                if pend > P["hold_gain"] * pnow:
                    self.hold.add(item)
        self.targets = tg; self.plan_day = d; self.plan_log = plan
        _CUR["targets"] = tg

    # ---------- market ----------
    def market_orders(self):
        if self.plan_day != self.day and self.hour == 0 or self.targets is None:
            self.decide()
        _CUR["targets"] = self.targets
        orders = super().market_orders()
        # remove held items from the sells (unless the shed is getting full or it is the last day)
        held = sum(int(self.shed.get(k, 0)) for k in self.hold)
        final = self.day >= 29
        if self.hold and not final:
            out = []
            for o in orders:
                if o[0] == "SELL" and o[1] in self.hold:
                    if held > P["shed_soft"]:
                        keep = held - P["shed_soft"]; q = min(o[2], keep); held -= q
                        if q > 0:
                            out.append(["SELL", o[1], q])
                    continue
                out.append(o)
            orders = out
        # land by valuation
        if getattr(self, "want_land", False) and self.hour in (1, 12) and not any(o[0] == "BUY_LAND" for o in orders):
            orders.append(["BUY_LAND"]); self.want_land = False
        # last day: more hands for the harvest+dump
        if self.day == 29 and self.hour == 0:
            orders = [o for o in orders if o[0] != "HIRE"]
            orders = [["HIRE"]] * P["last_day_hands"] + orders
        return orders[:10]

    def act(self, obs):
        self.parse(obs)
        self.mm.update(self.step, self.market, self.shops, self.last_sells)
        out = super().act(obs)
        self.last_sells = {o[1]: min(o[2], int(self.shed.get(o[1], 0))) for o in out["market"] if o[0] == "SELL"}
        return out


_STATE = {}


def kaggle_submission_agent(observation, configuration=None):
    player = int(observation.get("player", 0))
    st = _STATE.get(player)
    if st is None or int(observation.get("step", 0)) == 0:
        st = _STATE[player] = Planner3(player)
    try:
        return st.act(observation)
    except Exception:
        import traceback; traceback.print_exc()
        return {"farmer": ["PASS"], "hands": [], "market": []}


agent = kaggle_submission_agent
