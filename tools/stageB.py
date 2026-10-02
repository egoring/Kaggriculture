import pickle,sys,json,importlib.util,multiprocessing as mp
from kaggle_environments import make
from tapeagent import make_tape_agent
SEEDS=[int(x) for x in sys.argv[1].split(",")]; OPP=sys.argv[2]; OUT=sys.argv[3]
def load(p,n):
    s=importlib.util.spec_from_file_location(n,p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m.agent
def run(args):
    name,acts,sd=args
    opp=load(OPP,"opp")
    env=make("kaggriculture",configuration={"seed":sd}); env.run([make_tape_agent(acts),opp])
    r=[s.reward for s in env.steps[-1]]; return name,sd,r[0],r[1]
if __name__=="__main__":
    cands=pickle.load(open("cands.pkl","rb"))
    jobs=[(n,a,sd) for n,a in cands.items() for sd in SEEDS]
    out={}
    with mp.Pool(2) as pool:
        for name,sd,a,b in pool.imap_unordered(run,jobs):
            out.setdefault(name,[]).append((sd,a,b))
    for name,res in out.items():
        res.sort(); w=sum(a>b for _,a,b in res)
        print(f"{name:14s} vs {OPP}: {w}/{len(res)}  mean diff {sum(a-b for _,a,b in res)/len(res):+.0f}  diffs {[round(a-b) for _,a,b in res]}")
    json.dump(out,open(OUT,"w"))
