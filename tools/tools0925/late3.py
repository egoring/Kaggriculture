import pickle,sys,ast,collections
from kaggle_environments import make
from tapeagent import make_tape_agent
P=pickle.load(open('recs_cache/logs__p866__all.pkl','rb'))
byep={}
for r in P: byep.setdefault(r['ep'],{})[r['seat']]=r
for ep,d in sorted(byep.items()):
    me=[r for r in d.values() if r['name']=='weense'][0]; op=[r for r in d.values() if r is not me][0]
    if op['name'][:12] not in ('Michael Chen','huaiyuyoung','LINXI','Liyi xin ji'): continue
    ags=[None,None]; ags[me['seat']]='submission_v868_oracle4.py'; ags[op['seat']]=make_tape_agent(op['acts'])
    env=make("kaggriculture",configuration={"seed":me['seed']}); env.run(ags)
    def md(t):
        f=env.steps[t][0].observation['farms']; return round(f[me['seat']]['money']-f[op['seat']]['money'])
    def inv(t,s):
        p=env.steps[t][s].observation.get('private') or {}; 
        return sum(sum(x.values()) for x in (p.get('inventories') or []) if isinstance(x,dict))
    T=len(env.steps)-1
    print(op['name'][:12], 'diff d16..d29:',[md(t) for t in range(384,T,48)]+[md(T)], ' our inv d24/d26/d28:',[inv(t,me['seat']) for t in (576,624,672)],' opp inv:',[inv(t,op['seat']) for t in (576,624,672)],flush=True)
    # sells per day last 6 days
    def sells(s,t0,t1):
        c=collections.Counter()
        for t in range(t0,t1):
            a=env.steps[t+1][s].action or {}
            for x in (a.get('market') or []):
                if x and x[0]=='SELL': c[x[1]]+=x[2]
        return dict(c)
    for d0 in range(23,30):
        print('   day',d0,'us',sells(me['seat'],d0*24,min(T,(d0+1)*24)),' opp',sells(op['seat'],d0*24,min(T,(d0+1)*24)))
