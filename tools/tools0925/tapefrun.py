import pickle,sys,os
from kaggle_environments import make
from tapeagent import make_tape_agent
pool,cand=sys.argv[1],sys.argv[2]; names=sys.argv[3:]
P=pickle.load(open(f'recs_cache/logs__{pool}__all.pkl','rb'))
byep={}
for r in P: byep.setdefault(r['ep'],{})[r['seat']]=r
for ep,d in sorted(byep.items()):
    me=[r for r in d.values() if r['name']=='weense'][0]; op=[r for r in d.values() if r is not me][0]
    if names and op['name'] not in names: continue
    ags=[None,None]; ags[me['seat']]=cand; ags[op['seat']]=make_tape_agent(op['acts'])
    try: os.remove('/tmp/orc.log')
    except Exception: pass
    env=make("kaggriculture",configuration={"seed":me['seed']}); env.run(ags); rw=[x.reward for x in env.steps[-1]]
    log=open('/tmp/orc.log').read().strip().splitlines() if os.path.exists('/tmp/orc.log') else []
    print(f"{op['name'][:14]:14s} rec {me['reward']-me['opp_reward']:+.0f} replay {rw[me['seat']]-rw[op['seat']]:+.0f} | {' | '.join(l[:70] for l in log)}",flush=True)
