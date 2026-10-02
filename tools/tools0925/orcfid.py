import importlib.util,sys,collections
from kaggle_environments import make
def load(p,n):
    s=importlib.util.spec_from_file_location(n,p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
cand,opp=sys.argv[1],sys.argv[2]; seed=int(sys.argv[3])
ME=load(cand,'ME'); RV=load(opp,'RV')
env=make("kaggriculture",configuration={"seed":seed}); env.reset()
cfg=dict(env.configuration); cfg['__raw_path__']='/root/kg/'+cand
IT=("MILK","WOOL","EGG","STRAWBERRY","MELON","CARROT","TOMATO")
def sells(a):
    d={}
    for o in (a.get('market') or []) if isinstance(a,dict) else []:
        if o and o[0]=='SELL' and len(o)>2 and o[1] in IT: d[o[1]]=d.get(o[1],0)+int(o[2])
    return d
stat=collections.defaultdict(lambda:[0,0,0,0]) # per 4-day: exact, rt-only, real-only, qty-mismatch
ex=[]
for t in range(720):
    obs=[env._Environment__get_shared_state(i).observation for i in (0,1)]
    a0=ME.kaggle_submission_agent(obs[0],cfg); a1=(getattr(RV,'kaggle_submission_agent',None) or RV.agent)(obs[1],env.configuration)
    rt=ME._ORC[0].get('last_rt') if ME._ORC.get(0) else None
    real=sells(a1); pred=sells(rt or {})
    # clamp real by shed
    shed=obs[1]['private']['shed']
    real={k:min(v,int(shed.get(k,0))) for k,v in real.items() if min(v,int(shed.get(k,0)))>0}
    b=t//96
    for k in set(real)|set(pred):
        if k in real and k in pred:
            if real[k]==pred[k]: stat[b][0]+=1
            else: stat[b][3]+=1; ex.append((t,k,real[k],pred[k],'q'))
        elif k in pred: stat[b][1]+=1; ex.append((t,k,0,pred[k],'rt-only'))
        else: stat[b][2]+=1; ex.append((t,k,real[k],0,'real-only'))
    # also farmer/hands unit equality
    if (rt or {}).get('farmer')!=a1.get('farmer') or (rt or {}).get('hands')!=a1.get('hands'): stat[b].append(t) if len(stat[b])<5 else None
    env.step([a0,a1])
    if env.done: break
rw=[s.reward for s in env.state]; print('margin %+.0f'%(rw[0]-rw[1]))
for b in sorted(stat): print('days %2d-%2d exact %3d rt-only %2d real-only %2d qty-mismatch %2d  first unit mismatch step: %s'%(b*4,b*4+3,*stat[b][:4], stat[b][4] if len(stat[b])>4 else '-'))
print('examples late:',[e for e in ex if e[0]>=384][:25])
