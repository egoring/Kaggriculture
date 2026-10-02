import pickle,sys,json,importlib.util,multiprocessing as mp
from kaggle_environments import make
from tapeagent import make_tape_agent
SEEDS=[int(x) for x in sys.argv[1].split(",")]
OUT=sys.argv[2]
def load(p,n):
    s=importlib.util.spec_from_file_location(n,p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m.agent
def run(args):
    h,acts=args
    base=load("submission_v812.py","base")
    res=[]
    for sd in SEEDS:
        env=make("kaggriculture",configuration={"seed":sd}); env.run([make_tape_agent(acts),base])
        r=[s.reward for s in env.steps[-1]]; res.append((sd,r[0],r[1]))
    return h,res
if __name__=="__main__":
    recs=pickle.load(open("recs.pkl","rb"))
    names=set(sys.argv[3].split(",")) if len(sys.argv)>3 else None
    uniq={}
    for r in recs:
        if names and r["name"] not in names: continue
        uniq.setdefault(r["hash"],r)
    items=[(h,r["acts"]) for h,r in uniq.items()]
    print("tapes",len(items),flush=True)
    out={}
    with mp.Pool(2) as pool:
        for h,res in pool.imap_unordered(run,items):
            out[h]=res; r=uniq[h]
            w=sum(a>b for _,a,b in res); print(f"{r['name']:14s} {r['prof']:8s} ep{r['ep']} {h} wins {w}/{len(res)} diffs {[round(a-b) for _,a,b in res]}",flush=True)
            json.dump(out,open(OUT,"w"))
