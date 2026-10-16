import struct, zlib, os, sys, json
P=sys.argv[1]
def mesh(b): n,c=struct.unpack_from('<II',b,8); assert n==len(b) and c==zlib.crc32(b[80:]),'mesh hdr'; return c
def side(b): h=struct.unpack_from('<4s7I',b); assert h[0]==b'R4PW' and zlib.crc32(b[32:])==h[5]; return h
def grp(b,mc,mb,sc):
    w=struct.unpack_from('<4s7I',b)
    ok=w[0]==b'R4SG' and w[4]==mc and w[5]==mb and w[6]==sc and len(b)==32+16*w[2]*w[3] and zlib.crc32(b[32:])==w[7]
    return ok
res={}
for r in sorted(d for d in os.listdir(P) if d.startswith('r1')):
    f=lambda n: open(os.path.join(P,r,n),'rb').read() if os.path.exists(os.path.join(P,r,n)) else None
    m0,pw,ids,g0,m5,g5=[f(n) for n in ('ps2-world.re4mesh','ps2-world.r4pw','ps2-world.ids','ps2-world.r4sg','ps2-wv5.re4mesh','ps2-wv5.r4sg')]
    c0=mesh(m0); h=side(pw); ih=struct.unpack_from('<4s3I',ids); assert ih[0]==b'R4ID' and ih[3]==h[5] and ih[2]==h[2],'ids'
    o=dict(l0=len(m0),sidecar=len(pw),l0_groups_valid=grp(g0,c0,len(m0),h[5]),g_alloc=(len(g0)+31)&~31)
    if m5:
        c5=mesh(m5); o.update(wv5=len(m5),wv5_fits=len(m5)<=len(m0),wv5_groups_valid=grp(g5,c5,len(m5),h[5]),g5_fits=len(g5)<=len(g0))
    res[r]=o; print(r,o)
json.dump(res,open(os.path.join(P,'check.json'),'w'),indent=1)
