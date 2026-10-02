import json,glob,os,hashlib,collections,pickle,sys
# usage: extract_cloud.py <folder> <src_dir> [delete]  → recs_cache/logs__<folder>__all.pkl (append/merge by ep)
folder,src=sys.argv[1],sys.argv[2]; delete=len(sys.argv)>3
outp=f"recs_cache/logs__{folder}__all.pkl"
out=pickle.load(open(outp,'rb')) if os.path.exists(outp) else []
seen={(r['ep'],r['seat']) for r in out}
for f in sorted(glob.glob(f"{src}/*.json")):
    try: d=json.load(open(f))
    except Exception as e: print('bad',f,e); continue
    info=d["info"]; names=info["TeamNames"]; steps=d["steps"]
    if len(steps)<720: print("short",f,len(steps)); continue
    town=steps[-1][0]["observation"].get("town",{}) or {}; shops=list(town.get("unlocked_shops",[]))
    for seat in (0,1):
        if (info["EpisodeId"],seat) in seen: continue
        acts=[steps[i+1][seat]["action"] for i in range(719)]
        h=hashlib.sha256(json.dumps(acts,sort_keys=True).encode()).hexdigest()[:16]
        buys=collections.Counter(); sells=collections.Counter()
        for a in acts:
            for o in (a or {}).get("market") or []:
                if not o or len(o)<2: continue
                if o[0]=="BUY_ANIMAL": buys[o[1]]+=int(o[2]) if len(o)>2 else 1
                elif o[0]=="SELL": sells[o[1]]+=int(o[2])
        prof=f"C{buys['COW']}S{buys['SHEEP']}G{buys['GOOSE']}"
        out.append(dict(file=f"logs/{folder}/"+os.path.basename(f),folder=folder,ep=info["EpisodeId"],seed=info["seed"],seat=seat,name=names[seat],opp=names[1-seat],
            reward=d["rewards"][seat],opp_reward=d["rewards"][1-seat],win=d["rewards"][seat]>d["rewards"][1-seat],shops=shops,hash=h,prof=prof,
            sells={k:sells[k] for k in ("MILK","WOOL","EGG","STRAWBERRY","MELON","WHEAT","CARROT","TOMATO")},acts=acts,status=d["statuses"][seat],step0=acts[0].get("market")))
    if delete: os.remove(f)
pickle.dump(out,open(outp,"wb"),protocol=4); print(folder,"records",len(out))
