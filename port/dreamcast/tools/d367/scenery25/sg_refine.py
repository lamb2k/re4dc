#!/usr/bin/env python3
"""sg_refine.py MESH R4PW IN.r4sg OUT.r4sg [--groups 8] [--report OUT.json]

Finer PS2_STRIP_GROUPS records for a world package without touching the package (lane scenery-rewrite25, step 2 option
A, 2026-10-26). The shipped R4SG (tools/ps2_strip_groups.py) cut each meshlet's strips into G spatial groups and
renumbered the corners by first use in group order, so inside a group consecutive strips are spatially close (the kd
leaf is sorted on its last split axis) and their corners form short index ranges. This splits every group of two or
more strips into consecutive runs (by strip count) until the meshlet has up to --groups records, keeping the mesh bytes,
the strip order and every corner number: the package crc, the R4ID / SCDD / SCPS bindings and the draw order are
unchanged. Each record is recomputed from the corners its strips reference (grid box lo/hi, strip byte end, first /
last corner), the same 16-byte layout; empty records pad the meshlet as ps2_strip_groups.py writes them.

Runtime cost of the result: heap 4 grows by 16 * meshlets * (groups - G) bytes at room load (the r4sg block); the
caller (sg8_rooms.sh) decides per room whether the heap allows it. Measured need: hwmodel census of the
SCENERY_STREAM check build, 48% of the corners transformed at the r101 crossing feed only strips culled after the
transform (15% at the bell)."""
import argparse, json, struct, sys, zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from visibility23.metadata import headers, meshlets, require, crc  # noqa: E402


def refine(mesh, side, sg, groups):
    h, p = headers(mesh, side)
    w = struct.unpack_from('<4s7I', sg)
    require(w[0] == b'R4SG' and w[1] == 1 and w[2] == h[6], 'R4SG identity')
    G = w[3]
    require(1 <= G <= groups <= 8, 'groups: input %d, output %d (1..8)' % (G, groups))
    # w[6] is the runtime's policy source crc (rect21 provenance: an older R4PW lineage for certified rooms), not
    # always this R4PW's crc: it is carried over unchanged.
    require(w[4] == h[3] and w[5] == len(mesh), 'R4SG binds another package')
    require(len(sg) == 32 + 16 * G * h[6] and crc(sg[32:]) == w[7], 'R4SG size / crc')
    out = bytearray()
    st = dict(meshlets=h[6], groups_in=G, groups_out=groups, split=0, range_in=0, range_out=0)
    for li, vc, pos, strips in meshlets(mesh, h):
        recs = [struct.unpack_from('<6HHBB', sg, 32 + 16 * (G * li + q)) for q in range(G)]
        # the input groups as strip runs (a record whose end does not move is empty)
        runs, prev, si, sizes = [], 0, 0, []
        offs = [0]
        for raw in strips:
            offs.append(offs[-1] + len(raw))
        for r in recs:
            end = r[6]
            if end == prev:
                continue
            j = si
            while j < len(strips) and offs[j + 1] <= end:
                j += 1
            require(offs[j] == end and j > si, 'group end off a strip boundary (meshlet %d)' % li)
            runs.append(strips[si:j]); si = j; prev = end
            st['range_in'] += r[8] - r[7] + 1
        require(si == len(strips), 'groups do not cover the strips (meshlet %d)' % li)
        # split the run with the most strips until 'groups' runs (or every run is one strip)
        while len(runs) < groups:
            i = max(range(len(runs)), key=lambda k: len(runs[k]))
            if len(runs[i]) < 2:
                break
            h2 = len(runs[i]) // 2
            runs[i:i + 1] = [runs[i][:h2], runs[i][h2:]]
            st['split'] += 1
        end = 0
        for run in runs:
            end += sum(map(len, run))
            ks = [k for raw in run for k in raw[1:]]
            lo = [min(pos[k][a] for k in ks) for a in range(3)]
            hi = [max(pos[k][a] for k in ks) for a in range(3)]
            out += struct.pack('<6HHBB', *lo, *hi, end, min(ks), max(ks))
            st['range_out'] += max(ks) - min(ks) + 1
        for _ in range(groups - len(runs)):
            out += struct.pack('<6HHBB', 0, 0, 0, 0, 0, 0, end, 1, 0)
    res = struct.pack('<4s7I', b'R4SG', 1, h[6], groups, h[3], len(mesh), w[6], crc(out)) + out
    require(len(res) <= 262144, 'R4SG exceeds the runtime size limit')
    st.update(bytes_in=len(sg), bytes_out=len(res), heap_delta=((len(res) + 31) & ~31) - ((len(sg) + 31) & ~31))
    return bytes(res), st


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mesh'); ap.add_argument('sidecar'); ap.add_argument('sg_in'); ap.add_argument('sg_out')
    ap.add_argument('--groups', type=int, default=8); ap.add_argument('--report')
    a = ap.parse_args()
    res, st = refine(Path(a.mesh).read_bytes(), Path(a.sidecar).read_bytes(), Path(a.sg_in).read_bytes(), a.groups)
    Path(a.sg_out).write_bytes(res)
    if a.report:
        Path(a.report).write_text(json.dumps(st, indent=1) + '\n')
    print(json.dumps(st))


if __name__ == '__main__':
    main()
