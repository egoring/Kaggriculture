import pickle,sys,importlib.util,multiprocessing as mp,json
from kaggle_environments import make
from tapeagent import make_tape_agent
# usage: matrix.py rows.pkl cols.pkl seeds out.json   (pkl: dict name-> acts list OR "file:path")
def mk(v):
    if isinstance(v,str) and v.startswith("file:"):
        p=v[5:]; s=importlib.util.spec_from_file_location("m"+str(abs(hash(p))),p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m.agent
    return make_tape_agent(v)
def run(args):
    rn,rv,cn,cv,sd=args
    env=make("kaggriculture",configuration={"seed":sd}); env.run([mk(rv),mk(cv)]); r=[s.reward for s in env.steps[-1]]
    return rn,cn,sd,r[0],r[1]
if __name__=="__main__":
    rows=pickle.load(open(sys.argv[1],"rb")); cols=pickle.load(open(sys.argv[2],"rb")); seeds=[int(x) for x in sys.argv[3].split(",")]
    jobs=[(rn,rv,cn,cv,sd) for rn,rv in rows.items() for cn,cv in cols.items() for sd in seeds]
    out={}
    with mp.Pool(2) as pool:
        for rn,cn,sd,a,b in pool.imap_unordered(run,jobs):
            out.setdefault(rn,{}).setdefault(cn,[]).append((sd,a,b))
    json.dump(out,open(sys.argv[4],"w"))
    cn_list=list(cols)
    print("rows=행(승/판, 평균마진) vs cols")
    print(" "*22+" ".join(f"{c[:11]:>12s}" for c in cn_list))
    for rn in rows:
        cells=[]
        for cn in cn_list:
            res=out[rn][cn]; w=sum(a>b for _,a,b in res); m=sum(a-b for _,a,b in res)/len(res)
            cells.append(f"{w}/{len(res)} {m:+6.0f}")
        print(f"{rn[:22]:22s}"+" ".join(f"{c:>12s}" for c in cells))
