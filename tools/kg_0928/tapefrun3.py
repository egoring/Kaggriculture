import importlib.util,sys,pickle
from kaggle_environments import make
from tapeagent import make_tape_agent
def load(p,n):
    s=importlib.util.spec_from_file_location(n,p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
pool,cand=sys.argv[1],sys.argv[2]; lo,hi=int(sys.argv[3]),int(sys.argv[4]); names=[]
P=pickle.load(open(f'recs_cache/logs__{pool}__all.pkl','rb'))
byep={}
for r in P: byep.setdefault(r['ep'],{})[r['seat']]=r
for idx,(ep,d) in enumerate(sorted(byep.items())):
    if not (lo<=idx<hi): continue
    me=[r for r in d.values() if r['name']=='weense'][0]; op=[r for r in d.values() if r is not me][0]
    if names and op['name'][:8] not in [n[:8] for n in names]: continue
    ME=load(cand,'ME%d'%ep); tape=make_tape_agent(op['acts'])
    env=make("kaggriculture",configuration={"seed":me['seed']}); env.reset()
    cfg=dict(env.configuration); cfg['__raw_path__']='/root/kg/'+cand
    on_step=None
    for t in range(720):
        obs=[env._Environment__get_shared_state(i).observation for i in (0,1)]
        acts=[None,None]
        acts[me['seat']]=ME.kaggle_submission_agent(obs[me['seat']],cfg); acts[op['seat']]=tape(obs[op['seat']],env.configuration)
        env.step(acts)
        if on_step is None and getattr(ME,'_ASAP_REPORT',{}).get('asap_on'): on_step=t
        if env.done: break
    rw=[s.reward for s in env.state]; r=getattr(ME,'_ORC_REPORT',{}); a=getattr(ME,'_ASAP_REPORT',{})
    print(f"{ep} {op['name'][:12]:12s} rec {me['reward']-me['opp_reward']:+6.0f} rep {rw[me['seat']]-rw[op['seat']]:+6.0f} orc_on={r.get('orc_on')} fires={r.get('orc_fires')} asap_on@{on_step} asap_turns={a.get('asap_turns')} units={a.get('asap_units')} dev={a.get('asap_dev')}",flush=True)
