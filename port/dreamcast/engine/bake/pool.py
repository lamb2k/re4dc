"""Build one bone-sorted position stream for parts sharing a pose and scale."""
import struct
from collections import defaultdict

def merge_positions(geometry, ids):
    positions = {}
    for i in ids:
        part=geometry.rows[i]
        count=struct.unpack_from("<I",part,4)[0]
        for (v,) in struct.iter_unpack("8s",part[36:36+8*count]):
            positions[v]=None
    order=sorted(positions,key=lambda v:struct.unpack_from("<H",v,6)[0])
    index={v:i for i,v in enumerate(order)}
    stream=b"".join(order)
    result={}
    for i in ids:
        part=geometry.rows[i]
        count,normals,strips=struct.unpack_from("<3I",part,4)
        remap=[index[v] for (v,) in struct.iter_unpack("8s",part[36:36+8*count])]
        data=bytearray(part[:36]+stream+part[36+8*count:])
        struct.pack_into("<I",data,4,len(order))
        at=36+8*(len(order)+normals)
        for _ in range(strips):
            n,=struct.unpack_from("<I",data,at)
            at+=4
            for j in range(n):
                off=at+j*8
                v,=struct.unpack_from("<H",data,off)
                struct.pack_into("<H",data,off,remap[v])
            at+=8*n
        assert at==len(data)
        result[i]=geometry.add(bytes(data))
    return len(order),result

def bind_shared_positions(baker,phases):
    groups=defaultdict(list)
    for draws in phases:
        for j,(header,idx) in enumerate(draws):
            raw=baker.draws.rows[idx&0x7fffffff]
            _,geo,pose,_=struct.unpack_from("<4I",raw)
            g=baker.geometry.rows[geo]
            if g[:4]==b"IDX2":
                groups[pose,g[16:20]].append((draws,j,header,raw,geo))
    vo=mo=0
    for (pose,_),entries in groups.items():
        if len(entries)<2:continue
        key=tuple(sorted({geo for *_,geo in entries}))
        if key not in baker.pools:baker.pools[key]=merge_positions(baker.geometry,key)
        n,remap=baker.pools[key]
        for draws,j,header,raw,geo in entries:
            row=raw[:4]+struct.pack("<I",remap[geo])+raw[8:]+struct.pack("<2I",vo,mo)
            draws[j]=(header,baker.draws.add(row))
        vo+=n
        mo+=max(1,len(baker.poses.rows[pose])//48-1)
    if vo>8192 or mo>1536:raise ValueError("picture exceeds shared projection workspace")
