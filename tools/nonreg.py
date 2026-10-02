import sys,importlib.util,multiprocessing as mp
from kaggle_environments import make
def load(p,n):
    s=importlib.util.spec_from_file_location(n,p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m.agent
def run(args):
    me,opp,sd=args
    A=load(me,"A"); B=load(opp,"B")
    env=make("kaggriculture",configuration={"seed":sd}); env.run([A,B]); r=[s.reward for s in env.steps[-1]]
    return opp,sd,r[0],r[1]
if __name__=="__main__":
    me=sys.argv[1]; opps=sys.argv[2].split(","); seeds=[int(x) for x in sys.argv[3].split(",")]
    out={}
    with mp.Pool(2) as pool:
        for opp,sd,a,b in pool.imap_unordered(run,[(me,o,s) for o in opps for s in seeds]):
            out.setdefault(opp,[]).append((sd,a,b))
    for opp,res in out.items():
        res.sort(); print(f"{me} vs {opp}: {sum(a>b for _,a,b in res)}/{len(res)} mean diff {sum(a-b for _,a,b in res)/len(res):+.0f} diffs {[round(a-b) for _,a,b in res]}",flush=True)
