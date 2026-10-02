import sys, importlib.util, collections
from kaggle_environments import make


def load(p):
    s = importlib.util.spec_from_file_location('C' + str(abs(hash(p))), p); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m


A = load(sys.argv[1]); B = load(sys.argv[2]); seed = int(sys.argv[3])
ag = [A.kaggle_submission_agent, getattr(B, 'kaggle_submission_agent', None) or B.agent]
env = make("kaggriculture", configuration={"seed": seed}); env.reset()
K = [collections.Counter() for _ in range(2)]
prev_tiles = [None, None]
sold = [collections.Counter() for _ in range(2)]; rev = [collections.Counter() for _ in range(2)]
for t in range(720):
    obs = [env._Environment__get_shared_state(i).observation for i in (0, 1)]
    acts = [ag[i](obs[i], env.configuration) for i in (0, 1)]
    prices = obs[0]['market']['prices']
    for i in (0, 1):
        f = obs[0]['farms'][i]
        for c in [acts[i]['farmer']] + acts[i]['hands']:
            K[i]['steps'] += 1
            if c[0] == 'PASS': K[i]['pass'] += 1
            elif c[0] in ('NORTH', 'SOUTH', 'EAST', 'WEST'): K[i]['move'] += 1
            else: K[i]['ops'] += 1; K[i]['op_'+c[0][:5]] += 1
        for o in acts[i]['market']:
            if o and o[0] == 'SELL':
                q = min(o[2], obs[i]['private']['shed'].get(o[1], 0)); sold[i][o[1]] += q; rev[i][o[1]] += q * prices[o[1]]
            if o and o[0] == 'HIRE': K[i]['hires'] += 1
    if t % 24 == 23:
        day = t // 24
        for i in (0, 1):
            f = obs[0]['farms'][i]
            for y, row in enumerate(f['tiles']):
                for x, tl in enumerate(row):
                    if isinstance(tl, dict):
                        if 'animal' in tl:
                            K[i]['animal_days'] += 1
                            if not tl['fed_today']: K[i]['unfed'] += 1
                            if not tl['cared_today']: K[i]['uncared'] += 1
                            if tl.get('fertilizer_available'): K[i]['fert_uncollected'] += 1
                            if tl['yield_units'] >= {'GOOSE': 4, 'COW': 6, 'SHEEP': 6}[tl['animal']]: K[i]['animal_capped'] += 1
                        elif tl.get('kind') == 'PLANT':
                            K[i]['plant_days'] += 1
                            if not tl['watered_today'] and tl['consecutive_unwatered'] >= 1: K[i]['plant_die'] += 1
                            if tl['crop'] in ('STRAWBERRY', 'TOMATO'):
                                age = day - tl['planted_day']; first = 10 if tl['crop'] == 'STRAWBERRY' else 8; iv = 2 if tl['crop'] == 'STRAWBERRY' else 1
                                k = age + 1 - first
                                if k >= 0 and k % iv == 0 and k // iv < 4:
                                    K[i]['ong_prod'] += 1
                                    if tl.get('fertilized_until_day', -1) >= day and tl['watered_today']: K[i]['ong_prod2'] += 1
                        elif tl.get('kind') == 'WEED': K[i]['weed_tiles'] += 1
            if day == 10: K[i]['money_d10'] = int(f['money'])
            if day == 20: K[i]['money_d20'] = int(f['money'])
    env.step(acts)
    if env.done: break
rw = [s.reward for s in env.state]
print(sys.argv[1], 'vs', sys.argv[2], 'seed', seed, 'FINAL', rw)
keys = [k for k in sorted(set(K[0])|set(K[1])) if k.startswith('op_')] + ['steps', 'ops', 'move', 'pass', 'hires', 'animal_days', 'unfed', 'uncared', 'fert_uncollected', 'animal_capped', 'plant_days', 'plant_die', 'weed_tiles', 'ong_prod', 'ong_prod2', 'money_d10', 'money_d20']
print(f"{'kpi':18s} {'A':>8s} {'B':>8s}")
for k in keys:
    print(f"{k:18s} {K[0][k]:8d} {K[1][k]:8d}")
for it in sorted(set(sold[0]) | set(sold[1])):
    print(f"  {it:12s} A {sold[0][it]:4d} ${rev[0][it]:6d}  B {sold[1][it]:4d} ${rev[1][it]:6d}")
