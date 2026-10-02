import sys,collections,importlib.util
from kaggle_environments import make
def load(p):
    s=importlib.util.spec_from_file_location('C'+str(abs(hash(p))),p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return getattr(m,'kaggle_submission_agent',None) or m.agent
A,B,seed=sys.argv[1],sys.argv[2],int(sys.argv[3])
env=make("kaggriculture",configuration={"seed":seed}); env.reset()
G=env.interpreter.__globals__; orig=G['_commit_unit']
CUR={'farms':None,'step':0}
H=[collections.defaultdict(lambda: collections.Counter()) for _ in range(2)]  # item -> hour -> revenue
FIRST=[collections.defaultdict(list) for _ in range(2)]  # item -> list of (day,hour) first sale of each day
def hook(op,item,price,farm,private,market,shed_capacity=100):
    ok=orig(op,item,price,farm,private,market,shed_capacity)
    if ok and op=='SELL' and price>1:
        pid=0 if farm is CUR['farms'][0] else 1; h=CUR['step']%24; d=CUR['step']//24
        H[pid][item][h]+=price
        if not FIRST[pid][item] or FIRST[pid][item][-1][0]!=d: FIRST[pid][item].append((d,h))
    return ok
G['_commit_unit']=hook
oi=env.interpreter
def interp(state, env_):
    CUR['farms']=list(state[0].observation.farms); CUR['step']=int(state[0].observation.step); return oi(state, env_)
env.interpreter=interp
a=load(A); b=load(B)
for t in range(720):
    obs=[env._Environment__get_shared_state(i).observation for i in (0,1)]
    env.step([a(obs[0],env.configuration), b(obs[1],env.configuration)])
    if env.done: break
print('FINAL',[s.reward for s in env.state])
import statistics as S
for item in ('MILK','WOOL','STRAWBERRY','EGG','MELON','WHEAT','CARROT','TOMATO','FERTILIZER'):
    for pid in (0,1):
        hh=H[pid][item]; tot=sum(hh.values())
        if not tot: continue
        # revenue-weighted mean hour, and median first-sale hour per day (days 12-28)
        mh=sum(h*v for h,v in hh.items())/tot
        fs=[h for d,h in FIRST[pid][item] if 12<=d<=28]
        print(f"{item:11s} p{pid} rev {tot:7.0f} mean-hour {mh:5.1f} first-sale-hour med {S.median(fs) if fs else '-'}")
