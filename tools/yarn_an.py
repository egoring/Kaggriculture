import re,collections,statistics,sys
rows=collections.defaultdict(list)
for f in sys.argv[1:]:
  for l in open(f):
    m=re.search(r"^(\S+)\s+ep(\d+) vs (.+?)\s*: replay me\s+(-?\d+) opp\s+(-?\d+) \(\s*([+-]?\d+)\) \| recorded me\s+(-?\d+) opp\s+(-?\d+) \(\s*([+-]?\d+)\)",l)
    if m: rows[m.group(1)].append((int(m.group(2)),m.group(3).strip(),int(m.group(6)),int(m.group(9))))
base={e:d for e,_,d,_ in rows["submission_v813.py"]}
for f,rs in rows.items():
    print(f"{f:24s} n={len(rs)} wins {sum(d>0 for _,_,d,_ in rs)}/{len(rs)} mean margin {statistics.mean(d for _,_,d,_ in rs):+.0f}  (recorded {sum(r>0 for *_,r in rs)}/{len(rs)})")
for f,rs in rows.items():
    if f=="submission_v813.py": continue
    dl=[d-base[e] for e,o,d,_ in rs if e in base]
    print(f"  {f}: delta vs v813 mean {statistics.mean(dl):+.0f}, better in {sum(x>0 for x in dl)}/{len(dl)}, per-game {[ (o[:8],d-base[e]) for e,o,d,_ in rs]}")
