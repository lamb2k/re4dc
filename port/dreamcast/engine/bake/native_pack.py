"""Bake static materials and unchanged logic values. The display program selects all draws."""
import argparse
import collections
import struct
import zlib
from pathlib import Path
from logic_delta import Changes
from native_world import whole_world
from pack_scene import Baker, Table, block, pack

def build(disc, capture, room):
    assets = Baker(disc, capture, room)
    def world_material(key, phase, cull):
        return assets.header(key, (0,2,3)[phase], cull, world=True, fog=True)
    world = whole_world(disc / f"native/r{room:x}", world_material)
    samples = [Table() for _ in range(8)]
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
            groups[kind].extend(b[offset:offset+size])
            offset += size
        if len(groups[1])!=104 or not groups[2] or not groups[6] or not groups[8]:
            raise ValueError(f"missing logic output in {path}: {[(k,len(v)) for k,v in groups.items()]}")
        frames.append(pack("9I",tick,*(table.add(changes[i].encode(groups[i+1])) for i,table in enumerate(samples))))
    sections = [block(t.rows) for t in [assets.textures,assets.headers]]
    sections += [world,block(frames),*(block(t.rows) for t in samples)]
    data = block(sections)
    print("room",hex(room),"resident pack",len(data)+20,"sections",list(map(len,sections)))
    return pack("4s4I",b"NAT3",3,room,len(data),zlib.crc32(data))+data

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("disc",type=Path)
    p.add_argument("capture",type=Path)
    p.add_argument("room",type=lambda s:int(s,16))
    p.add_argument("out",type=Path)
    a=p.parse_args()
    a.out.write_bytes(build(a.disc,a.capture,a.room))
