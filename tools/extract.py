import json,glob,os,hashlib,collections,pickle
recs=[]
for f in sorted(glob.glob("logs/*/*.json")):
    d=json.load(open(f)); info=d["info"]; names=info["TeamNames"]; steps=d["steps"]
    if len(steps)<720: print("short",f,len(steps)); continue
    town=steps[-1][0]["observation"].get("town",{}) if "town" in steps[-1][0]["observation"] else None
    shops=list((town or {}).get("unlocked_shops",[]))
    for seat in (0,1):
        acts=[steps[i+1][seat]["action"] for i in range(719)]
        # normalize
        h=hashlib.sha256(json.dumps(acts,sort_keys=True).encode()).hexdigest()[:16]
        buys=collections.Counter(); sells=collections.Counter(); hires=0
        for i,a in enumerate(acts):
            for o in (a or {}).get("market") or []:
                if o[0]=="BUY_ANIMAL": buys[o[1]]+=int(o[2]) if len(o)>2 else 1
                elif o[0]=="SELL": sells[o[1]]+=int(o[2])
                elif o[0]=="HIRE": hires+=int(o[1]) if len(o)>1 and str(o[1]).isdigit() else 1
        prof=f"C{buys['COW']}S{buys['SHEEP']}G{buys['GOOSE']}"
        recs.append(dict(file=f,folder=f.split("/")[1],ep=info["EpisodeId"],seed=info["seed"],seat=seat,name=names[seat],opp=names[1-seat],
            reward=d["rewards"][seat],opp_reward=d["rewards"][1-seat],win=d["rewards"][seat]>d["rewards"][1-seat],shops=shops,hash=h,prof=prof,
            sells={k:sells[k] for k in ("MILK","WOOL","EGG","STRAWBERRY","MELON","WHEAT","CARROT","TOMATO")},acts=acts,status=d["statuses"][seat]))
pickle.dump(recs,open("recs.pkl","wb"))
print("records",len(recs))
# per-name summary
byname=collections.defaultdict(list)
for r in recs: byname[r["name"]].append(r)
rows=sorted(byname.items(),key=lambda kv:-len(kv[1]))
for n,rs in rows[:25]:
    w=sum(r["win"] for r in rs); profs=collections.Counter(r["prof"] for r in rs); uniq=len(set(r["hash"] for r in rs))
    print(f"{n:22s} games {len(rs):3d} wins {w:3d} uniq_tapes {uniq:3d} mean {sum(r['reward'] for r in rs)/len(rs):7.0f} profs {dict(profs.most_common(4))}")
