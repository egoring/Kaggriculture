import importlib.util,sys,collections
from kaggle_environments import make
def load(p,n):
    s=importlib.util.spec_from_file_location(n,p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
cand,opp=sys.argv[1],sys.argv[2]; seed=int(sys.argv[3])
ME=load(cand,'ME'); RV=load(opp,'RV')
env=make("kaggriculture",configuration={"seed":seed}); env.reset()
cfg=dict(env.configuration); cfg['__raw_path__']='/root/kg/'+cand
IT=("MILK","WOOL","EGG","STRAWBERRY","MELON","CARROT","TOMATO")
prev=None; miss=[]; nscored=0; nhit=0
for t in range(720):
    obs=[env._Environment__get_shared_state(i).observation for i in (0,1)]
    if prev is not None:
        pobs,pa0,pa1=prev
        draw=ME._race_town(t-1,list(pobs[0]['town'].get('unlocked_shops',[])))
        ours={}
        for o in (pa0.get('market') or []):
            if o and o[0]=='SELL' and o[1] in IT: ours[o[1]]=ours.get(o[1],0)+min(int(o[2]),int(pobs[0]['private']['shed'].get(o[1],0)))
        for o in (pa1.get('market') or []):
            if o and o[0]=='SELL' and o[1] in IT and int(o[2])>0:
                it=o[1]; q=int(o[2]); sh0=int(pobs[1]['private']['shed'].get(it,0)); sh1=int(obs[1]['private']['shed'].get(it,0))
                car=sum(int(x.get(it,0)) for x in pobs[1]['private']['inventories'])
                if sh0+car==0: continue
                exp=min(q,sh0+car); rs=int(obs[0]['market']['inventory'][it])-int(pobs[0]['market']['inventory'][it])+int(draw.get(it,0))-int(ours.get(it,0))
                nscored+=1
                if rs>=max(1,exp//2): nhit+=1
                else: miss.append((t-1,it,'q',q,'exp',exp,'flow',rs,'shed',sh0,'->',sh1,'car',car,'draw',draw.get(it,0),'ours',ours.get(it,0),'inv',int(pobs[0]['market']['inventory'][it]),'->',int(obs[0]['market']['inventory'][it])))
    a0=ME.kaggle_submission_agent(obs[0],cfg); a1=(getattr(RV,'kaggle_submission_agent',None) or RV.agent)(obs[1],env.configuration)
    prev=(obs,a0,a1); env.step([a0,a1])
    if env.done: break
print('scored',nscored,'hit',nhit)
for m in miss[:40]: print(m)
