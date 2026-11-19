"""Check the M1 capture ABI and report the first rejected picture in a scene."""
import argparse
from collections import Counter
import struct
from pathlib import Path

def check(path, expected_room):
    records = sorted(path.glob("picture-*.bin"))
    last_frame = 0
    counts = Counter()
    worst_bytes = 0
    for expected, filename in enumerate(records,1):
        buf = filename.read_bytes()
        seq,magic,room,pic,frame,length,overflow = struct.unpack_from("<7I",buf)
        if (seq,magic,room,pic,length,overflow) != (2*expected,0x31434d46,expected_room,expected,len(buf)-28,0):
            raise ValueError(f"{filename.name} invalid frame header")
        if frame <= last_frame: raise ValueError("nonmonotonic game frame")
        last_frame = frame
        off = 28
        fields = Counter()
        prior = {}
        pending = None
        while off < len(buf):
            typ,size = struct.unpack_from("<II",buf,off)
            off += 8
            data = buf[off:off+size]
            if len(data) != size: raise ValueError("truncated record")
            fields[typ] += 1
            if pending is not None:
                if typ != 2 or size != pending * 8: raise ValueError("incomplete meshlet picks")
                pending = None
            elif typ == 1:
                if size != 100: raise ValueError("camera shape")
            elif typ == 2:
                if size != 60: raise ValueError("world part shape")
                pending = struct.unpack_from("<I",data,8)[0]
            elif typ in (4,5):
                prior[off-28] = typ
            elif typ in (12,13):
                if size != 4 or prior.get(struct.unpack("<I",data)[0]) != typ-8: raise ValueError("invalid back-reference")
            elif typ not in (3,6,7): raise ValueError(f"unknown record {typ}")
            off += size
        if pending is not None or fields[1] != 1 or not fields[2] or not fields[3]:
            raise ValueError(f"{filename.name} missing required scene records {dict(fields)}")
        counts.update(fields)
        worst_bytes=max(worst_bytes,length)
    print(f"{path.name} contiguous pictures {len(records)}, largest {worst_bytes} bytes, records {dict(counts)}")
    if len(records)!=300: raise ValueError("expected 300 pictures")
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("path",type=Path)
    p.add_argument("room",type=lambda x:int(x,16))
    a=p.parse_args()
    check(a.path,a.room)
