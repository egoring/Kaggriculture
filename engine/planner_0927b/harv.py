import sys,importlib.util,collections
from kaggle_environments import make
def load(p):
    s=importlib.util.spec_from_file_location('C'+str(abs(hash(p))),p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
A=load(sys.argv[1]); B=load(sys.argv[2]); seed=int(sys.argv[3])
ag=[A.kaggle_submission_agent, getattr(B,'kaggle_submission_agent',None) or B.agent]
env=make("kaggriculture",configuration={"seed":seed}); env.reset()
H=[collections.Counter() for _ in range(2)]; U=[collections.Counter() for _ in range(2)]; AGE=[collections.Counter() for _ in range(2)]
for t in range(720):
    obs=[env._Environment__get_shared_state(i).observation for i in (0,1)]
    acts=[ag[i](obs[i],env.configuration) for i in (0,1)]
    day=t//24
    for i in (0,1):
        f=obs[0]['farms'][i]; units=[f['farmer']]+f['hands']
        for u,(c) in zip(units,[acts[i]['farmer']]+acts[i]['hands']):
            if c and c[0]=='HARVEST':
                tl=f['tiles'][u[1]][u[0]]
                if isinstance(tl,dict) and tl.get('yield_units',0)>0:
                    if 'animal' in tl: k=tl['animal']
                    else: k=tl['crop']; AGE[i][(k,day-tl['planted_day'])]+=1
                    H[i][k]+=1; U[i][k]+=tl['yield_units']
    env.step(acts)
    if env.done: break
print('FINAL',[s.reward for s in env.state])
for k in sorted(set(H[0])|set(H[1])):
    print(f"{k:12s} A harvests {H[0][k]:4d} units {U[0][k]:5d}   B harvests {H[1][k]:4d} units {U[1][k]:5d}")
for i in (0,1):
    print('ages',i,sorted((k,v) for k,v in AGE[i].items() if k[0] in ('WHEAT','STRAWBERRY','MELON','CARROT')))
