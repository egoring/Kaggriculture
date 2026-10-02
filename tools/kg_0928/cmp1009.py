import re,glob
def parse(files):
    d={}
    for f in files:
        for l in open(f):
            m=re.match(r'(\d+) (.{12}) rec\s+([+-]\d+) rep\s+([+-]\d+)',l)
            if m: d[int(m.group(1))]=(m.group(2).strip(),int(m.group(3)),int(m.group(4)))
    return d
a=parse(['/root/kg/ev/tf879_all.txt']); b=parse(glob.glob('/root/kg/ev/tf1009_*.txt'))
common=sorted(set(a)&set(b))
wa=sum(a[e][2]>0 for e in common); wb=sum(b[e][2]>0 for e in common)
print(f"common {len(common)}: v877 wins {wa} avg {sum(a[e][2] for e in common)/max(1,len(common)):+.0f} | v878 wins {wb} avg {sum(b[e][2] for e in common)/max(1,len(common)):+.0f} | v878-v877 avg {sum(b[e][2]-a[e][2] for e in common)/max(1,len(common)):+.0f}, better in {sum(b[e][2]>a[e][2] for e in common)}")
flips=[(e,a[e][0],a[e][2],b[e][2]) for e in common if (a[e][2]>0)!=(b[e][2]>0)]
print('flips',flips[:20])
