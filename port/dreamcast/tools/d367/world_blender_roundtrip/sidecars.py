"""Explicit companion registry. No certificate is inferred from a matching CRC.

Supported dependency payloads are reserialized only after identity of both world
files is proved. Existing labels/proofs are inherited, never newly certified.
"""
from pathlib import Path
import json
import struct

from package import PW_HEAD, crc, require, sha
import provenance

REGISTRY = {
    'ps2-world.ids': ('R4ID v1', 'supported: inherited source IDs, current policy CRC'),
    'ps2-world.r4tc': ('R4TC v1/classifier1', 'supported: inherited classes, both CRCs'),
    'ps2-world.r4sg': ('R4SG v1', 'supported: regenerate existing consecutive strip-group bounds'),
    'ps2-world.pvs': ('R4PV v1', 'supported: identity-only inherited proof; no PVS23 certificate issued'),
    'interior.cell': ('PCL1', 'supported: identity-only inherited portal proof/constants'),
    'ps2-world.occl': ('R4OC v1', 'supported: identity-only inherited occluder proof'),
    'room.r4rc': ('R4RC v1', 'supported: explicit SRCB/GRID/VIS/OCCL/SCNK/SCDD/SCCN/SCPS registry'),
    'far-shell.fsh': ('FSH1 v1/v2', 'supported: independent far-shell representation, identity-only'),
    'ps2-world.re4mesh.dd3': ('SDO3', 'unsupported: alternate lineage/dedup representation'),
    'ps2-world.re4mesh.sds1': ('SDS1', 'unsupported: Build12 direct-strip representation'),
    'ps2-world.json': ('ps2_world_r4im report', 'supported: actual output hashes verified; source provenance inherited'),
}
REQUIRED = {'ps2-world.re4mesh', 'ps2-world.r4pw'}


def inventory(folder):
    folder = Path(folder)
    require(folder.is_dir(), 'bundle directory required')
    files = {}
    for p in folder.iterdir():
        require(p.is_file() and not p.is_symlink(), 'non-file/symlink bundle member '+p.name)
        require(p.name in REQUIRED or p.name in REGISTRY, 'unknown companion '+p.name)
        if p.name in REGISTRY:
            require(REGISTRY[p.name][1].startswith('supported:'),
                    p.name+': '+REGISTRY[p.name][1])
        files[p.name] = p.read_bytes()
    require(REQUIRED <= files.keys(), 'bundle needs ps2-world.re4mesh and ps2-world.r4pw')
    return files


def regenerate(name, data, doc, mesh, side, files=None):
    """Validate actual old bindings and rebuild fields using unchanged records."""
    mh = struct.unpack_from('<4s19I', mesh)
    ph = list(PW_HEAD.unpack_from(side))
    # Bind to the runtime's policy source CRC (certified rekeyed worlds keep their original policy CRC).
    ph[5] = provenance.policy_crc(mesh, side)[0]
    if name == 'ps2-world.ids':
        require(len(data) >= 16 and len(data) % 32 == 0, 'R4ID size')
        magic, version, count, bound = struct.unpack_from('<4s3I', data)
        require((magic,version,bound) == (b'R4ID',1,ph[5]), 'R4ID stale binding/version')
        # The existing runtime requires count==nplacements and a safe source field.
        require(count == len(doc['placements']) and all(p[1] < count for p in doc['placements']), 'R4ID count/source identity')
        require(len(data) == (16+count+31)//32*32 and not any(data[16+count:]), 'R4ID padding')
        out = struct.pack('<4s3I', b'R4ID',1,count,ph[5])+bytes(data[16:16+count])
        return out+bytes(-len(out)%32)
    if name == 'ps2-world.r4tc':
        require(len(data) >= 24, 'R4TC size')
        magic, version, classifier, count, bound, body_crc = struct.unpack_from('<4s5I',data)
        require((magic,version,classifier,count,bound) == (b'R4TC',1,1,ph[3],ph[5]), 'R4TC stale binding/version')
        require(len(data) == 24+(count+3)//4*4, 'R4TC extent')
        classes = data[24:24+count]
        require(crc(classes) == body_crc and all(v <= 10 for v in classes) and not any(data[24+count:]), 'R4TC classes/CRC/padding')
        return struct.pack('<4s5I',b'R4TC',1,1,count,ph[5],crc(classes))+classes+bytes(-count%4)
    if name == 'ps2-world.r4sg':
        require(len(data) >= 32, 'R4SG size')
        h = struct.unpack_from('<4s7I',data)
        require(h[:3] == (b'R4SG',1,mh[6]) and 1 <= h[3] <= 8 and
                h[4:7] == (mh[3],len(mesh),ph[5]), 'R4SG stale binding/version')
        require(len(data) == 32+16*h[2]*h[3] and len(data) <= 262144 and crc(data[32:]) == h[7], 'R4SG size/CRC')
        rebuilt = bytearray()
        for ji, (m,cmd) in enumerate(zip(doc['meshlets'],doc['commands'])):
            cursor, consumed = 0, 0
            for gi in range(h[3]):
                r = struct.unpack_from('<6HHBB',data,32+16*(ji*h[3]+gi))
                end, lo, hi = r[6:]
                require(cursor <= end <= m[2], 'R4SG interval')
                keys = []
                while cursor < end:
                    require(consumed < len(cmd['strips']), 'R4SG past strips')
                    s = cmd['strips'][consumed]; consumed += 1
                    cursor += 1+len(s); keys += s
                require(cursor == end, 'R4SG splits a strip')
                if keys:
                    points = [doc['vertices'][m[0]+cmd['pool'][k]][:3] for k in keys]
                    actual = (*[min(p[a] for p in points) for a in range(3)],
                              *[max(p[a] for p in points) for a in range(3)],end,min(keys),max(keys))
                else:
                    actual = (0,0,0,0,0,0,end,1,0)
                require(tuple(r) == actual, 'R4SG bounds/range do not match geometry')
                rebuilt.extend(struct.pack('<6HHBB',*actual))
            require(cursor == m[2] and consumed == len(cmd['strips']), 'R4SG missing strips')
        return struct.pack('<4s7I',b'R4SG',1,h[2],h[3],mh[3],len(mesh),ph[5],crc(rebuilt))+rebuilt
    import proof_identity as proof
    if name == 'ps2-world.pvs':return proof.pvs(data,doc,mesh,side)
    if name == 'interior.cell':return proof.pcl(data,doc,mesh,side)
    if name == 'ps2-world.occl':return proof.occluders(data,doc,mesh,side)
    if name == 'room.r4rc':return proof.room(data,doc,mesh,side,files or {})
    if name == 'far-shell.fsh':return proof.far_shell(data)
    if name == 'ps2-world.json':
        report=json.loads(data)
        require(set(report)=={'source','source_sha256','inc_sha256','args','meshes','placements',
            'source_triangles','re4mesh_bytes','re4mesh_sha256','r4pw_bytes','r4pw_sha256',
            'level0_triangles','summary'},'unknown builder report schema')
        require(report['meshes']==len(doc['meshes']) and report['placements']==len(doc['placements']) and
            report['re4mesh_bytes']==len(mesh) and report['re4mesh_sha256']==sha(mesh) and
            report['r4pw_bytes']==len(side) and report['r4pw_sha256']==sha(side),'stale builder report')
        require(all(isinstance(report[k],str) and len(report[k])==64 and
            all(c in '0123456789abcdef' for c in report[k]) for k in ('source_sha256','inc_sha256')),
            'builder source hash syntax (external evidence inherited)')
        result=json.dumps(report,indent=1,allow_nan=False).encode()
        require(result==data,'noncanonical builder report')
        return result
    raise ValueError('no supported adapter for '+name)


def rebuild(files, doc, mesh, side):
    require(mesh == files['ps2-world.re4mesh'] and side == files['ps2-world.r4pw'],
            'identity companion rebuild requires unchanged geometry AND policy')
    out = {'ps2-world.re4mesh':mesh,'ps2-world.r4pw':side}
    for name in sorted(files.keys()-REQUIRED):
        out[name] = regenerate(name,files[name],doc,mesh,side,files)
        require(out[name] == files[name], name+' regenerated bytes differ')
    return out


def hashes(files):
    return {name:sha(blob) for name,blob in sorted(files.items())}
