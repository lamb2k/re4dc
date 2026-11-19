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

def build(disc, capture, room, tables, prior_dir=None):
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
        prior=(prior_dir or capture.parent)/("eng-bench-"+("cross" if room==0x101 else "hayfork")+"-4")
        actor_models+=build_extra(assets,prior,ids)
    samples = [Table() for _ in range(9)]
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
    def effect_header(data,offset,pair):
        key=struct.unpack_from("<2I",data,offset)
        if key==(0,0):return 0xffffffff
        tag=key,4,pair
        if tag not in material_cache:
            if key in assets.lookup:material_cache[tag]=assets.header(key,4,blend=pair,fog=True)
            else:missing[tag]+=1;material_cache[tag]=0xffffffff
        return material_cache[tag]
    import numpy as np, dctex
    def masked_header(data,offset,phase):
        """HUD widget with a mask texture (eng-e0b): the source multiplies the widget texture's alpha by the mask's
        (IdSys TEV stage 1). Baked here as one texture: the widget texture's colour, alpha = texture x mask."""
        key=struct.unpack_from("<2I",data,offset);mask=struct.unpack_from("<2I",data,offset+8)
        tag=key,mask,phase
        if tag not in material_cache:
            if mask not in assets.lookup:
                missing[tag]+=1;material_cache[tag]=sprite_header(data,offset,phase);return material_cache[tag]
            def img(k):
                off,size=assets.lookup[k];return dctex.decode(assets.texpack[off:off+size])
            m=img(mask);t=img(key) if key in assets.lookup and key!=(0,0) else np.full_like(m,255)
            if m.shape!=t.shape:
                ys=(np.arange(t.shape[0])*m.shape[0]//t.shape[0]);xs=(np.arange(t.shape[1])*m.shape[1]//t.shape[1])
                m=m[ys][:,xs]
            out=t.copy();out[...,3]=(t[...,3].astype(np.uint32)*m[...,3]//255).astype(np.uint8)
            pkg=dctex.encode_4444(out,b"hud-masked")
            ck=(zlib.crc32(pkg),0x4b53414d)
            if ck not in assets.lookup:
                assets.lookup[ck]=(len(assets.texpack),len(pkg));assets.texpack+=pkg
            material_cache[tag]=assets.header(ck,phase,fog=False)
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
            if kind not in range(1,10) or offset+size>len(b):
                raise ValueError(f"invalid logic record in {path}")
            record=bytearray(b[offset:offset+size])
            if kind==2 and struct.unpack_from("<I",record)[0]==2:
                struct.pack_into("<I",record,8,prop_ids[struct.unpack_from("<I",record,8)[0]])
            if kind==4 and size==152:
                # the effect's own GX blend (type, src, dst): GX and PVR share the factor codes 0-7
                # (zero, one, other colour, inverse other colour, src alpha, inverse, dst alpha, inverse)
                blend=struct.unpack_from("<I",record,148)[0]
                bt,bs,bd=blend&255,blend>>8&255,blend>>16&255
                pair=(bs&7,bd&7) if bt==1 else (4,5)
                struct.pack_into("<I",record,128,effect_header(record,128,pair))
            if kind==7:
                if size!=60:raise ValueError("glyph source format")
                struct.pack_into("<I",record,28,sprite_header(record,28,5))
            if kind==6 and size==96:
                masked=struct.unpack_from("<2I",record,24)!=(0,0)
                hdr=masked_header(record,16,5) if masked else sprite_header(record,16,5)
                struct.pack_into("<I",record,16,hdr)
                struct.pack_into("<2I",record,24,int(masked),0)   # mask applied at bake; 1 = a masked backdrop
            groups[kind].extend(record)
            offset += size
        if len(groups[1])!=104 or not groups[2] or not groups[6] or not groups[8]:
            raise ValueError(f"missing logic output in {path}: {[(k,len(v)) for k,v in groups.items()]}")
        frames.append(pack("10I",tick,*(table.add(changes[i].encode(groups[i+1])) for i,table in enumerate(samples))))
    sections = [block(t.rows) for t in [assets.textures,assets.headers]]
    sections += [world,block(frames),*(block(t.rows) for t in samples)]
    sections.append(block(actor_models))
    sections.append(pack("2f",assets.top,assets.bottom))
    data = block(sections)
    print("missing source textures",len(missing),"texture count",len(assets.textures.rows))
    print("room",hex(room),"resident pack",len(data)+20,"sections",list(map(len,sections)))
    return pack("4s4I",b"NAT3",4,room,len(data),zlib.crc32(data))+data

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("disc",type=Path)
    p.add_argument("capture",type=Path)
    p.add_argument("room",type=lambda s:int(s,16))
    p.add_argument("out",type=Path)
    p.add_argument("tables",type=Path)
    p.add_argument("--prior",type=Path,help="folder holding the first capture's eng-bench-<scene>-4 RAM snapshot")
    a=p.parse_args()
    a.out.write_bytes(build(a.disc,a.capture,a.room,a.tables,a.prior))
