import importlib.util,sys,collections,pickle
from kaggle_environments import make
from tapeagent import make_tape_agent
def load(p,n):
    s=importlib.util.spec_from_file_location(n,p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
cand,pool,name=sys.argv[1],sys.argv[2],sys.argv[3]; LIM=int(sys.argv[4]) if len(sys.argv)>4 else 80
ME=load(cand,'ME'); P=pickle.load(open(f'recs_cache/logs__{pool}__all.pkl','rb'))
byep={}
for r in P: byep.setdefault(r['ep'],{})[r['seat']]=r
for ep,d in byep.items():
    me=[r for r in d.values() if r['name']=='weense'][0]; op=[r for r in d.values() if r is not me][0]
    if op['name'].startswith(name): break
rv=make_tape_agent(op['acts']); seed=me['seed']; mes=me['seat']
env=make("kaggriculture",configuration={"seed":seed}); env.reset()
cfg=dict(env.configuration); cfg['__raw_path__']='/root/kg/'+cand
um=0; mm=[]; same=0
def mk(a): 
    d={}
    for o in (a.get('market') or []):
        if o: d.setdefault(tuple(o[:2]),0); d[tuple(o[:2])]+=int(o[2]) if len(o)>2 else 0
    return d
for t in range(720):
    obs=[env._Environment__get_shared_state(i).observation for i in (0,1)]
    acts=[None,None]; acts[mes]=ME.kaggle_submission_agent(obs[mes],cfg); acts[1-mes]=rv(obs[1-mes],env.configuration)
    st=ME._ORC.get(mes); rt=(st or {}).get('last_rt') or {}
    shd=dict(((st or {}).get('rv_private') or {}).get('shed') or {})
    a1=acts[1-mes] or {}
    if rt.get('farmer')!=a1.get('farmer') or rt.get('hands')!=a1.get('hands'): um+=1
    if mk(rt)!=mk(a1):
        r,a=mk(rt),mk(a1); keys=sorted(set(r)|set(a))
        mm.append((t,[(':'.join(str(z)[:5] for z in k),r.get(k,'-'),a.get(k,'-'),'shed',shd.get(k[1] if len(k)>1 else '',0)) for k in keys if r.get(k)!=a.get(k)]))
    else: same+=1
    env.step(acts)
    if env.done: break
rw=[s.reward for s in env.state]; print(name,'margin %+.0f'%(rw[mes]-rw[1-mes]),'unit mismatch steps',um,'market same',same,'diff',len(mm))
for x in mm[:LIM]: print(x)
