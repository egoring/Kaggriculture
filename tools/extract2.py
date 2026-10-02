import json,glob,os,hashlib,collections,pickle,sys
os.makedirs("recs_cache",exist_ok=True)
recs=[]
for f in sorted(glob.glob("logs/*/*.json")):
    key=f.replace("/","__")
    cp=f"recs_cache/{key}.pkl"
    if os.path.exists(cp):
        recs.extend(pickle.load(open(cp,"rb"))); continue
    d=json.load(open(f)); info=d["info"]; names=info["TeamNames"]; steps=d["steps"]
    if len(steps)<720: print("short",f,len(steps)); continue
    town=steps[-1][0]["observation"].get("town",{}) or {}
    shops=list(town.get("unlocked_shops",[]))
    out=[]
    for seat in (0,1):
        acts=[steps[i+1][seat]["action"] for i in range(719)]
        h=hashlib.sha256(json.dumps(acts,sort_keys=True).encode()).hexdigest()[:16]
        buys=collections.Counter(); sells=collections.Counter()
        for a in acts:
            for o in (a or {}).get("market") or []:
                if o[0]=="BUY_ANIMAL": buys[o[1]]+=int(o[2]) if len(o)>2 else 1
                elif o[0]=="SELL": sells[o[1]]+=int(o[2])
        prof=f"C{buys['COW']}S{buys['SHEEP']}G{buys['GOOSE']}"
        out.append(dict(file=f,folder=f.split("/")[1],ep=info["EpisodeId"],seed=info["seed"],seat=seat,name=names[seat],opp=names[1-seat],
            reward=d["rewards"][seat],opp_reward=d["rewards"][1-seat],win=d["rewards"][seat]>d["rewards"][1-seat],shops=shops,hash=h,prof=prof,
            sells={k:sells[k] for k in ("MILK","WOOL","EGG","STRAWBERRY","MELON","WHEAT","CARROT","TOMATO")},acts=acts,status=d["statuses"][seat],step0=acts[0].get("market")))
    pickle.dump(out,open(cp,"wb"),protocol=4); recs.extend(out)
pickle.dump(recs,open("recs.pkl","wb"),protocol=4)
print("records",len(recs))
