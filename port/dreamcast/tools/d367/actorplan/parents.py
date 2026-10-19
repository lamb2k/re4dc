import sys,os,re,bisect,collections
P=sys.argv[1]; T=re.compile(sys.argv[2]); SUB=re.compile(sys.argv[3]) if len(sys.argv)>3 else None
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
    n=re.sub(r'\(anonymous namespace\)::','',n); return n.split('(')[0] if '(' in n and not n.startswith('(') else n[:80]
fn={n:(short(name(nodes[n][1])) if n else '<root>') for n in nodes}
incl={}
order=[];st=[0]
while st:
    n=st.pop();order.append(n);st.extend(kids.get(n,[]))
for n in reversed(order): incl[n]=nodes[n][2]+sum(incl[c] for c in kids.get(n,[]))
def subincl(n):
    if SUB is None: return incl[n]
    t=0;st=[n]
    while st:
        x=st.pop()
        if SUB.search(fn[x]): t+=incl[x]; continue
        st.extend(kids.get(x,[]))
    return t
agg=collections.Counter();cnt=collections.Counter()
for n in nodes:
    if n and T.search(fn[n]):
        par=nodes[n][0]; chain=[]
        x=par
        for _ in range(3):
            if not x: break
            chain.append(fn[x]); x=nodes[x][0]
        k=' < '.join(chain)
        agg[k]+=subincl(n); cnt[k]+=nodes[n][3]
for k,v in agg.most_common(40): print('%7.3f %6.1f/t  %s'%(v/K,cnt[k]/nfr,k[:200]))
