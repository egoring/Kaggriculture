import importlib.util,sys,multiprocessing as mp
from kaggle_environments import make
def load(p,n):
    s=importlib.util.spec_from_file_location(n,p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m.agent
def passer(obs,cfg=None): return {"farmer":["PASS"],"hands":[],"market":[]}
def run(a):
    f,sd=a; env=make("kaggriculture",configuration={"seed":sd}); env.run([load(f,"E"),passer]); return sd,env.steps[-1][0].reward
if __name__=="__main__":
    f=sys.argv[1]; seeds=[int(x) for x in sys.argv[2].split(",")]
    with mp.Pool(2) as p: res=p.map(run,[(f,s) for s in seeds])
    print(f, "solo mean", round(sum(r for _,r in res)/len(res)), [int(r) for _,r in sorted(res)])
