import importlib.util,sys
from kaggle_environments import make
def load(p,n):
    s=importlib.util.spec_from_file_location(n,p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m.agent
def passer(obs,cfg=None): return {"farmer":["PASS"],"hands":[],"market":[]}
eng=load(sys.argv[1],"E"); seed=int(sys.argv[2]); days=[int(x) for x in sys.argv[3].split(",")]
env=make("kaggriculture",configuration={"seed":seed}); env.run([eng,passer]); st=env.steps
for day in days:
    for t in range(day*24,day*24+24):
        o=st[t][0].observation; f=o["farms"][0]; pv=o["private"]; a=st[t+1][0].action
        units=[tuple(f["farmer"])]+[tuple(h) for h in f["hands"]]
        print(f"t{t} h{t%24} money {int(f['money'])} shed {{k:v for k,v in pv['shed'].items() if v}} seeds {{k:v for k,v in pv['seeds'].items() if v}}")
        print("   units:",[(u,dict((k,v) for k,v in inv.items() if v)) for u,inv in zip(units,pv["inventories"])])
        print("   acts :",[a["farmer"]]+list(a["hands"]),"| mkt",a["market"])
