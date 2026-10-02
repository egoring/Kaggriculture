import sys,importlib.util,multiprocessing as mp
from kaggle_environments import make
def load(p,n):
    s=importlib.util.spec_from_file_location(n,p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m.agent
def run(args):
    a,b,sd=args; A=load(a,"A"); B=load(b,"B")
    env=make("kaggriculture",configuration={"seed":sd}); env.run([A,B]); r=[s.reward for s in env.steps[-1]]
    return sd,r[0],r[1],env.steps[-1][0].observation["town"]["unlocked_shops"][:2]
if __name__=="__main__":
    a,b=sys.argv[1],sys.argv[2]; seeds=[int(x) for x in sys.argv[3].split(",")]
    with mp.Pool(2) as pool:
        res=list(pool.imap(run,[(a,b,s) for s in seeds]))
    for sd,x,y,sh in res: print(sd,sh,f"{x:.0f} vs {y:.0f} ({x-y:+.0f})")
    y=[(x,yy) for sd,x,yy,sh in res if sh and sh[0]=="YARN_STORE"]
    print("yarn-first games",len(y),"A wins",sum(x>yy for x,yy in y),"mean",sum(x-yy for x,yy in y)/max(1,len(y)))
