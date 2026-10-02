import importlib.util,sys,collections
from kaggle_environments import make
def load(p,n):
    s=importlib.util.spec_from_file_location(n,p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
cand,opp=sys.argv[1],sys.argv[2]; seed=int(sys.argv[3])
ME=load(cand,'ME'); RV=load(opp,'RV')
env=make("kaggriculture",configuration={"seed":seed}); env.reset()
cfg=dict(env.configuration); cfg['__raw_path__']='/root/kg/'+cand
IT=("MILK","WOOL","EGG","STRAWBERRY","MELON","CARROT","TOMATO")
dev=collections.defaultdict(lambda:[0,0,0,0])  # per 4 days: steps, sum|dev|, phantom(sell ordered, real shed 0, tracked>0), real-sell-total
for t in range(720):
    obs=[env._Environment__get_shared_state(i).observation for i in (0,1)]
    a0=ME.kaggle_submission_agent(obs[0],cfg); a1=(getattr(RV,'kaggle_submission_agent',None) or RV.agent)(obs[1],env.configuration)
    st=ME._ORC.get(0)
    if st and st.get('rv_private'):
        tr=st['rv_private'].get('shed') or {}; rs=obs[1]['private']['shed']; b=t//96
        dev[b][0]+=1; dev[b][1]+=sum(abs(int(tr.get(k,0))-int(rs.get(k,0))) for k in IT)
        for o in (a1.get('market') or []):
            if o and o[0]=='SELL' and o[1] in IT:
                q=int(o[2]); dev[b][3]+=min(q,int(rs.get(o[1],0)))
                if int(rs.get(o[1],0))< max(1,q//2) : dev[b][2]+=1
    env.step([a0,a1])
    if env.done: break
rw=[s.reward for s in env.state]; print('margin %+.0f'%(rw[0]-rw[1]))
for b in sorted(dev): print('days %2d-%2d  avg|tracked-real shed| %.1f   sell orders with real stock < q/2: %d'%(b*4,b*4+3,dev[b][1]/dev[b][0],dev[b][2]))
