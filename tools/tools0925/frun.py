import sys,time,importlib.util
from kaggle_environments import make
A,B=sys.argv[1],sys.argv[2]; seeds=[int(x) for x in sys.argv[3].split(',')]
for sd in seeds:
    for seat in ((0,) if len(sys.argv)<5 else (0,1)):
        ags=[A,B] if seat==0 else [B,A]
        env=make("kaggriculture",configuration={"seed":sd}); t0=time.time(); env.run(ags); r=[s.reward for s in env.steps[-1]]
        a,b=(r[0],r[1]) if seat==0 else (r[1],r[0])
        print(sd,seat,round(a),round(b),round(a-b),'%.0fs'%(time.time()-t0),[s.status for s in env.steps[-1]],flush=True)
