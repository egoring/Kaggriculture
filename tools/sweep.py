import sys, importlib.util
from kaggle_environments import make
def load(p,name,tape):
    s=importlib.util.spec_from_file_location(name,p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m)
    def sel(obs,step,seat,_m=m,_t=tape):
        st=_m._STATE[seat]; st["cur"]=_t; st["last"]=step; return _t
    m._select=sel; return m.agent
seeds=[7,17,27,37]
A=load("submission_v89.py","A",0)
for t in range(1,14):
    B=load("submission_v89.py","B%d"%t,t); res=[]
    for sd in seeds:
        env=make("kaggriculture",configuration={"seed":sd}); env.run([A,B])
        r=[s.reward for s in env.steps[-1]]; res.append((r[0],r[1]))
    w=sum(b>a for a,b in res)
    print(f"tape{t:2d} vs tape0: tape{t} wins {w}/{len(seeds)}  mean tape{t} {sum(b for a,b in res)/len(res):.0f}  tape0 {sum(a for a,b in res)/len(res):.0f}  diffs {[round(b-a) for a,b in res]}", flush=True)
