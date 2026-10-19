#!/usr/bin/env python3
"""fnlines.py <hwmodel dir> <function regex> [top]: per source line cycles (nominal pcs) inside matching functions."""
import sys,os,re,subprocess,collections,bisect
E=sys.argv[1]; RX=re.compile(sys.argv[2]); TOP=int(sys.argv[3]) if len(sys.argv)>3 else 30
ELF=E+'/re4dc-game.elf'; T='/opt/toolchains/dc/sh-elf/bin/sh-elf-'
syms=[]
for l in subprocess.run([T+'nm','-n','-C','-S',ELF],capture_output=True,text=True).stdout.splitlines():
    p=l.split(' ',3)
    if len(p)==4 and p[2] in 'TtWw': syms.append((int(p[0],16),int(p[1],16),p[3]))
rng=[(a,a+s) for a,s,n in syms if RX.search(n)]
f=open(E+'/proj/nominal.pcs.tsv'); h=f.readline().rstrip('\n').split('\t'); ix={k:i for i,k in enumerate(h)}
cols=['base','dep_load','dep_fpu','dep_fdiv','dep_other','flock','branch','imiss','dmiss','pfwait','sq','uncached']
pcs={}
for l in f:
    p=l.rstrip('\n').split('\t'); a=int(p[0],16)
    if any(lo<=a<hi for lo,hi in rng): pcs[a]=(sum(float(p[ix[c]]) for c in cols),int(p[1]))
nfr=sum(1 for _ in open(E+'/proj/nominal.frames.tsv'))-1
out=subprocess.run([T+'addr2line','-e',ELF,'-i']+['%x'%a for a in pcs],capture_output=True,text=True).stdout
# with -i, inlined frames add lines; take the first line per address by re-running without -i
out=subprocess.run([T+'addr2line','-e',ELF]+['%x'%a for a in pcs],capture_output=True,text=True).stdout.splitlines()
agg=collections.Counter(); ex=collections.Counter()
for (a,(c,e)),ln in zip(pcs.items(),out):
    k=ln.split('/')[-1]; agg[k]+=c; ex[k]=max(ex[k],e)
tot=sum(agg.values())
print('total %.3f ms/frame over %d frames'%(tot/200000/nfr,nfr))
for k,v in agg.most_common(TOP): print('%7.4f ms  exec/fr %7.1f  %s'%(v/200000/nfr,ex[k]/nfr,k))
