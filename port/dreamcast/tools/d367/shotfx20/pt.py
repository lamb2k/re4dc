import re,sys,collections
d=collections.OrderedDict()
for l in open(sys.argv[1],errors='replace'):
    if not l.startswith('PT f='): continue
    m=re.match(r'PT f=(\d+)-(\d+)',l); k=int(m.group(1))
    r=d.setdefault(k,{})
    for kk,v in re.findall(r'(\S+?)=(\d+)/',l): r[kk]=int(v)
cols=sys.argv[2].split(',')
print('frame '+' '.join(cols))
for k,r in d.items():
    if (k-1)%int(sys.argv[3] if len(sys.argv)>3 else 120): continue
    print(k,' '.join(str(r.get(c,'-')) for c in cols))
