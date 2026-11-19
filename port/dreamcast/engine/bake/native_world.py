"""Bake the complete room. All partitioning and bounds use room coordinates."""
import collections
import math
import struct
import zlib
from pathlib import Path

def whole_world(directory, material):
    mesh=(directory/"ps2-world.re4mesh").read_bytes()
    side=(directory/"ps2-world.r4pw").read_bytes()
    sky=(directory/"ps2-sky.r4sk").read_bytes()
    sg_file=directory/"ps2-world.r4sg"
    groups=sg_file.read_bytes() if sg_file.exists() else b""
    def read(fmt,data,at):return struct.unpack_from("<"+fmt,data,at)
    version,size,crc=read("3I",mesh,4)
    if mesh[:4]!=b"R4IM" or version!=3 or size!=len(mesh) or zlib.crc32(mesh[80:])!=crc:
        raise ValueError("invalid whole-room mesh")
    _,places,parts,meshes,crc,*_=read("7I",side,4)
    if side[:4]!=b"R4PW" or zlib.crc32(side[32:])!=crc or len(side)!=32+16*parts+52*places:
        raise ValueError("invalid placement sidecar")
    if (meshes,parts)!=read("2I",mesh,16):raise ValueError("world table mismatch")
    mesh_at=read("I",mesh,40)[0]
    sky_count,sky_at=read("HH",sky,36)
    sky_rows=set(read(f"{sky_count}H",sky,48))
    if sky_at<48+2*sky_count:raise ValueError("bad sky placement map")
    meta=bytearray()
    for i in range(parts):
        a,b,w,h,phase,cull,tex,flags=read("IIHH4B",side,32+16*i)
        meta+=struct.pack("<IBBH",material((a,b),phase,cull),phase,flags,0)
    cells=collections.defaultdict(list)
    for i in range(places):
        mi,row,*aff=read("HH12f",side,32+parts*16+i*52)
        if mi>=meshes:raise ValueError("invalid placement mesh")
        mesh_record=mesh_at+68*mi
        origin=read("3f",mesh,mesh_record+20);step=read("3f",mesh,mesh_record+32)
        minimum=read("3f",mesh,mesh_record+44);maximum=read("3f",mesh,mesh_record+56)
        center=[.5*(a+b) for a,b in zip(minimum,maximum)]
        half=[.5*(b-a) for a,b in zip(minimum,maximum)]
        wc=[];wh=[];grid=[]
        for r in range(3):
            m=aff[4*r:4*r+4]
            wc.append(m[3]+sum(a*b for a,b in zip(m,center)))
            wh.append(sum(abs(a)*b for a,b in zip(m,half)))
            grid.extend(m[j]*step[j] for j in range(3))
            grid.append(m[3]+sum(a*b for a,b in zip(m,origin)))
        scale=max(math.sqrt(sum(x*x for x in aff[j:j+3])) for j in (0,4,8))
        record=struct.pack("<4H19f",mi,i,row,int(row in sky_rows),*grid,*wc,*wh,scale)
        cells[math.floor(wc[0]/8192),math.floor(wc[2]/8192)].append((record,wc,wh))
    placements=bytearray();cell_data=bytearray()
    for key,items in sorted(cells.items()):
        first=len(placements)//84
        lo=[min(c[j]-h[j] for _,c,h in items) for j in range(3)]
        hi=[max(c[j]+h[j] for _,c,h in items) for j in range(3)]
        cell_data+=struct.pack("<2I6f",first,len(items),*(.5*(a+b) for a,b in zip(lo,hi)),*(.5*(b-a) for a,b in zip(lo,hi)))
        placements+=b"".join(record for record,_,_ in items)
    chunks=[mesh,meta,placements,cell_data,groups]
    header=struct.pack("<4s6I",b"NWR3",places,len(cells),*map(len,(mesh,meta,placements,cell_data)))
    return header+b"".join(chunks)

if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("room",type=Path);parser.add_argument("out",type=Path)
    args=parser.parse_args()
    keys={}
    def index(key,phase,cull):
        tag=(key,phase,cull)
        return keys.setdefault(tag,len(keys))
    args.out.write_bytes(whole_world(args.room,index))
