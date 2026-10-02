import sys,collections,importlib.util,pickle
from kaggle_environments import make
from tapeagent import make_tape_agent
def load(p,n):
    s=importlib.util.spec_from_file_location(n,p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
pool,cand=sys.argv[1],sys.argv[2]; EPS=[int(x) for x in sys.argv[3].split(',')] if len(sys.argv)>3 else None
P=pickle.load(open(f'recs_cache/logs__{pool}__all.pkl','rb'))
byep={}
for r in P: byep.setdefault(r['ep'],{})[r['seat']]=r
TOT=collections.Counter(); N=0
for ep,d in sorted(byep.items()):
    if EPS and ep not in EPS: continue
    me=[r for r in d.values() if r['name']=='weense'][0]; op=[r for r in d.values() if r is not me][0]
    ME=load(cand,'ME%d'%ep); tape=make_tape_agent(op['acts'])
    env=make("kaggriculture",configuration={"seed":me['seed']}); env.reset()
    cfg=dict(env.configuration); cfg['__raw_path__']='/root/kg/'+cand
    G=env.interpreter.__globals__; orig=G['_commit_unit']; CUR={'farms':None,'step':0}
    REV=[collections.Counter(),collections.Counter()]; HOUR=[collections.defaultdict(list),collections.defaultdict(list)]
    def hook(op_,item,price,farm,private,market,shed_capacity=100):
        ok=orig(op_,item,price,farm,private,market,shed_capacity)
        if ok and op_=='SELL':
            pid=0 if farm is CUR['farms'][0] else 1; REV[pid][item]+=price; HOUR[pid][item].append(CUR['step']%24)
        return ok
    G['_commit_unit']=hook
    oi=env.interpreter
    def interp(state, env_):
        CUR['farms']=list(state[0].observation.farms); CUR['step']=int(state[0].observation.step); return oi(state, env_)
    env.interpreter=interp
    for t in range(720):
        obs=[env._Environment__get_shared_state(i).observation for i in (0,1)]
        acts=[None,None]; acts[me['seat']]=ME.kaggle_submission_agent(obs[me['seat']],cfg); acts[op['seat']]=tape(obs[op['seat']],env.configuration)
        env.step(acts)
        if env.done: break
    G['_commit_unit']=orig
    rw=[s.reward for s in env.state]; m,o=me['seat'],op['seat']
    diff={k:REV[m][k]-REV[o][k] for k in set(REV[m])|set(REV[o])}
    for k,v in diff.items(): TOT[k]+=v
    N+=1
    import statistics as S
    hrs={k:(round(S.mean(HOUR[m][k]),1) if HOUR[m][k] else None, round(S.mean(HOUR[o][k]),1) if HOUR[o][k] else None) for k in ('MILK','WOOL','STRAWBERRY','EGG','WHEAT','CARROT')}
    print(f"{ep} {op['name'][:12]:12s} margin {rw[m]-rw[o]:+6.0f} revdiff {dict(sorted(((k,int(v)) for k,v in diff.items()),key=lambda kv:kv[1]))} hours(me,opp) {hrs}",flush=True)
print('TOTAL over',N,'games:',dict(sorted(((k,int(v)) for k,v in TOT.items()),key=lambda kv:kv[1])))
