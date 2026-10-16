import sys,os,re,bisect,collections
P=sys.argv[1]; ROOT=re.compile(sys.argv[2]); EXCL=re.compile(sys.argv[3]) if len(sys.argv)>3 and sys.argv[3] else None
TOP=int(sys.argv[4]) if len(sys.argv)>4 else 80
syms=[]
for l in open(os.path.join(P,'cg.syms.txt')):
    p=l.rstrip('\n').split(' ',2)
    if len(p)==3: syms.append((int(p[0],16),p[2]))
syms.sort(); sa=[a for a,_ in syms]
def name(a):
    i=bisect.bisect_right(sa,a)-1; return syms[i][1]
nodes={};kids=collections.defaultdict(list)
f=open(os.path.join(P,'cg.cg.tsv'));next(f)
for l in f:
    i,par,e,s,c=l.split('\t');i=int(i);par=int(par);nodes[i]=[par,int(e,16),float(s),int(c)]
    if i: kids[par].append(i)
nfr=sum(1 for _ in open(os.path.join(P,'cgsim.frames.tsv')))-1;K=200000.0*nfr
def short(n):
    n=re.sub(r'\(anonymous namespace\)::','',n)
    return n.split('(')[0] if '(' in n and not n.startswith('(') else n[:80]
fn={n:(short(name(nodes[n][1])) if n else '<root>') for n in nodes}
selfc=collections.Counter(); calls=collections.Counter(); tot=0; rc=0
stack=[(0,False)]
while stack:
    n,ins=stack.pop()
    if EXCL and ins and EXCL.search(fn[n]): continue
    if not ins and ROOT.search(fn[n]): ins=True; rc+=nodes[n][3]
    if ins: selfc[fn[n]]+=nodes[n][2]; calls[fn[n]]+=nodes[n][3]; tot+=nodes[n][2]
    for c in kids.get(n,[]): stack.append((c,ins))
print('subtree /%s/ excl /%s/: self total %.3f ms/tick, %.1f root calls/tick (x2 = per drawn picture)'%(ROOT.pattern,EXCL.pattern if EXCL else '',tot/K,rc/nfr))
for k,v in selfc.most_common(TOP): print('%7.3f %7.1f/t  %s'%(v/K,calls[k]/nfr,k[:100]))
