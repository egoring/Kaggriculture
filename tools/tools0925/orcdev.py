import importlib.util,sys,collections,pickle
from kaggle_environments import make
from tapeagent import make_tape_agent
def load(p,n):
    s=importlib.util.spec_from_file_location(n,p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
cand=sys.argv[1]; kind=sys.argv[2]  # file:<path>:<seed>  or tape:<pool>:<name>
ME=load(cand,'ME')
if kind.startswith('file:'):
    _,p,seed=kind.split(':'); RV=load(p,'RV'); rv=(getattr(RV,'kaggle_submission_agent',None) or RV.agent); seed=int(seed); mes=0
else:
    _,pool,name=kind.split(':'); P=pickle.load(open(f'recs_cache/logs__{pool}__all.pkl','rb'))
    byep={}
    for r in P: byep.setdefault(r['ep'],{})[r['seat']]=r
    for ep,d in byep.items():
        me=[r for r in d.values() if r['name']=='weense'][0]; op=[r for r in d.values() if r is not me][0]
        if op['name'].startswith(name): break
    rv=make_tape_agent(op['acts']); seed=me['seed']; mes=me['seat']
env=make("kaggriculture",configuration={"seed":seed}); env.reset()
cfg=dict(env.configuration); cfg['__raw_path__']='/root/kg/'+cand
b=collections.defaultdict(lambda:[0,0,0,0,0.0])
for t in range(720):
    obs=[env._Environment__get_shared_state(i).observation for i in (0,1)]
    st=ME._ORC.get(mes)
    if st and st.get('pending'):
        pf=st['pending']; real=obs[0]['farms'][1-mes]; md=abs(float(pf['farm']['money'])-float(real['money']))
        inv=obs[0]['market']['inventory']; idv=sum(abs(int(inv.get(k,0))-int(v)) for k,v in pf['inv'].items())
        k=t//96; b[k][0]+=1; b[k][1]+=md>0.5; b[k][2]+=md>20; b[k][3]+=idv>0; b[k][4]+=md
    acts=[None,None]; acts[mes]=ME.kaggle_submission_agent(obs[mes],cfg); acts[1-mes]=rv(obs[1-mes],env.configuration)
    env.step(acts)
    if env.done: break
rw=[s.reward for s in env.state]; print(kind,'margin %+.0f'%(rw[mes]-rw[1-mes]))
for k in sorted(b): print('days %2d-%2d n=%d money_dev>0.5: %2d  >20: %2d  inv_dev>0: %2d  mean money_dev %.1f'%(k*4,k*4+3,b[k][0],b[k][1],b[k][2],b[k][3],b[k][4]/b[k][0]))
