import importlib.util,sys,collections,time
from kaggle_environments import make
def load(p,n):
    s=importlib.util.spec_from_file_location(n,p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m.agent
def passer(obs,cfg=None): return {"farmer":["PASS"],"hands":[],"market":[]}
eng=load(sys.argv[1],"E"); opp=passer if sys.argv[2]=="pass" else load(sys.argv[2],"O"); seed=int(sys.argv[3]) if len(sys.argv)>3 else 7
env=make("kaggriculture",configuration={"seed":seed},debug=True); t=time.time(); env.run([eng,opp]); st=env.steps
print("reward",[s.reward for s in st[-1]],"status",[s.status for s in st[-1]],"time",round(time.time()-t,1),"shops",st[-1][0].observation["town"]["unlocked_shops"][:4])
def render(tiles):
    out=[]
    for row in tiles:
        s=""
        for tl in row:
            if tl is None: s+="."
            elif tl=="LOCKED": s+="#"
            elif tl.get("kind")=="WEED": s+="x"
            elif tl.get("kind")=="PLANT": s+=tl["crop"][0].lower()
            elif tl.get("animal"): s+=tl["animal"][0]
            else: s+=tl["kind"][0]
        out.append(s)
    return out
for day in range(30):
    t1=min(day*24+23,719); f=st[t1][0].observation["farms"][0]; pv=st[t1][0].observation["private"]
    c=collections.Counter()
    for row in f["tiles"]:
        for tl in row:
            if isinstance(tl,dict): c[tl.get("crop") or tl.get("animal") or tl.get("kind")]+=1
    mk=collections.Counter()
    for i in range(day*24,t1):
        for o in st[i+1][0].action.get("market") or []:
            if o[0]=="SELL": mk[o[1]]+=int(o[2])
    unw=sum(1 for row in f["tiles"] for tl in row if isinstance(tl,dict) and tl.get("kind")=="PLANT" and not tl.get("watered_today"))
    unf=sum(1 for row in f["tiles"] for tl in row if isinstance(tl,dict) and tl.get("animal") and not tl.get("fed_today"))
    unc=sum(1 for row in f["tiles"] for tl in row if isinstance(tl,dict) and tl.get("animal") and not tl.get("cared_today"))
    npass=sum(1 for i in range(day*24+2,t1) for u in [st[i+1][0].action.get("farmer")]+list(st[i+1][0].action.get("hands") or []) if u and u[0]=="PASS")
    if day in (0,1,2,3,5,6,8,10,11,12,15,20,25,29) or len(sys.argv)>4:
        print(f"    unwatered {unw} unfed {unf} uncared {unc} PASS-steps {npass}")
        print(f"D{day:2d} money {int(f['money']):6d} hands {len(st[day*24+12][0].observation['farms'][0]['hands']):2d} shed {sum(pv['shed'].values()):3d} wheat {pv['shed'].get('WHEAT',0):3d} seeds {dict((k,v) for k,v in pv['seeds'].items() if v)} tiles {dict(c)} sold {dict(mk)}")
    if day in (1,6,12,20) and len(sys.argv)>4:
        for r in render(f["tiles"]): print("    ",r)
