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
    # eng-look: distance variants appended after the catalogue (base 6 + props), listed in section 14's tail:
    # 'LODV', count, rows of (base model, kind 1-3 = PS2 level, 4 = rigid far variant, variant model, 0).
    from native_models import level_models, rigid
    variants=[]
    levels={}
    for base,level,blob in level_models(disc,tables,(capture/"leon-bind.bin").read_bytes(),lambda key,phase:assets.header(key,phase,fog=True)):
        variants.append((base,level,len(actor_models)));actor_models.append(blob);levels[base,level]=blob
    for base in range(1,6):
        src=levels.get((base,3))
        r=rigid(src) if src else None
        if r:variants.append((base,4,len(actor_models)));actor_models.append(r)
    for base in range(6,6+len(prop_ids)):
        r=rigid(actor_models[base]) if struct.unpack_from("<I",actor_models[base])[0]>1 else None
        if r:variants.append((base,4,len(actor_models)));actor_models.append(r)
    print("distance variants",len(variants),"catalogue",len(actor_models))
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
    def glow_header(data,offset):
        """eng-look: the frame-alpha glow of an effect that writes the frame's alpha (filter03 mask): a white texture
        whose alpha is the sprite texture's alpha shrunk to the middle 80% and blurred (sigma 4% of the size, the
        filter's quarter-size copy and feedback passes), drawn additive (source alpha, one) without fog."""
        key=struct.unpack_from("<2I",data,offset)
        if key==(0,0) or key not in assets.lookup:return 0xffffffff
        tag=key,"glow"
        if tag not in material_cache:
            off,size=assets.lookup[key];img=dctex.decode(assets.texpack[off:off+size])
            H,W=img.shape[:2];h,w=min(H,32),min(W,32)   # the glow is soft: 32 texels a side at most
            a=img[...,3].astype(np.float32).reshape(h,H//h,w,W//w).mean(axis=(1,3))
            ys=np.clip(((np.arange(h)+.5)/h-.5)/.8+.5,0,1-1e-6)*h;xs=np.clip(((np.arange(w)+.5)/w-.5)/.8+.5,0,1-1e-6)*w
            inner=(np.abs(np.arange(h)+.5-h/2)<=.4*h)[:,None]&(np.abs(np.arange(w)+.5-w/2)<=.4*w)[None,:]
            a=a[ys.astype(int)][:,xs.astype(int)]*inner
            for axis,n in ((0,h),(1,w)):
                sig=max(1.,.04*n);r=int(3*sig);k=np.exp(-.5*(np.arange(-r,r+1)/sig)**2);k/=k.sum()
                a=np.apply_along_axis(lambda v:np.convolve(v,k,mode="same"),axis,a)
            out=np.zeros((h,w,4),np.uint8);out[...,:3]=255;out[...,3]=np.clip(a,0,255).astype(np.uint8)
            pkg=dctex.encode_4444(out,b"glow")
            ck=(zlib.crc32(pkg),0x574f4c47)
            if ck not in assets.lookup:
                assets.lookup[ck]=(len(assets.texpack),len(pkg));assets.texpack+=pkg
            material_cache[tag]=assets.header(ck,4,blend=(4,1),fog=False)
        return material_cache[tag]
    first_pose={}
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
                tool=struct.unpack_from("<I",record,24)[0]
                glow=glow_header(record,128) if tool&0x8000 and not tool&0x200000 else 0xffffffff
                struct.pack_into("<2I",record,128,effect_header(record,128,pair),glow)   # eng-look: + the glow header
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
        g2=groups[2];recs=[struct.unpack_from("<4I12f",g2,i) for i in range(0,len(g2),64)]   # eng-look: first pose per prop
        for i,r in enumerate(recs):
            if r[3]==0 and r[0]==2 and r[2] not in first_pose:
                j=i+1
                while j<len(recs) and recs[j][3]:j+=1
                first_pose[r[2]]=[x[4:] for x in recs[i:j]]
        if len(groups[1])!=104 or not groups[2] or not groups[6] or not groups[8]:
            raise ValueError(f"missing logic output in {path}: {[(k,len(v)) for k,v in groups.items()]}")
        frames.append(pack("10I",tick,*(table.add(changes[i].encode(groups[i+1])) for i,table in enumerate(samples))))
    # eng-look: far props as flat cards (native_cards.py)
    from native_cards import bake as bake_card
    tex_cache={}
    def header_texture(hdr):
        if hdr not in tex_cache:
            tid=struct.unpack_from("<I",assets.headers.rows[hdr])[0];tex_cache[hdr]=dctex.decode(assets.textures.rows[tid])
        return tex_cache[hdr]
    cards=[]
    for model in range(6,6+len(prop_ids)):
        if model not in first_pose:continue
        got=bake_card(actor_models[model],first_pose[model],header_texture)
        if not got:continue
        atlas,centre,rw,hh=got
        pkg=dctex.encode_4444(atlas,b"card");ck=(zlib.crc32(pkg),0x44524143)
        if ck not in assets.lookup:assets.lookup[ck]=(len(assets.texpack),len(pkg));assets.texpack+=pkg
        cards.append(pack("2H5f",model,assets.header(ck,2,fog=True),*centre,rw,hh))
    print("prop cards",len(cards))
    sections = [block(t.rows) for t in [assets.textures,assets.headers]]
    sections += [world,block(frames),*(block(t.rows) for t in samples)]
    sections.append(block(actor_models))
    sections.append(pack("2f",assets.top,assets.bottom)+pack("4sI",b"LODV",len(variants))+b"".join(pack("4H",b,k,v,0) for b,k,v in variants)
                    +pack("4sI",b"CARD",len(cards))+b"".join(cards))
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
