
# ---------------------------------------------------------------------------
# PULL layer (9/25): the 2400+ field runs a liquidate-first variant of the public stack that sells every race
# product the step it lands. Prices fall ~2%/unit above I0 and recover only 1-2 units per 4 steps, so the first
# seller captures the value. The public stack's routes hold products for scheduled sales up to a day later;
# this layer pulls those scheduled sales forward: whatever the route sells within the next _PULL_H steps and is
# already in the shed is sold now, in front of the other orders. Quantities stay the route's own, so the stack's
# bookkeeping is unchanged apart from the shed emptying earlier.
_PULL_ITEMS = tuple(__import__('os').environ.get('PULL_ITEMS', 'MILK,WOOL,EGG,STRAWBERRY,MELON,CARROT,TOMATO').split(','))
_PULL_H = int(__import__('os').environ.get('PULL_H', '24'))
_PULL_REPORT = dict(pull_turns=0, pull_units=0, pull_errors=0)
_PULL_PARENT = agent


def _pull_planned(step, player, item):
    try:
        native = _IMPL.chassis.players[player]; route = native['route']; q = 0
        for s in range(step + 1, min(719, step + _PULL_H)):
            a = _IMPL.chassis.routes[2 if s >= 648 else route][s]
            for o in a.get('market', []):
                if len(o) > 2 and o[0] == 'SELL' and o[1] == item:
                    q += int(o[2])
        return q
    except Exception:
        return 0


def agent(observation, configuration=None):
    action = _PULL_PARENT(observation, configuration)
    try:
        if not isinstance(action, dict):
            return action
        step = int(observation['step']); player = int(observation['player'])
        shed = observation['private']['shed']
        market = [list(o) if isinstance(o, (list, tuple)) else o for o in (action.get('market') or [])]
        have = {}
        for o in market:
            if o and len(o) > 2 and o[0] == 'SELL' and o[1] in _PULL_ITEMS:
                have[o[1]] = have.get(o[1], 0) + int(o[2])
        add = []
        for it in _PULL_ITEMS:
            stock = int(shed.get(it, 0)) - have.get(it, 0)
            if stock <= 0:
                continue
            q = min(stock, _pull_planned(step, player, it))
            if q > 0:
                add.append(['SELL', it, q])
        if not add or len(market) + len(add) > 10:
            return action
        action = dict(action); action['market'] = add + market
        _PULL_REPORT['pull_turns'] += 1; _PULL_REPORT['pull_units'] += sum(a[2] for a in add)
    except Exception:
        _PULL_REPORT['pull_errors'] += 1
    return action


agent.telemetry = _PULL_REPORT
agent = globals().pop("agent")

kaggle_submission_agent = agent
