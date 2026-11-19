"""Bake static materials and unchanged logic values. The display program selects all draws."""
import argparse
import collections
import struct
import zlib
from pathlib import Path
from native_models import models
from logic_delta import Changes
from native_world import whole_world
from pack_scene import Baker, Table, block, pack

def build(disc, capture, room, tables):
    assets = Baker(disc, capture, room)
    def world_material(key, phase, cull):
        return assets.header(key, (0,2,3)[phase], cull, world=True, fog=True)
    world = whole_world(disc / f"native/r{room:x}", world_material)
    actor_models=models(disc,tables,(capture/"leon-bind.bin").read_bytes(),lambda key,phase:assets.header(key,phase,fog=True))
    import json
    from native_extra import build_extra
    extra=capture/"extra-models.json"
    prop_ids={}
    if extra.exists():
        ids=sorted({t for _,t,_ in json.loads(extra.read_text())})
        prop_ids={t:6+i for i,t in enumerate(ids)}
        prior=capture.parent/("eng-bench-"+("cross" if room==0x101 else "hayfork")+"-4")
        actor_models+=build_extra(assets,prior,ids)
    samples = [Table() for _ in range(8)]
    missing=collections.Counter()
    material_cache={}
    def sprite_header(data,offset,phase):
        key=struct.unpack_from("<2I",data,offset)
        if key==(0,0):return 0xffffffff
        tag=key,phase
        if tag not in material_cache:
            if key in assets.lookup:
                material_cache[tag]=assets.header(key,phase,fog=phase==4)
            else:
                missing[tag]+=1
                material_cache[tag]=0xffffffff
        return material_cache[tag]
    frames = []
    changes = [Changes() for _ in samples]
    previous = None
    for picture in range(1,301):
        path = capture / f"picture-{picture:03}.bin"
        b = path.read_bytes()
        magic, r, seq, tick = struct.unpack_from("<4s3I", b)
        if (magic,r,seq)!=(b"LOG3",room,picture) or (previous is not None and tick!=previous+1):
            raise ValueError(f"logic discontinuity in {path}")
        previous = tick
        groups = collections.defaultdict(bytearray)
        offset = 16
        while offset < len(b):
            kind,size = struct.unpack_from("<2I",b,offset)
            offset += 8
            if kind not in range(1,9) or offset+size>len(b):
                raise ValueError(f"invalid logic record in {path}")
            record=bytearray(b[offset:offset+size])
            if kind==2 and struct.unpack_from("<I",record)[0]==2:
                struct.pack_into("<I",record,8,prop_ids[struct.unpack_from("<I",record,8)[0]])
            if kind==4 and size==148:
                struct.pack_into("<I",record,128,sprite_header(record,128,4))
            if kind==7:
                if size!=60:raise ValueError("glyph source format")
                struct.pack_into("<I",record,28,sprite_header(record,28,5))
            if kind==6 and size==96:
                hdr=sprite_header(record,16,5)
                struct.pack_into("<I",record,16,hdr)
            groups[kind].extend(record)
            offset += size
        if len(groups[1])!=104 or not groups[2] or not groups[6] or not groups[8]:
            raise ValueError(f"missing logic output in {path}: {[(k,len(v)) for k,v in groups.items()]}")
        frames.append(pack("9I",tick,*(table.add(changes[i].encode(groups[i+1])) for i,table in enumerate(samples))))
    sections = [block(t.rows) for t in [assets.textures,assets.headers]]
    sections += [world,block(frames),*(block(t.rows) for t in samples)]
    sections.append(block(actor_models))
    sections.append(pack("2f",assets.top,assets.bottom))
    data = block(sections)
    print("missing source textures",len(missing),"texture count",len(assets.textures.rows))
    print("room",hex(room),"resident pack",len(data)+20,"sections",list(map(len,sections)))
    return pack("4s4I",b"NAT3",3,room,len(data),zlib.crc32(data))+data

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("disc",type=Path)
    p.add_argument("capture",type=Path)
    p.add_argument("room",type=lambda s:int(s,16))
    p.add_argument("out",type=Path)
    p.add_argument("tables",type=Path)
    a=p.parse_args()
    a.out.write_bytes(build(a.disc,a.capture,a.room,a.tables))
