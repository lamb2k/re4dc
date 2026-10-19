#!/usr/bin/env python3
"""Lossless ordered GX strips for an optional character host fixture only.

Native source .gx files stay unchanged for the existing independent fit/verify
path. This reduces the unchanged converter's per-strip scratch demand without
increasing its workspace or altering any triangle, corner attribute or order.
"""
import hashlib
from pathlib import Path
import struct
import sys


def ordered_gx(data, counts=None):
    if len(data) < 3 or data[0] != 0x90:
        raise ValueError('one original GX triangle list required')
    count = struct.unpack_from('>H', data, 1)[0]
    end = 3 + count * 6
    if count < 3 or count % 3 or end > len(data) or any(data[end:]):
        raise ValueError('invalid GX triangle list or nonzero trailing data')
    corners = [struct.unpack_from('>3H', data, 3 + 6*k) for k in range(count)]
    if counts is not None and (len(counts) != 3 or any(n <= 0 for n in counts) or
                               any(c[k] >= counts[k] for c in corners for k in range(3))):
        raise ValueError('GX corner index outside its original position/normal/UV arrays')
    triangles = [corners[k:k+3] for k in range(0, count, 3)]
    strips, current = [], []
    for triangle in triangles:
        following = None
        if current and len(current) < 64:
            edge = (current[-1], current[-2]) if len(current) & 1 else (current[-2], current[-1])
            for k in range(3):
                if (triangle[k], triangle[(k+1) % 3]) == edge:
                    following = triangle[(k+2) % 3]
                    break
        if following is None:
            if current:
                strips.append(current)
            current = list(triangle)
        else:
            current.append(following)
    strips.append(current)
    # Compare the complete sequence, not merely the triangle multiset.
    canonical = lambda t: min(tuple(t[k:] + t[:k]) for k in range(3))
    decoded = []
    for strip in strips:
        for k in range(len(strip)-2):
            decoded.append([strip[k+1], strip[k], strip[k+2]] if k & 1 else strip[k:k+3])
    if [canonical(t) for t in decoded] != [canonical(t) for t in triangles]:
        raise ValueError('ordered GX strip conversion changed winding, attributes or order')
    output = b''.join(struct.pack('>BH', 0x98, len(strip)) + b''.join(struct.pack('>3H', *c) for c in strip)
                      for strip in strips)
    output += bytes((-len(output)) % 32)
    return output, dict(triangles=len(triangles), strips=len(strips), max_strip_corners=max(map(len, strips)),
                       exact_oriented_corner_sequence=True, original_bytes=len(data), ordered_bytes=len(output),
                       original_sha256=hashlib.sha256(data).hexdigest(), ordered_sha256=hashlib.sha256(output).hexdigest())


_ORIGINAL_REFERENCE = """static std::multiset<Triangle> from_gx(const castmodel::Chunk& c) {
    assert(c.stream[0]==0x90 && be16(c.stream+1)==c.triangles*3);
    std::multiset<Triangle> out;
    for(unsigned i=0;i<c.triangles;++i){Triangle t;for(unsigned j=0;j<3;++j)for(unsigned k=0;k<3;++k)t[j][k]=be16(c.stream+3+(i*3+j)*6+k*2);out.insert(canonical(t));}return out;
}
"""
_ORDERED_REFERENCE = """static std::multiset<Triangle> from_gx(const castmodel::Chunk& c) {
    std::multiset<Triangle> out;
    unsigned at=0;
    while(at<c.stream_bytes){
        const unsigned op=c.stream[at++];if(!op)continue;
        assert(op==0x90 || op==0x98);assert(at+2<=c.stream_bytes);
        const unsigned n=be16(c.stream+at);at+=2;assert(n>=3 && at+6*n<=c.stream_bytes);
        std::vector<Corner> run(n);
        for(unsigned i=0;i<n;++i)for(unsigned k=0;k<3;++k)run[i][k]=be16(c.stream+at+6*i+2*k);
        at+=6*n;
        if(op==0x90){assert(n%3==0);for(unsigned i=0;i<n;i+=3)out.insert(canonical(Triangle{run[i],run[i+1],run[i+2]}));}
        else for(unsigned i=0;i+2<n;++i){Triangle t{run[i],run[i+1],run[i+2]};if(i&1)std::swap(t[0],t[1]);out.insert(canonical(t));}
    }
    assert(out.size()==c.triangles);return out;
}
"""


def host_test(source):
    """Extend only the pinned independent reference reader; keep all gates."""
    if source.count(_ORIGINAL_REFERENCE) != 1:
        raise ValueError('original host reference reader changed; review before adapting it')
    return source.replace(_ORIGINAL_REFERENCE, _ORDERED_REFERENCE, 1)


if __name__ == '__main__':
    if len(sys.argv) != 4 or sys.argv[1] != 'host-test':
        raise SystemExit('usage: ps2_cast_host_strips.py host-test ORIGINAL.cpp OUT.cpp')
    Path(sys.argv[3]).write_text(host_test(Path(sys.argv[2]).read_text()), encoding='utf-8')
