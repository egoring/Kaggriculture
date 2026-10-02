import sys,importlib.util,pickle
from kaggle_environments import make
from tapeagent import make_tape_agent
def load(p,n):
    s=importlib.util.spec_from_file_location(n,p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
pool,cand,ep,lo,hi=sys.argv[1],sys.argv[2],int(sys.argv[3]),int(sys.argv[4]),int(sys.argv[5])
P=pickle.load(open(f'recs_cache/logs__{pool}__all.pkl','rb'))
d={r['seat']:r for r in P if r['ep']==ep}
me=[r for r in d.values() if r['name']=='weense'][0]; op=[r for r in d.values() if r is not me][0]
ME=load(cand,'ME%d'%ep); tape=make_tape_agent(op['acts'])
env=make("kaggriculture",configuration={"seed":me['seed']}); env.reset()
cfg=dict(env.configuration); cfg['__raw_path__']='/root/kg/'+cand
for t in range(720):
    obs=[env._Environment__get_shared_state(i).observation for i in (0,1)]
    acts=[None,None]; acts[me['seat']]=ME.kaggle_submission_agent(obs[me['seat']],cfg); acts[op['seat']]=tape(obs[op['seat']],env.configuration)
    if lo<=t<=hi:
        o=obs[me['seat']]; sh=o['private']['shed']; mk=[x for x in acts[me['seat']]['market'] if x and (x[0] in('HIRE','BUY_ANIMAL','BUY_SEED','BUY_LAND') or (len(x)>1 and x[1]=='WHEAT'))]
        print(f"t{t} d{t//24}h{t%24} money {int(o['farms'][me['seat']]['money'])} wheat {sh.get('WHEAT',0)} shedtot {sum(sh.values())} pW {o['market']['prices']['WHEAT']} {mk}")
    env.step(acts)
    if env.done: break
