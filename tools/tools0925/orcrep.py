import importlib.util,sys,time
from kaggle_environments import make
def load(p,n):
    s=importlib.util.spec_from_file_location(n,p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
cand,opp=sys.argv[1],sys.argv[2]; seeds=[int(x) for x in sys.argv[3].split(',')]
ME=load(cand,'ME'); RV=load(opp,'RV')
for seed in seeds:
    env=make("kaggriculture",configuration={"seed":seed}); env.reset()
    cfg=dict(env.configuration); cfg['__raw_path__']='/root/kg/'+cand
    for t in range(720):
        obs=[env._Environment__get_shared_state(i).observation for i in (0,1)]
        a0=ME.kaggle_submission_agent(obs[0],cfg); a1=(getattr(RV,'kaggle_submission_agent',None) or RV.agent)(obs[1],env.configuration); env.step([a0,a1])
        if env.done: break
    rw=[s.reward for s in env.state]; r=ME._ORC_REPORT
    print(seed,'margin %+.0f'%(rw[0]-rw[1]),{k:r.get(k) for k in ('orc_on','orc_off_reason','orc_fires','orc_units','orc_hits','orc_hit_n','orc_soft','orc_skipped')},flush=True)
