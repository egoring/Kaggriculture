
# ---------------------------------------------------------------------------
# ASAP layer (9/25): the 2400+ field runs a "liquidate immediately" variant of the public stack (5-wheat opening,
# sells every race product the step it lands in the shed, down to the $1 floor). The market price falls ~2%/unit
# above I0 and recovers only 1-2 units per 4 steps, so whoever sells first captures the value; the public stack's
# reservation windows (holding MILK/STRAWBERRY for scheduled sales) lose the race against it. This layer sells the
# whole shed stock of every race product every step (product sells first, in slot order), including units the
# hands DROP this step.
_ASAP_ITEMS = tuple(__import__('os').environ.get('ASAP_ITEMS', 'MILK,WOOL,EGG,STRAWBERRY,MELON,CARROT,TOMATO').split(','))
_ASAP_FROM = int(__import__('os').environ.get('ASAP_FROM', '0'))
_ASAP_REPORT = dict(asap_turns=0, asap_units=0, asap_errors=0)
_ASAP_PARENT = agent


def agent(observation, configuration=None):
    action = _ASAP_PARENT(observation, configuration)
    try:
        if not isinstance(action, dict) or int(observation.get('step', 0)) < _ASAP_FROM:
            return action
        private = observation.get('private') or {}
        shed = dict(private.get('shed') or {})
        invs = private.get('inventories') or []
        cmds = [action.get('farmer') or ['PASS']] + list(action.get('hands') or [])
        for h, c in enumerate(cmds):
            if not isinstance(c, (list, tuple)) or not c:
                continue
            if c[0] == 'DROP' and h < len(invs) and isinstance(invs[h], dict):
                for k, v in invs[h].items():
                    shed[k] = int(shed.get(k, 0)) + int(v)
            elif c[0] == 'PLACE' and len(c) > 1 and h < len(invs) and isinstance(invs[h], dict):
                q = int(c[2]) if len(c) > 2 else int(invs[h].get(c[1], 0))
                shed[c[1]] = int(shed.get(c[1], 0)) + min(q, int(invs[h].get(c[1], 0)))
        market = [list(o) if isinstance(o, (list, tuple)) else o for o in (action.get('market') or [])]
        have = {}
        for o in market:
            if o and len(o) > 2 and o[0] == 'SELL' and o[1] in _ASAP_ITEMS:
                have[o[1]] = have.get(o[1], 0) + int(o[2])
        add = []
        for it in _ASAP_ITEMS:
            s = int(shed.get(it, 0))
            if s > 0 and have.get(it, 0) < s:
                add.append(['SELL', it, s])
        if not add:
            return action
        # drop the parent's smaller sells of the same items (the new full-stock order replaces them)
        rest = [o for o in market if not (o and len(o) > 2 and o[0] == 'SELL' and o[1] in {a[1] for a in add})]
        new = add + rest
        # never push a BUY_*/first HIRE out of the 10-order window: shed repeated HIREs first
        while len(new) > 10:
            hs = [i for i, o in enumerate(new) if o and o[0] == 'HIRE']
            if len(hs) > 1:
                del new[hs[-1]]
            else:
                break
        if len(new) > 10:
            return action
        action = dict(action); action['market'] = new
        _ASAP_REPORT['asap_turns'] += 1; _ASAP_REPORT['asap_units'] += sum(a[2] for a in add)
    except Exception:
        _ASAP_REPORT['asap_errors'] += 1
    return action


agent.telemetry = _ASAP_REPORT
agent = globals().pop("agent")

kaggle_submission_agent = agent
