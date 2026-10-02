# Market projection model for kaggriculture (9/26). Prices are a known function of market inventory;
# town shops consume at known rates; the opponent's supply is estimated from observed inventory deltas.
import math

I0 = 10000
MP = {
    "WHEAT":      dict(base=25, T=400, bf="sqrt", bt=0.80, af="log", at=0.20),
    "CARROT":     dict(base=35, T=450, bf="hinge", bt=1.00, af="sqrt", at=0.70),
    "TOMATO":     dict(base=60, T=200, bf="hinge", bt=0.40, af="sqrt", at=0.60),
    "STRAWBERRY": dict(base=120, T=100, bf="sqrt", bt=0.70, af="linear", at=1.60),
    "MELON":      dict(base=250, T=300, bf="log", bt=0.20, af="sq", at=3.60),
    "EGG":        dict(base=50, T=332, bf="hinge", bt=0.40, af="log", at=0.20),
    "MILK":       dict(base=160, T=122, bf="sqrt", bt=0.60, af="linear", at=1.60),
    "WOOL":       dict(base=200, T=105, bf="log", bt=0.20, af="sq", at=3.20),
    "FERTILIZER": dict(base=100, T=200, bf="linear", bt=0.40, af="linear", at=0.40),
}
SHOPS = {
    "BAKERY": ["EGG", "WHEAT"], "PIZZA_SHOP": ["MILK", "TOMATO", "WHEAT"], "BRUNCH_SPOT": ["EGG", "WHEAT", "STRAWBERRY"],
    "YARN_STORE": ["WOOL"], "ICE_CREAM_SHOP": ["STRAWBERRY", "MILK", "WHEAT"], "PET_CAFE": ["CARROT"],
    "SMOOTHIE_SHOP": ["STRAWBERRY", "MILK"], "FARMERS_MARKET": ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY"],
}
PRODUCTS = list(MP)
HINGE = ("CARROT", "TOMATO", "EGG")


def _shape(f, x, T):
    x = max(0.0, x)
    if f == "linear": return x
    if f == "sq": return x * x
    if f == "sqrt": return math.sqrt(x)
    if f == "log": return math.log(1.0 + x)
    if f == "hinge":
        u = x / T
        return u + 8.0 * max(0.0, u - 1.0) ** 2
    return x


def price_x(item, x):
    """Price when market inventory is I0 + x."""
    p = MP[item]; base = p["base"]; T = p["T"]
    if x < 0:
        amp = p["bt"] * base / _shape(p["bf"], T, T)
        v = base + amp * _shape(p["bf"], -x, T)
    else:
        amp = p["at"] * base / _shape(p["af"], T, T)
        v = base - amp * _shape(p["af"], x, T)
    return max(1, int(round(v)))


def revenue_x(item, x, n):
    """Revenue of selling n units starting at inventory offset x (each sale raises x by 1 unless priced $1)."""
    tot = 0
    for _ in range(int(n)):
        pr = price_x(item, x); tot += pr
        if pr > 1:
            x += 1
    return tot


EXP_RATE = {}
for _it in PRODUCTS:
    EXP_RATE[_it] = sum((12 if len(_p) == 1 else 6) for _p in SHOPS.values() if _it in _p) / 8.0


def future_consumption(item, shops, day_now, day_target):
    """Town consumption between now and day_target: known shops + expected future unlocks (days 3,6,...,24)."""
    dd = max(0.0, day_target - day_now)
    tot = shop_rate(item, shops) * dd
    n_known = len(shops)
    for k in range(1, 9):
        u = 3 * k
        if len(shops) >= 8:
            break
        if k <= n_known:
            continue
        if u > day_now and u < day_target:
            tot += EXP_RATE[item] * (day_target - u)
    return tot


def shop_rate(item, shops):
    """Units the town removes per day."""
    r = 0 if item == "FERTILIZER" else 1
    for s in shops:
        prod = SHOPS.get(s, [])
        if item in prod:
            r += (12 if len(prod) == 1 else 6)
    return r


class MarketModel:
    def __init__(self):
        self.hist = []          # (step, inv dict, shops count)
        self.our = {}           # step -> {item: units we ordered to sell}
        self.opp_rate = {k: 0.0 for k in PRODUCTS}

    def update(self, step, market, shops, our_sold_prev):
        inv = {k: int(market["inventory"][k]) for k in PRODUCTS}
        self.inv = inv; self.shops = list(shops); self.step = step
        if our_sold_prev:
            self.our[step - 1] = dict(our_sold_prev)
        self.hist.append((step, inv))
        if len(self.hist) > 200:
            self.hist = self.hist[-200:]
        # opponent supply: inventory rise beyond town consumption and our own sales over the trailing window
        W = 72
        base = None
        for s, iv in self.hist:
            if s >= step - W:
                base = (s, iv); break
        if base and step - base[0] >= 24:
            ds = step - base[0]
            for k in PRODUCTS:
                cons = shop_rate(k, self.shops) * ds / 24.0
                ours = sum(v.get(k, 0) for s, v in self.our.items() if s >= base[0])
                opp = (inv[k] - base[1][k]) + cons - ours
                self.opp_rate[k] = max(0.0, opp / ds * 24.0)

    def x_at(self, item, day_target, day_now, extra=0):
        """Projected inventory offset (inv - I0) at the start of day_target (before our planned sales), + extra."""
        dd = max(0.0, day_target - day_now)
        return (self.inv[item] - I0) - future_consumption(item, self.shops, day_now, day_target) + self.opp_rate[item] * dd + extra

    def price_at(self, item, day_target, day_now, extra=0):
        return price_x(item, self.x_at(item, day_target, day_now, extra))

    def revenue_at(self, item, day_target, day_now, n, extra=0):
        return revenue_x(item, self.x_at(item, day_target, day_now, extra), n)
