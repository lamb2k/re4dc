import sys,hashlib
sys.path[:0]=['/root/work/lanes/assets-dc/port/dreamcast/tools','/root/work/lanes/assets-dc/port/dreamcast/tools/d367/gc_port23']
import ps2_audio as pa, build_catalog as bc
S='/root/re4data/private/isnd300-20261103'; rel='st3/r300.dar'
d=bytearray(open(S+'/'+rel,'rb').read())
_p,bases=pa.ab.archive_bases(S,rel)
old={(k,w):hashlib.sha256(b).hexdigest() for k,i,b,w in bc.member_rows(rel,bytes(d))}
n=0
for base in bases:
    for (t,mo,ms,ao,h,smp) in pa.gc_blocks(bytes(d),base,False):
        if t!=6: continue
        reach={gs for k,gs,fl in pa.gc_cue_samples(bytes(d),t,mo,ms) if gs is not None}
        assert 22 not in reach
        rate,length,sh,p,nb,loop=smp[22]; m=(length+(1<<sh)-1)>>sh
        enc=pa.ab.yamaha_encode([0]*m); d[p:p+nb]=enc[:nb]+bytes(nb-min(nb,len(enc))); n+=1
assert n==1
open(S+'/'+rel,'wb').write(bytes(d))
new={(k,w):hashlib.sha256(b).hexdigest() for k,i,b,w in bc.member_rows(rel,bytes(d))}
ch={old[x]:new[x] for x in old if old[x]!=new[x]}
L=open(S+'/provenance.tsv').read().splitlines()
out=[L[0]]
for l in L[1:]:
    c=l.split('\t')
    if c[2] in ch:
        c[2]=ch[c[2]]; c[5]=c[5]+'; ROOM sample 22 silenced: no cue reaches it, PS2 r300.snd has no such sound (PS2-dropped)'
    out.append('\t'.join(c))
open(S+'/provenance.tsv','w').write('\n'.join(out)+'\n')
print('changed members',len(ch))
