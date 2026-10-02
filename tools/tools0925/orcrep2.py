import importlib.util,sys
from kaggle_environments import make
def load(p,n):
    s=importlib.util.spec_from_file_location(n,p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
cand,opp=sys.argv[1],sys.argv[2]; seeds=[int(x) for x in sys.argv[3].split(',')]
for seed in seeds:
    ME=load(cand,'ME%d'%seed); RV=load(opp,'RV%d'%seed)
    env=make("kaggriculture",configuration={"seed":seed}); env.reset()
    cfg=dict(env.configuration); cfg['__raw_path__']='/root/kg/'+cand
    hr=[];fi=[]
    for t in range(720):
        obs=[env._Environment__get_shared_state(i).observation for i in (0,1)]
        a0=ME.kaggle_submission_agent(obs[0],cfg); a1=(getattr(RV,'kaggle_submission_agent',None) or RV.agent)(obs[1],env.configuration); env.step([a0,a1])
        if t%48==47:
            r=ME._ORC_REPORT; hr.append('%d/%d'%(r.get('orc_hits') or 0,r.get('orc_hit_n') or 0)); fi.append(r.get('orc_fires'))
        if env.done: break
    rw=[s.reward for s in env.state]
    print(seed,opp,'margin %+.0f'%(rw[0]-rw[1]),'fires',fi,'hits',hr,flush=True)
