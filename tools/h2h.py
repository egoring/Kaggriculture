import sys, importlib.util, json, time
from kaggle_environments import make
def load(p,name,tape=None):
    s=importlib.util.spec_from_file_location(name,p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m)
    if tape is not None:
        def sel(obs,step,seat,_m=m,_t=tape):
            st=_m._STATE[seat]; st["cur"]=_t; st["last"]=step; return _t
        m._select=sel
    return m.agent
# args: fileA[:tape] fileB[:tape] seeds...
def parse(a):
    if ":" in a: f,t=a.split(":"); return f,int(t)
    return a,None
fa,ta=parse(sys.argv[1]); fb,tb=parse(sys.argv[2]); seeds=[int(x) for x in sys.argv[3:]]
A=load(fa,"A",ta); B=load(fb,"B",tb)
tot=[0,0]; w=0; n=0
for sd in seeds:
    for flip in (0,1):
        env=make("kaggriculture",configuration={"seed":sd})
        env.run([B,A] if flip else [A,B])
        r=[s.reward for s in env.steps[-1]]
        ra,rb=(r[1],r[0]) if flip else (r[0],r[1])
        n+=1; w+= ra>rb; tot[0]+=ra; tot[1]+=rb
        print(f"seed {sd} flip {flip}: A {ra:.0f}  B {rb:.0f}  diff {ra-rb:+.0f}", flush=True)
print(f"A wins {w}/{n}  meanA {tot[0]/n:.0f} meanB {tot[1]/n:.0f} meandiff {(tot[0]-tot[1])/n:+.0f}")
