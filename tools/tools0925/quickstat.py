import pickle,collections,sys
def fam(r):
    if r["name"]=="Crop Dusta": return "CropDusta(live)"
    s0=[x for x in (r["step0"] or []) if len(x)>2 and x[0]=="BUY_PRODUCT"]; wq=str(s0[0][2]) if s0 else "-"
    return wq+"/"+r["prof"]
for lab in sys.argv[1:]:
    rs=pickle.load(open(f"recs_cache/logs__{lab}__all.pkl","rb"))
    byep=collections.defaultdict(list)
    for r in rs: byep[r["ep"]].append(r)
    games=[]
    for ep,pair in sorted(byep.items()):
        m=[r for r in pair if r["name"]=="weense"][0]; o=[r for r in pair if r is not m][0]; games.append((m,o))
    n=len(games); w=sum(m["win"] for m,_ in games); h=n//2
    print(f"== {lab}: {n}판 {w}승 ({100*w/n:.0f}%) 평균 {sum(m['reward'] for m,_ in games)/n:.0f} vs {sum(o['reward'] for _,o in games)/n:.0f} | 전반 {sum(m['win'] for m,_ in games[:h])}/{h}, 후반 {sum(m['win'] for m,_ in games[h:])}/{n-h}")
    st=collections.defaultdict(lambda:[0,0,[]])
    for m,o in games:
        f=fam(o); st[f][0 if m["win"] else 1]+=1; st[f][2].append(int(m["reward"]-o["reward"]))
    for f,v in sorted(st.items(),key=lambda kv:-(kv[1][0]+kv[1][1]))[:9]:
        print(f"   vs {f:18s} {v[0]}/{v[0]+v[1]}  margin {sum(v[2])/len(v[2]):+7.0f}")
    print("   패배:",[(o["name"][:12],fam(o),int(m["reward"]-o["reward"])) for m,o in games if not m["win"]])
