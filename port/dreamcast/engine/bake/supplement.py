"""Match a second capture with environment/light records to the original inputs."""
import struct

def records(blob):
    offset = 28
    while offset < len(blob):
        kind, size = struct.unpack_from("<2I", blob, offset)
        value = blob[offset+8:offset+8+size]
        if len(value) != size:
            raise ValueError("short capture record")
        yield kind, value
        offset += 8 + size

def identity(blob):
    # Addresses and alignment padding differ in a relinked capture image.
    # Resolve its per-picture palette and light back-references before comparing.
    refs = {}
    offset = 8
    world_picks = False
    for kind, value in records(blob):
        refs[offset] = value
        offset += 8 + len(value)
        if kind in (12, 13):
            value = refs[struct.unpack("<I",value)[0]]
            kind -= 8
        if kind == 2:
            if world_picks:
                value = b"".join((value[i:i+3] if value[i+2]==255 else value[i:i+6]) for i in range(0,len(value),8))
            world_picks = not world_picks
        elif kind == 3:
            value = value[24:84] + value[92:]
        elif kind in (14,15,16,17):
            continue
        yield kind, value

def matched_environment(original, extra):
    if list(identity(original)) != list(identity(extra)):
        raise ValueError("supplement draw inputs differ from original picture")
    rows = list(records(extra))
    folds = [v for k,v in rows if k == 14]
    env, = [v for k,v in rows if k == 16]
    if len(folds) != sum(k == 3 for k,_ in rows) or len(env)!=528:
        raise ValueError("incomplete part lights or environment")
    materials=[v for k,v in rows if k==17]
    if materials and len(materials)!=len(folds):raise ValueError("incomplete actor materials")
    return iter(folds),iter(materials) if materials else None, env, b"".join(v for k,v in rows if k == 15)
