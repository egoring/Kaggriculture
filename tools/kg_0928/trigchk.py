import sys,pickle,importlib.util,collections
from kaggle_environments import make
from tapeagent import make_tape_agent
def load(p,n):
    s=importlib.util.spec_from_file_location(n,p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
ME=load('submission_v888_jatape.py','ME')
out=collections.Counter(); ex=[]
for pool in sys.argv[1:]:
    P=pickle.load(open(f'recs_cache/logs__{pool}__all.pkl','rb')); byep={}
    for r in P: byep.setdefault(r['ep'],{})[r['seat']]=r
    for ep,d in byep.items():
        me=[r for r in d.values() if r['name']=='weense'][0]; op=[r for r in d.values() if r is not me][0]
        if op['name']=='weense': continue
        tape=make_tape_agent(op['acts']); env=make("kaggriculture",configuration={"seed":me['seed']}); env.reset()
        for t in range(2):
            obs=[env._Environment__get_shared_state(i).observation for i in (0,1)]
            acts=[None,None]; acts[me['seat']]=ME.kaggle_submission_agent(obs[me['seat']],env.configuration); acts[op['seat']]=tape(obs[op['seat']],env.configuration)
            env.step(acts)
        obs=env._Environment__get_shared_state(0).observation
        m_me=obs['farms'][me['seat']]['money']; m_op=obs['farms'][op['seat']]['money']
        trig = float(m_me)==float(m_op)
        out[(pool,trig)]+=1
        if trig: ex.append((pool,ep,op['name'][:14],m_me,str(op['step0'])[:70]))
print(out); print('triggered examples:'); [print(x) for x in ex[:20]]
