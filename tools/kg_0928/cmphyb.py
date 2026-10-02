import re, glob, sys
def parse(files):
    d = {}
    for f in files:
        for l in open(f):
            m = re.match(r'(\d+) (.{12}) rec\s+([+-]\d+) rep\s+([+-]\d+)', l)
            if m: d[int(m.group(1))] = (m.group(2).strip(), int(m.group(3)), int(m.group(4)))
    return d
sets = {'v879': parse(['/root/kg/ev/tf879_all.txt']), '1009': parse(glob.glob('/root/kg/ev/tf1009_*.txt'))}
for tag in sys.argv[1:]:
    sets[tag] = parse(glob.glob('/root/kg/ev/tf%s_*.txt' % tag))
common = sorted(set.intersection(*[set(v) for v in sets.values()]))
print('common episodes', len(common))
import statistics
for k, d in sets.items():
    v = [d[e][2] for e in common]
    print(f"{k:6s} wins {sum(x>0 for x in v):3d}/{len(v)} avg {sum(v)/max(1,len(v)):+7.0f} median {statistics.median(v) if v else 0:+6.0f} loss-avg {sum(x for x in v if x<=0)/max(1,sum(x<=0 for x in v)):+7.0f}")
base = sets['1009']
for k, d in sets.items():
    if k in ('1009',): continue
    better = sum(d[e][2] > base[e][2] for e in common)
    flips = [(e, base[e][0], base[e][2], d[e][2]) for e in common if (base[e][2] > 0) != (d[e][2] > 0)]
    print(f"{k} vs 1009: better in {better}/{len(common)}, avg diff {sum(d[e][2]-base[e][2] for e in common)/max(1,len(common)):+.0f}, flips {len(flips)}: {flips[:12]}")
