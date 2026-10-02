import pickle,importlib.util,collections,sys
from kaggle_environments import make
def load(p):
    s=importlib.util.spec_from_file_location('C'+str(abs(hash(p))),p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return getattr(m,'kaggle_submission_agent',None) or m.agent
def useq(acts): return tuple(( tuple((a or {}).get('farmer') or []), tuple(map(tuple,(a or {}).get('hands') or [])) ) for a in acts)
refs={}
for name,f in (('m2965','m2965.py'),('v57','v57.py'),('W20','W20.py'),('W20v41','W20v41.py'),('v56','nb/v56_main.py'),('v55','nb/v55_main.py'),('metav4','W20.py')):
    if name=='metav4': continue
    env=make("kaggriculture",configuration={"seed":268039310}); env.run([load(f),load('m2965.py')])
    acts=[env.steps[i+1][0]['action'] for i in range(144)]; refs[name]=useq(acts)
pickle.dump(refs,open('prefix_refs.pkl','wb'))
print({k:sum(1 for a,b in zip(v,refs['m2965']) if a!=b) for k,v in refs.items()})
