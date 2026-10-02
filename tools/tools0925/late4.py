import pickle,sys,collections
from kaggle_environments import make
from tapeagent import make_tape_agent
P=pickle.load(open('recs_cache/logs__p866__all.pkl','rb'))
byep={}
for r in P: byep.setdefault(r['ep'],{})[r['seat']]=r
for ep,d in sorted(byep.items()):
    me=[r for r in d.values() if r['name']=='weense'][0]; op=[r for r in d.values() if r is not me][0]
    if op['name'][:12] !='Michael Chen': continue
    ags=[None,None]; ags[me['seat']]='submission_v868_oracle4.py'; ags[op['seat']]=make_tape_agent(op['acts'])
    env=make("kaggriculture",configuration={"seed":me['seed']}); env.run(ags)
    print('our seat',me['seat'])
    T=len(env.steps)-1
    for t in range(660,T+1,2):
        f=env.steps[t][0].observation['farms']; mm=f[me['seat']]['money']; om=f[op['seat']]['money']
        a=env.steps[t][me['seat']].action or {}; b=env.steps[t][op['seat']].action or {}
        pm=env.steps[t][0].observation['private'] if me['seat']==0 else env.steps[t][1].observation['private']
        inv=collections.Counter()
        for x in (pm.get('inventories') or []): inv.update(x)
        print(t, f'us {mm:8.0f} opp {om:8.0f} diff {mm-om:+7.0f}', 'usM',[x for x in (a.get('market') or []) if x and x[0]=='SELL'][:4], 'oppM',[x for x in (b.get('market') or []) if x and x[0]=='SELL'][:4], 'inv',dict(inv))
