#!/usr/bin/env python3
"""Byte-neutral SDO3 offline scenery point dedup prototype; not runtime-ready.

The 80-byte R4IM v3 header reserves word18 for the original body CRC and word19
for 'SDO3'. Plain meshlets encode repeat_count in strip_count bits7..14; bits0..6
remain the strip count and bit15 remains indexed. Repeats follow unique corners.
Their XYZ becomes (first index, 0x5344, 0x4f33); UV and colour remain unchanged.
Only exclusive plain vertex spans are encoded. No section/table/padding grows.
A matching runtime must reject the marker unless SCENERY_DEDUP=3, validate the
records, decode repeat XYZ on clip/fallback paths, and never transform metadata.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct
import zlib

MARKER = int.from_bytes(b'SDO3', 'little')
TAG_Y, TAG_Z = 0x5344, 0x4f33
INDEXED = 0x8000


class Package:
    def __init__(self, data, encoded=False):
        self.data = bytes(data)
        if len(data) < 112:
            raise ValueError('short R4IM')
        self.h = struct.unpack_from('<4s19I', data)
        h = self.h
        if h[0] != b'R4IM' or h[1] != 3 or h[2] != len(data) or h[16] != 2:
            raise ValueError('need prelit R4IM v3')
        if zlib.crc32(data[80:]) != h[3]:
            raise ValueError('body CRC')
        if h[19] != (MARKER if encoded else 0) or (not encoded and h[18]):
            raise ValueError('format marker')
        self.encoded = encoded
        self.lets = []
        for i in range(h[6]):
            p = h[12] + 28*i
            if p + 28 > len(data):
                raise ValueError('meshlet section')
            l = struct.unpack_from('<IIIHH6H', data, p)
            fv, fs, size, n, sc = l[:5]
            if not 1 <= n <= 256 or fv >= h[7]:
                raise ValueError('meshlet vertices')
            ix = bool(sc & INDEXED)
            table = 2*n if ix else 0
            if fs + table + size > h[8] or h[14] + fs + table + size > len(data):
                raise ValueError('meshlet strips')
            idx = struct.unpack_from('<%dH' % n, data, h[14]+fs) if ix else range(n)
            if max(idx) + fv >= h[7]:
                raise ValueError('pool index')
            strip_count = sc & (0x7f if encoded and not ix else 0x7fff)
            rep = (sc >> 7) & 255 if encoded and not ix else 0
            if rep >= n:
                raise ValueError('repeat count')
            s, end = h[14]+fs+table, h[14]+fs+table+size
            strips = []
            while s < end:
                count = data[s];s += 1
                if count < 3 or s+count > end:
                    raise ValueError('strip length')
                strip = list(data[s:s+count]);s += count
                if max(strip) >= n:
                    raise ValueError('strip index')
                strips.append(strip)
            if len(strips) != strip_count:
                raise ValueError('strip count')
            corners = [struct.unpack_from('<6H', data, h[13]+12*(fv+k)) for k in idx]
            if rep:
                u = n-rep
                for k in range(u, n):
                    q, y, z = corners[k][:3]
                    if q >= u or (y,z) != (TAG_Y,TAG_Z):
                        raise ValueError('repeat source/tag')
            self.lets.append(dict(offset=p, fv=fv, fs=fs, size=size, n=n, sc=sc,
                                  ix=ix, rep=rep, strips=strips, corners=corners,
                                  strip_begin=h[14]+fs+table, indices=list(idx)))
        # Reject aliases: repeat metadata must never be visible to another meshlet.
        counts = Counter(fv+l['fv'] for l in self.lets for fv in set(l['indices']))
        if encoded:
            for l in self.lets:
                if l['rep'] and any(counts[l['fv']+k] != 1 for k in l['indices']):
                    raise ValueError('encoded vertex alias')
        self.refs = counts

    def decoded(self, l):
        c = l['corners']
        u = l['n']-l['rep']
        return [v if k < u else c[v[0]][:3]+v[3:] for k,v in enumerate(c)]


def convert(mesh, sg=None):
    p = Package(mesh)
    m = bytearray(mesh)
    groups = 0
    g = bytearray(sg) if sg is not None else None
    if g is not None:
        w = struct.unpack_from('<4s7I',g)
        if (w[0],w[1],w[2],w[4],w[5]) != (b'R4SG',1,p.h[6],p.h[3],len(mesh)):
            raise ValueError('SG package identity')
        groups = w[3]
        if not 1 <= groups <= 8 or len(g) != 32+16*groups*p.h[6] or zlib.crc32(g[32:]) != w[7]:
            raise ValueError('SG section')
    # Match the no-allocation runtime's conservative, linear ownership proof.
    alias=set();covered=0;plain_end=0
    for pi in range(p.h[5]):
        part=struct.unpack_from('<IIBBBBII4f',p.data,p.h[11]+36*pi)
        first,count=part[6:8]
        if first!=covered:raise ValueError('part partition')
        covered+=count;lets=p.lets[first:covered]
        pool=[l['fv']+k for l in lets if l['ix'] for k in l['indices']]
        lo,hi=(min(pool),max(pool)+1) if pool else (0,0)
        for li,l in enumerate(lets,first):
            if not l['ix']:
                if l['fv']<plain_end:raise ValueError('plain vertex alias')
                plain_end=l['fv']+l['n']
                if pool and l['fv']<hi and l['fv']+l['n']>lo:alias.add(li)
    if covered!=p.h[6]:raise ValueError('part coverage')
    st = Counter(meshlets=p.h[6], corners=0, repeats=0, eligible_meshlets=0,
                 skipped_indexed=0, skipped_alias=0, skipped_strip_count=0)
    if any(not l['ix'] and l['sc'] > 127 for l in p.lets):
        raise ValueError('plain strip count exceeds SDO3 format')
    for li,l in enumerate(p.lets):
        n,c = l['n'],l['corners'];st['corners']+=n
        reason = 'indexed' if l['ix'] else 'alias' if li in alias else 'strip_count' if l['sc'] > 127 else None
        if reason:
            st['skipped_'+reason]+=1;continue
        seen = {};first = [seen.setdefault(v[:3],k) for k,v in enumerate(c)]
        uniques = [k for k,f in enumerate(first) if k==f]
        repeats = [k for k,f in enumerate(first) if k!=f]
        if not repeats:
            continue
        order = uniques+repeats;pos={old:new for new,old in enumerate(order)}
        for k,old in enumerate(order):
            v=c[old]
            if k >= len(uniques):
                v=(pos[first[old]],TAG_Y,TAG_Z)+v[3:]
            struct.pack_into('<6H',m,p.h[13]+12*(l['fv']+k),*v)
        struct.pack_into('<H',m,l['offset']+14,l['sc'] | len(repeats)<<7)
        s=l['strip_begin']
        for strip in l['strips']:
            s+=1;m[s:s+len(strip)]=bytes(pos[k] for k in strip);s+=len(strip)
        if g is not None:
            prev=0
            for j in range(groups):
                off=32+16*(li*groups+j);end=struct.unpack_from('<H',g,off+12)[0]
                if end < prev or end > l['size']:
                    raise ValueError('SG end')
                if end != prev:
                    used=[];s=l['strip_begin']+prev;stop=l['strip_begin']+end
                    while s < stop:
                        count=m[s];s+=1
                        for q in m[s:s+count]:
                            used.append(q if q < len(uniques) else m[p.h[13]+12*(l['fv']+q)])
                        s+=count
                    if s != stop or not used:
                        raise ValueError('SG strip boundary')
                    struct.pack_into('<H',g,off+14,min(used) | max(used)<<8)
                prev=end
            if prev != l['size']:
                raise ValueError('SG coverage')
        st['eligible_meshlets']+=1;st['repeats']+=len(repeats)
    struct.pack_into('<II',m,72,p.h[3],MARKER)
    struct.pack_into('<I',m,12,zlib.crc32(m[80:]))
    if g is not None:
        struct.pack_into('<I',g,16,struct.unpack_from('<I',m,12)[0])
        struct.pack_into('<I',g,28,zlib.crc32(g[32:]))
    validate_pair(mesh,bytes(m),None if g is None else bytes(g))
    st.update(mesh_bytes=len(m), sg_bytes=len(g) if g is not None else 0,
              package_delta_bytes=0, old_body_crc=p.h[3], new_body_crc=struct.unpack_from('<I',m,12)[0])
    return bytes(m),None if g is None else bytes(g),dict(st)


def validate_pair(before, after, groups=None):
    a,b=Package(before),Package(after,encoded=True)
    if len(before)!=len(after) or a.h[4:18]!=b.h[4:18] or a.h[3]!=b.h[18]:
        raise ValueError('package shape/provenance')
    for old,new in zip(a.lets,b.lets):
        decoded=b.decoded(new)
        left=[[old['corners'][k] for k in strip] for strip in old['strips']]
        right=[[decoded[k] for k in strip] for strip in new['strips']]
        if left != right:
            raise ValueError('rendered corners differ')
    if groups is not None:
        w=struct.unpack_from('<4s7I',groups)
        if w[4]!=b.h[3] or w[5]!=len(after) or zlib.crc32(groups[32:])!=w[7]:
            raise ValueError('SG output identity')
        for li,l in enumerate(b.lets):
            prev=0;u=l['n']-l['rep'];s=l['strip_begin']
            for j in range(w[3]):
                off=32+16*(li*w[3]+j);end,span=struct.unpack_from('<HH',groups,off+12)
                if end==prev:continue
                needed=[];cursor=s+prev
                while cursor<s+end:
                    count=after[cursor];cursor+=1
                    for k in after[cursor:cursor+count]:
                        needed.append(k if k<u else l['corners'][k][0])
                    cursor+=count
                if cursor!=s+end or any(not span&255 <= k <= span>>8 for k in needed):
                    raise ValueError('SG omits a needed first copy')
                prev=end


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('mesh',type=Path);ap.add_argument('--groups',type=Path)
    ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();mesh=a.mesh.read_bytes();sg=a.groups.read_bytes() if a.groups else None
    m,g,st=convert(mesh,sg);a.out.mkdir(parents=True,exist_ok=False)
    # Explicit alternate names: cannot replace a release package accidentally.
    files={'ps2-dd3.re4mesh':m}
    if g is not None:files['ps2-dd3.r4sg']=g
    for name,data in files.items():(a.out/name).write_bytes(data)
    st['source_mesh']=str(a.mesh);st['source_groups']=str(a.groups) if a.groups else None
    st['input_sha256']=hashlib.sha256(mesh).hexdigest()
    st['output_sha256']=hashlib.sha256(m).hexdigest()
    (a.out/'report.json').write_text(json.dumps(st,indent=2)+'\n')
    (a.out/'SHA256SUMS').write_text(''.join(hashlib.sha256(data).hexdigest()+'  '+name+'\n' for name,data in files.items()))
    print(json.dumps(st,indent=2))


if __name__=='__main__':main()