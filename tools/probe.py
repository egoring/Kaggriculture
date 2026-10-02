import json, sys, importlib.util, time
from kaggle_environments import make
def load(p,name):
    s=importlib.util.spec_from_file_location(name,p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m.agent
A=load("submission_v89.py","a"); B=load("submission_v89r.py","b")
seed=int(sys.argv[1]) if len(sys.argv)>1 else 7
env=make("kaggriculture",configuration={"seed":seed},debug=True)
t=time.time(); env.run([A,B]); print("elapsed",round(time.time()-t,1),"status",[s.status for s in env.steps[-1]])
last=env.steps[-1]
for i in range(2):
    o=last[i].observation
    print("seat",i,"reward",last[i].reward)
    pv=o.get("private",{})
    print("  shed",{k:v for k,v in pv.get("shed",{}).items() if v})
    print("  inv",[{k:v for k,v in d.items() if v} for d in pv.get("inventories",[])])
    print("  seeds",{k:v for k,v in pv.get("seeds",{}).items() if v} if isinstance(pv.get("seeds"),dict) else pv.get("seeds"))
    print("  keys",list(pv.keys()))
farm=last[0].observation["farms"][0]
print("farm keys",list(farm.keys()))
print("town",last[0].observation.get("town"))
mk=last[0].observation.get("market")
print("market",mk if not isinstance(mk,dict) else {k:(v if not isinstance(v,dict) else {kk:vv for kk,vv in v.items()}) for k,v in list(mk.items())[:12]})
# count animals/crops at end for seat0
from collections import Counter
c=Counter()
for row in farm["tiles"]:
    for tl in row:
        if isinstance(tl,dict):
            for f in ("crop","animal","kind"):
                if tl.get(f): c[str(tl.get(f))]+=1
print("tiles",dict(c))
# money trajectory
for st in (600,660,690,700,710,715,717,718,719):
    print(st,[env.steps[st][i].observation["farms"][i].get("money") if "money" in env.steps[st][i].observation["farms"][i] else env.steps[st][i].reward for i in range(2)])
