import sys,collections,importlib.util
from kaggle_environments import make
import kaggle_environments.envs.kaggriculture.kaggriculture as K
def load(p):
    s=importlib.util.spec_from_file_location('C'+str(abs(hash(p))),p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return getattr(m,'kaggle_submission_agent',None) or m.agent
A,B,seed=sys.argv[1],sys.argv[2],int(sys.argv[3])
env=make("kaggriculture",configuration={"seed":seed}); env.reset()
G=env.interpreter.__globals__; orig=G['_commit_unit']; REV=[collections.Counter(),collections.Counter()]; QTY=[collections.Counter(),collections.Counter()]; CUR={'farms':None}
def hook(op,item,price,farm,private,market,shed_capacity=100):
    ok=orig(op,item,price,farm,private,market,shed_capacity)
    if ok:
        pid=CUR['farms'].index(farm) if farm in CUR['farms'] else -1
        REV[pid][op+':'+item]+= price if op=='SELL' else -price; QTY[pid][op+':'+item]+=1
    return ok
G['_commit_unit']=hook
cfg=dict(env.configuration); cfg['__raw_path__']='/root/kg/'+A
a=load(A); b=load(B)
for t in range(720):
    obs=[env._Environment__get_shared_state(i).observation for i in (0,1)]
    CUR['farms']=env.state[0].observation['farms']
    env.step([a(obs[0],cfg),b(obs[1],env.configuration)])
    if env.done: break
rw=[s.reward for s in env.state]; print(A,'vs',B,'seed',seed,'margin %+.0f'%(rw[0]-rw[1]))
for k in sorted(set(REV[0])|set(REV[1])): print(f"  {k:22s} A {REV[0][k]:8.0f} ({QTY[0][k]:4d})   B {REV[1][k]:8.0f} ({QTY[1][k]:4d})")
