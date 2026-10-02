"""Build Step1009 hybrids:
 H1 = Step1009 + WASH + FEED5 + ORACLE(model = m2965v7 stack blob from v879) + ASAP gate
 H2 = H1 + v7 MPX (9-22h) below the layers
 H3 = Step1009 + WASH + FEED5 only
"""
import base64, zlib, re, sys, hashlib

v879 = open('/root/kg/submission_v879_mpx9.py', encoding='utf-8').read()
s1009 = open('/root/kg/submission_step1009.py', encoding='utf-8').read()
lines = v879.split('\n')

def block(a, b):  # 1-based inclusive line numbers
    return '\n'.join(lines[a - 1:b]) + '\n'

# ---- pieces from v879 ----
cut = v879.find('# ==ORACLE_END==')
oracle_src = v879[:cut]
blob = base64.b64encode(zlib.compress(oracle_src.encode('utf-8'), 9)).decode()
i_wash = v879.find('# WASH layer (9/23)')
i_feed = v879.find('# FEED5 layer (9/24)')
i_orc = v879.find('# ORACLE layer (9/24)')
i_asap = v879.find('# ASAP layer (9/25)')
i_end = v879.rfind('kaggle_submission_agent = agent')
wash = v879[i_wash:i_feed]
# hybrid gate: the Step1009 route tapes 103/104/112/124 wash wheat themselves from day 12-21; never run two washes
_gate_old = """        if st["off"] and st["pending"] <= 0:
            return action
"""
_gate_new = """        if not st["off"] and step > 0:
            try:
                _rt = _IMPL.chassis.players[player]["route"]
                if _rt != st.get("route_seen"):
                    st["route_seen"] = _rt
                    _tape = _IMPL.chassis.routes[_rt]
                    if any(o and o[0] == "BUY_PRODUCT" and len(o) > 2 and o[1] == "WHEAT" and int(o[2]) >= 20 for _a in _tape[1:] for o in _a.get("market", [])):
                        st["off"] = True; _WASH_REPORT["wash_off"] = 3
            except Exception:
                pass
        if st["off"] and st["pending"] <= 0:
            return action
"""
assert _gate_old in wash
wash = wash.replace(_gate_old, _gate_new)
# hybrid: leave room for the hands' cargo so Step1009's warehouse layers never sell feed wheat to make space
_room_old = """        room = 100 - sum(int(v) for v in shed.values()) - _WASH_ROOM
"""
_room_new = """        room = 100 - sum(int(v) for v in shed.values()) - _WASH_ROOM
        try:
            _proj = sum(max(0, int(v)) for v in projected_shed(action, FarmView(observation)).values())
            _cargo = sum(int(n) for bag in (private.get("inventories") or []) if isinstance(bag, dict) for n in bag.values())
            room = min(room, 100 - _proj - _cargo - _WASH_ROOM)
        except Exception:
            pass
"""
assert _room_old in wash
wash = wash.replace(_room_old, _room_new)

WASH2 = """
# ---------------------------------------------------------------------------
# WASH2 layer (9/27, hybrid): wheat round-trip around the town's 4-step draw, priced with the market's own curve.
# BUY q wheat at a step%4==0 step (units at P(I-1)..P(I-q)); the town then draws c; SELL q next step from I-q-c
# (units at P(I-q-c)..P(I-c-1)). Predicted profit is computed exactly per unit and the wash runs only if it clears
# _W2_MIN; the realized profit (same curve, real inventory at the sell step) is accumulated and the layer switches
# off for good once it goes negative beyond _W2_STOP (a rival that sells wheat between the legs).
_W2_QTY = 60
_W2_DAY0 = 10
_W2_DAY1 = 27
_W2_HOURS = (4, 8, 12, 16, 20)
_W2_RESERVE = 1500.0
_W2_ROOM = 2
_W2_MIN = 6.0
_W2_STOP = -60.0
_W2_STATE = {}
_WASH_REPORT = dict(wash_buys=0, wash_sells=0, wash_units=0, wash_errors=0, wash_pred=0.0, wash_real=0.0, wash_skips=0)
_W2_PARENT = agent


def _w2_price(inv):
    return _r37_market_price('WHEAT', int(inv))


def _w2_profit(inv, q, c):
    tot = 0
    for k in range(q):
        tot += _w2_price(inv - q - c + k) - _w2_price(inv - 1 - k)
    return tot


def agent(observation, configuration=None):
    action = _W2_PARENT(observation, configuration)
    try:
        player = int(observation["player"]); step = int(observation["step"])
        st = _W2_STATE.get(player)
        if st is None or step <= st["step"]:
            st = _W2_STATE[player] = {"step": -1, "pending": 0, "wheat_before": 0, "off": False, "real": 0.0, "buy_cost": 0, "inv_buy": 0}
            if step == 0:
                _WASH_REPORT.update(wash_buys=0, wash_sells=0, wash_units=0, wash_errors=0, wash_pred=0.0, wash_real=0.0, wash_skips=0)
        st["step"] = step
        day, hour = step // 24, step % 24
        if not isinstance(action, dict):
            return action
        market = list(action.get("market") or [])
        private = observation.get("private") or {}
        shed = private.get("shed") or {}
        wheat = int(shed.get("WHEAT", 0))
        inv_now = int(observation["market"]["inventory"]["WHEAT"])
        # sell leg: exactly what the buy delivered
        if st["pending"] > 0:
            got = max(0, min(st["pending"], wheat - st["wheat_before"]))
            st["pending"] = 0
            if got > 0 and len(market) < 10:
                market.append(["SELL", "WHEAT", int(got)])
                rev = sum(_w2_price(inv_now + k) for k in range(got))
                st["real"] += rev - st["buy_cost"]
                _WASH_REPORT["wash_sells"] += 1; _WASH_REPORT["wash_units"] += int(got); _WASH_REPORT["wash_real"] = round(st["real"], 1)
                if st["real"] < _W2_STOP:
                    st["off"] = True; _WASH_REPORT["wash_off"] = 4
                action = dict(action); action["market"] = market
            return action
        if st["off"] or day < _W2_DAY0 or day > _W2_DAY1 or step % 4 != 0 or hour not in _W2_HOURS or len(market) >= 10:
            return action
        if any(o and o[0] in ("SELL", "BUY_PRODUCT") and len(o) > 1 and o[1] == "WHEAT" for o in market):
            return action
        farm = observation["farms"][player]
        money = float(farm.get("money", 0))
        price = float(observation["market"]["prices"]["WHEAT"])
        room = 100 - sum(int(v) for v in shed.values()) - _W2_ROOM
        try:
            _proj = sum(max(0, int(v)) for v in projected_shed(action, FarmView(observation)).values())
            _cargo = sum(int(n) for bag in (private.get("inventories") or []) if isinstance(bag, dict) for n in bag.values())
            room = min(room, 100 - _proj - _cargo - _W2_ROOM)
        except Exception:
            pass
        q = min(_W2_QTY, room, int((money - _W2_RESERVE) / max(1.0, price * 1.3)))
        if q < 5:
            return action
        shops = list((observation.get("town") or {}).get("unlocked_shops") or [])
        c = int(_race_town(step, shops).get("WHEAT", 0))
        prof = _w2_profit(inv_now, q, c)
        if prof < _W2_MIN:
            _WASH_REPORT["wash_skips"] += 1
            return action
        market.append(["BUY_PRODUCT", "WHEAT", int(q)])
        st["pending"] = int(q); st["wheat_before"] = wheat
        st["buy_cost"] = sum(_w2_price(inv_now - 1 - k) for k in range(q)); st["inv_buy"] = inv_now
        _WASH_REPORT["wash_buys"] += 1; _WASH_REPORT["wash_pred"] = round(_WASH_REPORT["wash_pred"] + prof, 1)
        action = dict(action); action["market"] = market
    except Exception:
        _WASH_REPORT["wash_errors"] += 1
    return action


agent.telemetry = _WASH_REPORT
agent = globals().pop("agent")


"""
feed = v879[i_feed:i_orc]
orc = v879[i_orc:i_asap]
asap = v879[i_asap:i_end]
# oracle: take the model source from the embedded blob instead of the file cut
old = """        if not path:
            st['reason'] = 'no_path'; return st
        src = open(path, encoding='utf-8').read()
        cut = src.find('# ==ORACLE_END==')
        if cut < 0:
            st['reason'] = 'no_marker'; return st
        ns = {'__name__': '_orc_ns'}
        exec(compile(src[:cut], 'orc', 'exec'), ns)"""
new = """        import base64 as _b64, zlib as _zl
        src = _zl.decompress(_b64.b64decode(_ORC_SRC_BLOB)).decode('utf-8')
        ns = {'__name__': '_orc_ns'}
        exec(compile(src, 'orc', 'exec'), ns)"""
assert old in orc
orc = orc.replace(old, new)
orc = orc.replace("_ORC_PARENT = agent\n", "_ORC_PARENT = agent\n_ORC_SRC_BLOB = '''%s'''\n" % blob, 1)
assert '_ORC_SRC_BLOB' in orc
# MPX layer from v7 (v879 window 9-22h), re-parented
i_mpx = v879.find('# 2. MPX: Microstructure Price Defense')
i_mpx_end = v879.find('# 3. CXD: V59 Order-Book Permutation Search')
mpx = v879[i_mpx:i_mpx_end]
mpx = mpx.replace('_V7_MPX_PARENT = v7_sm_agent', '_V7_MPX_PARENT = agent')
mpx = '# ' + '-' * 75 + '\n' + mpx + 'agent = v7_mpx_agent\nagent.telemetry = _V7_MPX_REPORT\n\n'

head = s1009.rstrip('\n') + '\n\n\n# ==== HYBRID (9/27): Step1009 body + weense layers ====\n'
tail = '\nkaggle_submission_agent = agent\n'
variants = {
    'submission_v884b_h1.py': head + wash + feed + orc + asap + tail,
    'submission_v885b_h2.py': head + mpx + wash + feed + orc + asap + tail,
    'submission_v886b_h3.py': head + wash + feed + tail,
    'submission_v891_w2a.py': head + WASH2 + feed + tail,
    'submission_v892_w2a3.py': head + WASH2.replace('_W2_MIN = 6.0', '_W2_MIN = 3.0') + feed + tail,
}
for name, src in variants.items():
    open('/root/kg/' + name, 'w', encoding='utf-8').write(src)
    compile(src, name, 'exec')
    print(name, len(src), hashlib.md5(src.encode()).hexdigest())
