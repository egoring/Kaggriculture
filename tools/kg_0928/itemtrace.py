import sys,collections,importlib.util,pickle
from kaggle_environments import make
from tapeagent import make_tape_agent
def load(p,n):
    s=importlib.util.spec_from_file_location(n,p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
pool,cand,ep,ITEM=sys.argv[1],sys.argv[2],int(sys.argv[3]),sys.argv[4]
P=pickle.load(open(f'recs_cache/logs__{pool}__all.pkl','rb'))
d={r['seat']:r for r in P if r['ep']==ep}
me=[r for r in d.values() if r['name']=='weense'][0]; op=[r for r in d.values() if r is not me][0]
ME=load(cand,'ME%d'%ep); tape=make_tape_agent(op['acts'])
env=make("kaggriculture",configuration={"seed":me['seed']}); env.reset()
cfg=dict(env.configuration); cfg['__raw_path__']='/root/kg/'+cand
G=env.interpreter.__globals__; orig=G['_commit_unit']; CUR={'farms':None,'step':0}
SALES=[collections.defaultdict(list),collections.defaultdict(list)]
def hook(op_,item,price,farm,private,market,shed_capacity=100):
    ok=orig(op_,item,price,farm,private,market,shed_capacity)
    if ok and item==ITEM:
        pid=0 if farm is CUR['farms'][0] else 1; SALES[pid][CUR['step']].append((op_[0],price))
    return ok
G['_commit_unit']=hook
oi=env.interpreter
def interp(state, env_):
    CUR['farms']=list(state[0].observation.farms); CUR['step']=int(state[0].observation.step); return oi(state, env_)
env.interpreter=interp
shedlog=[]
for t in range(720):
    obs=[env._Environment__get_shared_state(i).observation for i in (0,1)]
    acts=[None,None]; acts[me['seat']]=ME.kaggle_submission_agent(obs[me['seat']],cfg); acts[op['seat']]=tape(obs[op['seat']],env.configuration)
    if t%24==0: shedlog.append((t//24,int(obs[me['seat']]['private']['shed'].get(ITEM,0)),int(obs[me['seat']]['private']['shed'].get('WHEAT',0)),sum(int(v) for v in obs[me['seat']]['private']['shed'].values()),int(obs[0]['market']['inventory'][ITEM])))
    env.step(acts)
    if env.done: break
m,o=me['seat'],op['seat']
print('day shed',ITEM,'wheat total mktinv:',shedlog)
for pid,lab in ((m,'me'),(o,'opp')):
    tot=0
    for s in sorted(SALES[pid]):
        v=SALES[pid][s]; n=sum(1 for x in v if x[0]=='S'); r=sum(p for x,p in v if x=='S'); b=sum(1 for x in v if x[0]=='B'); bc=sum(p for x,p in v if x=='B'); tot+=r; totb=locals().get('totb',0)+bc
        if len(sys.argv)<6: print(f"{lab} step {s} d{s//24}h{s%24} sell {n} ${r} buy {b} ${bc}")
    print(lab,'total sell',tot,'buy',totb,'net',tot-totb)
