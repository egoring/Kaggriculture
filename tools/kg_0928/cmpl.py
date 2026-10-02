import re,glob,sys,statistics
def parse(fs):
    d={}
    for f in fs:
        for l in open(f):
            m=re.match(r'(\d+) (.{12}) rec\s+([+-]\d+) rep\s+([+-]\d+)',l)
            if m: d[int(m.group(1))]=(m.group(2).strip(),int(m.group(3)),int(m.group(4)))
    return d
base=parse(glob.glob(sys.argv[1])); 
for pat in sys.argv[2:]:
    d=parse(glob.glob(pat)); E=[e for e in sorted(set(base)&set(d)) if base[e][0]!='weense']
    v=[d[e][2] for e in E]; b=[base[e][2] for e in E]
    print(f"{pat}: n {len(E)} wins {sum(x>0 for x in v)} (base {sum(x>0 for x in b)}) avg {sum(v)/len(v):+.0f} (base {sum(b)/len(b):+.0f}) median {statistics.median(v):+.0f} better {sum(d[e][2]>base[e][2] for e in E)} worse {sum(d[e][2]<base[e][2] for e in E)} flips {[(e,base[e][0],base[e][2],d[e][2]) for e in E if (base[e][2]>0)!=(d[e][2]>0)]}")
