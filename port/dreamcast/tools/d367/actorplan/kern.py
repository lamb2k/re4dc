import sys,collections,bisect,subprocess
E='/mnt/d/Flycast-Evidence/re4-dreamcast/hwcal-20261015/hw-cross'
syms=[]
for l in subprocess.run(['/opt/toolchains/dc/sh-elf/bin/sh-elf-nm','-n','-C',E+'/re4dc-game.elf'],capture_output=True,text=True).stdout.splitlines():
    p=l.split(' ',2)
    if len(p)==3 and p[1] in 'TtWw': syms.append((int(p[0],16),p[2]))
syms.sort(); sa=[a for a,_ in syms]
def nm(a):
    i=bisect.bisect_right(sa,a)-1; return syms[i][1]
f=open(E+'/proj/nominal.pcs.tsv'); hdr=f.readline().rstrip('\n').split('\t')
ix={h:i for i,h in enumerate(hdr)}
cyc=collections.Counter(); mx=collections.Counter(); ex=collections.Counter(); st=collections.defaultdict(collections.Counter)
cols=['base','dep_load','dep_fpu','dep_fdiv','dep_other','flock','branch','imiss','dmiss','pfwait','sq','uncached']
for l in f:
    p=l.rstrip('\n').split('\t'); a=int(p[0],16); n=nm(a)
    if not (n.startswith('re4dc_avk') or 'Part::whole' in n or 'Part::strips' in n or 'pass_positions' in n or 'pass_lights' in n or n.startswith('re4dc_sk1')): continue
    c=sum(float(p[ix[k]]) for k in cols); cyc[n]+=c; e=int(p[1]); ex[n]+=e; mx[n]=max(mx[n],e)
    for k in cols: st[n][k]+=float(p[ix[k]])
NF=40
for n,c in cyc.most_common(25):
    s=st[n];
    print('%-60s cyc/t %8.0f  ms/t %.3f  maxexec/t %7.0f  cyc/iter %6.1f  stall(i %.0f d %.0f)/iter'%(n[:60],c/NF,c/NF/200000,mx[n]/NF,c/max(1,mx[n]),s['imiss']/max(1,mx[n]),(s['dmiss']+s['pfwait'])/max(1,mx[n])))
