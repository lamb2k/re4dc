#!/usr/bin/env python3
"""Exact immutable strip-block sharing for existing prelit SDO3 alternates.

This never changes a vertex, corner/index, strip order, LOD or source ID. It
writes only to a new explicit output directory; original assets stay intact.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import zlib
from offline_dedup import Package


def align(n,a):return (n+a-1)&~(a-1)
def digest(b):return hashlib.sha256(b).hexdigest()


def layout(p):
    h=p.h;l=struct.unpack_from('<8I',p.data,80)
    # Source extent uses reserved[1] only under this existing prelit marker;
    # no oct-vertex colour table, classes/rules or runtime extension is moved.
    if l[5] or l[6] or l[7]:raise ValueError('unsupported extra LOD tables')
    if h[17] and h[17]<len(p.data):raise ValueError('source extent below physical bytes')
    sections=[(0,112),(h[10],68*h[4]),(h[11],36*h[5]),(h[12],28*h[6]),
              (h[13],12*h[7]),(h[14],h[8]),(h[15],4*h[9]),
              (l[2],8*h[5]),(l[3],20*l[0]),(l[4],12*l[1])]
    last=0
    for off,size in sections:
        if off<last or off+size>len(p.data) or off%4:raise ValueError('unsupported section layout')
        last=off+size
    if h[15]%32:raise ValueError('palette tail alignment')
    return l


def block(p,l):
    n=l['size']+(2*l['n'] if l['ix'] else 0)
    return p.data[p.h[14]+l['fs']:p.h[14]+l['fs']+n]


def validate(before,after):
    a=Package(before,True);b=Package(after,True);al=layout(a);bl=layout(b)
    fixed=(0,1,4,5,6,7,9,10,11,12,13,14,16,18,19)
    if any(a.h[i]!=b.h[i] for i in fixed):raise ValueError('shape/source changed')
    if b.h[17]!=(a.h[17] or len(before)):raise ValueError('source extent changed')
    if after[a.h[13]:a.h[13]+12*a.h[7]]!=before[a.h[13]:a.h[13]+12*a.h[7]]:raise ValueError('vertex bytes changed')
    for x,y in zip(a.lets,b.lets):
        old=before[x['offset']:x['offset']+28];new=after[y['offset']:y['offset']+28]
        if old[:4]!=new[:4] or old[8:]!=new[8:] or block(a,x)!=block(b,y):raise ValueError('meshlet/strip bytes changed')
    for off,count,stride in ((a.h[10],a.h[4],68),(a.h[11],a.h[5],36)):
        if before[off:off+count*stride]!=after[off:off+count*stride]:raise ValueError('source record changed')
    if before[a.h[15]:]!=after[b.h[15]:]:raise ValueError('LOD/palette tail changed')
    delta=a.h[15]-b.h[15]
    if any(bl[i]!=al[i]-delta for i in (2,3,4)):raise ValueError('LOD absolute offsets changed')
    if tuple(al[:2])!=tuple(bl[:2]) or tuple(al[5:])!=tuple(bl[5:]):raise ValueError('LOD counts changed')
    return a,b


def groups_rekey(groups,a,b):
    if groups is None:return None
    if len(groups)<32:raise ValueError('short SG')
    w=struct.unpack_from('<4s7I',groups)
    if w[:3]!=(b'R4SG',1,a.h[6]) or not 1<=w[3]<=8 or w[4]!=a.h[3] or w[5]!=len(a.data) or len(groups)!=32+16*w[3]*a.h[6] or zlib.crc32(groups[32:])!=w[7]:raise ValueError('SG identity/body')
    g=bytearray(groups);struct.pack_into('<II',g,16,b.h[3],len(b.data))
    if g[32:]!=groups[32:]:raise ValueError('SG records changed')
    return bytes(g)


def pack(mesh,groups=None):
    p=Package(mesh,True);lh=layout(p);h=p.h
    strip=bytearray();seen={};offsets=[];duplicates=0
    for l in p.lets:
        raw=block(p,l)
        if raw in seen:duplicates+=1;off=seen[raw]
        else:
            strip.extend(bytes(align(len(strip),2)-len(strip)));off=len(strip)
            seen[raw]=off;strip.extend(raw)
        offsets.append(off)
    tail=align(h[14]+len(strip),32);delta=h[15]-tail
    if delta<0:raise ValueError('sharing would grow package')
    out=bytearray(mesh[:h[14]])+strip
    out.extend(bytes(tail-len(out)));out.extend(mesh[h[15]:])
    for l,off in zip(p.lets,offsets):struct.pack_into('<I',out,l['offset']+4,off)
    struct.pack_into('<I',out,8,len(out));struct.pack_into('<I',out,32,len(strip))
    struct.pack_into('<I',out,60,tail);struct.pack_into('<I',out,68,h[17] or len(mesh))
    for i in (2,3,4):struct.pack_into('<I',out,80+4*i,lh[i]-delta)
    struct.pack_into('<I',out,12,zlib.crc32(out[80:]))
    a,b=validate(mesh,bytes(out));g=groups_rekey(groups,a,b)
    return bytes(out),g,dict(input_bytes=len(mesh),output_bytes=len(out),allocation_saving=align(len(mesh),32)-align(len(out),32),
        strip_bytes_before=h[8],strip_bytes_after=len(strip),meshlets=len(p.lets),unique_blocks=len(seen),duplicate_blocks=duplicates,
        source_bytes=b.h[17],source_crc=b.h[18],body_crc=b.h[3],input_sha256=digest(mesh),output_sha256=digest(out),
        ordered_strip_and_index_bytes_equal=True,all_vertex_bytes_equal=True,lod_and_source_records_equal=True)


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('mesh',type=Path)
    ap.add_argument('--groups',type=Path);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();m,g,report=pack(a.mesh.read_bytes(),a.groups.read_bytes() if a.groups else None)
    files={'ps2-dd3.re4mesh':m}
    if g is not None:files['ps2-dd3.r4sg']=g
    a.out.mkdir(parents=True,exist_ok=False)
    for name,b in files.items():(a.out/name).write_bytes(b)
    report.update(input_path=str(a.mesh),groups_input_path=str(a.groups) if a.groups else None,
        files={name:dict(bytes=len(b),sha256=digest(b)) for name,b in files.items()},
        scope='Offline exact-byte sharing only; target memory/movie/render gates NOT RUN')
    (a.out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))


if __name__=='__main__':main()
