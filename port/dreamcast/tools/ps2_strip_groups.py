#!/usr/bin/env python3
"""ps2_strip_groups.py IN.re4mesh IN.r4pw OUT.re4mesh OUT.r4sg [--groups 4] [--report OUT.json]

Offline strip groups for a PS2 world package (R4IM v3) + its R4PW sidecar (lane objs 2026-10-15, r101 release gate;
game knob PS2_STRIP_GROUPS, native_static.cpp). Measured need: on bench-r101 47% of the strips the runtime walks are
culled after their vertices were transformed (stripcull.py: 46% of transformed vertices feed only culled strips).

Per meshlet (every level):
  - strips of opaque / punch-through parts (R4PW pass 0 / 1) are split into up to G spatial groups (kd: halve the
    largest group at the median strip centroid of its widest model-space axis); translucent parts (pass 2) keep their
    order (draw order matters there) and are cut into up to G runs of consecutive strips;
  - the meshlet's corners are renumbered by first use in group order (non-indexed meshlets: the vertex records are
    permuted in place; indexed (pool) meshlets: their offset table is permuted), so each group's corners form a short
    index range and a group that is off screen leaves its range untransformed;
  - one 16-byte record per group in OUT.r4sg: grid box lo[3] hi[3] (u16), strip byte end (u16, relative to the
    meshlet's strip start; a group starts where the previous ended), first / last corner (u8, inclusive).
The meshlet set, vertex records, strips (as triangles), bounds, clusters and levels are unchanged: OUT.re4mesh has the
same size, header crc recomputed (zlib.crc32 of bytes 80..). Indexed (LOD) meshlets that read a renumbered non-indexed
meshlet's records through their pool offsets are re-pointed to the records' new places.
OUT.r4sg: header 'R4SG', version 1, meshlet_count, groups, mesh crc (OUT), mesh bytes, sidecar crc (R4PW), crc32 of the
records; then meshlet_count x groups x 16 bytes."""
import argparse, json, struct, sys, zlib


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mesh'); ap.add_argument('sidecar'); ap.add_argument('out_mesh'); ap.add_argument('out_groups')
    ap.add_argument('--groups', type=int, default=4); ap.add_argument('--report')
    ap.add_argument('--preserve-order', action='store_true',
                    help='write metadata only, preserve all mesh bytes; OUT.re4mesh must be -')
    a = ap.parse_args()
    if a.preserve_order:
        from d367.visibility23.metadata import write_metadata
        write_metadata(a)
        return
    G = a.groups
    assert 1 <= G <= 8
    m = bytearray(open(a.mesh, 'rb').read())
    side = open(a.sidecar, 'rb').read()
    h = struct.unpack_from('<4s15I4I', m, 0)
    magic, version, nbytes, crc, nmesh, npart, nlet, nvert, nstrip, npal, o_mesh, o_part, o_let, o_vert, o_strip, o_pal = h[:16]
    assert magic == b'R4IM' and version == 3 and nbytes == len(m), (magic, version)
    ncl, nlv, o_plod, o_cl, o_lv = struct.unpack_from('<5I', m, 80)
    hp = struct.unpack_from('<4s7I', side, 0)
    assert hp[0] == b'R4PW'
    nplace, nparts_side = hp[2], hp[3]
    side_crc = struct.unpack_from('<I', side, 20)[0]
    assert nparts_side == npart
    part_pass = [side[32 + 16 * i + 12] for i in range(npart)]
    part_step = [(1.0, 1.0, 1.0)] * npart  # part -> its mesh's grid step
    for mi in range(nmesh):
        r = struct.unpack_from('<HBBHHIII12f', m, o_mesh + 68 * mi)
        for pi in range(r[6], r[6] + r[7]):
            part_step[pi] = tuple(abs(x) for x in r[11:14])
    # meshlet -> part (level 0 ranges and the LOD clusters' levels)
    let_part = [None] * nlet
    for pi in range(npart):
        first_let, let_count = struct.unpack_from('<II', m, o_part + 36 * pi + 12)
        for li in range(first_let, first_let + let_count):
            let_part[li] = pi
        fc, cc = struct.unpack_from('<II', m, o_plod + 8 * pi)
        for c in range(fc, fc + cc):
            fl, lc = struct.unpack_from('<II', m, o_cl + 20 * c + 12)
            for lv in range(fl, fl + lc):
                fm, mc = struct.unpack_from('<II', m, o_lv + 12 * lv)
                for li in range(fm, fm + mc):
                    let_part[li] = pi
    lets = []
    for li in range(nlet):
        r = struct.unpack_from('<IIIHH6H', m, o_let + 28 * li)
        lets.append(dict(fv=r[0], fs=r[1], sb=r[2], vc=r[3], sc=r[4]))
    # Non-indexed meshlets own their vertex records (no two share one: asserted); indexed LOD meshlets may read them
    # through their pool offsets, so a permuted record's readers are re-pointed (vmap: old absolute -> new absolute).
    owner = {}
    for li, L in enumerate(lets):
        if not L['sc'] & 0x8000:
            for v in range(L['fv'], L['fv'] + L['vc']):
                assert v not in owner, 'two non-indexed meshlets share vertex %d' % v
                owner[v] = li
    vmap = {}
    recs = {}
    stats = dict(meshlets=nlet, groups=G, sorted=0, renumbered=0, repointed_offsets=0, group_records=0,
                 nonempty_groups=0, range_sum=0, vertex_sum=0)

    def process(li, L):
        indexed = bool(L['sc'] & 0x8000)
        fs = o_strip + L['fs']
        vc = L['vc']
        if indexed:
            offs = list(struct.unpack_from('<%dH' % vc, m, fs))
            for k in range(vc):  # re-point offsets into permuted non-indexed records
                v = L['fv'] + offs[k]
                if v in vmap and vmap[v] != v:
                    offs[k] = vmap[v] - L['fv']; stats['repointed_offsets'] += 1
            s0 = fs + 2 * vc
        else:
            s0 = fs
        end = s0 + L['sb']
        strips = []
        s = s0
        while s < end:
            n = m[s]; strips.append(list(m[s + 1:s + 1 + n])); s += 1 + n
        assert s == end

        def grid(k):  # corner k's grid position
            base = L['fv'] + (offs[k] if indexed else k)
            return struct.unpack_from('<3H', m, o_vert + 12 * base)
        pos = [grid(k) for k in range(vc)]
        pi = let_part[li]
        ng = min(G, len(strips))
        if pi is not None and part_pass[pi] in (0, 1) and len(strips) > 1:
            # kd split: halve the strip set at the median centroid of its widest model-space axis until ng groups
            st_ = part_step[pi]
            cen = {id(t): [sum(pos[k][a] for k in t) / len(t) * st_[a] for a in range(3)] for t in strips}
            groups = [strips]
            while len(groups) < ng:
                i = max(range(len(groups)), key=lambda j: len(groups[j]))
                g = groups[i]
                if len(g) < 2:
                    break
                ax = max(range(3), key=lambda a: max(cen[id(t)][a] for t in g) - min(cen[id(t)][a] for t in g))
                g = sorted(g, key=lambda t: cen[id(t)][ax])
                h = len(g) // 2
                groups[i:i + 1] = [g[:h], g[h:]]
            stats['sorted'] += 1
        else:
            per = -(-len(strips) // ng)
            groups = [strips[i:i + per] for i in range(0, len(strips), per)]
        new_of = {}
        for g in groups:
            for st in g:
                for k in st:
                    if k not in new_of:
                        new_of[k] = len(new_of)
        for k in range(vc):  # corners no strip uses: last
            if k not in new_of:
                new_of[k] = len(new_of)
        old_of = [0] * vc
        for k, nk in new_of.items():
            old_of[nk] = k
        if indexed:
            struct.pack_into('<%dH' % vc, m, fs, *[offs[old_of[nk]] for nk in range(vc)])
        else:
            rec = [bytes(m[o_vert + 12 * (L['fv'] + k):o_vert + 12 * (L['fv'] + k) + 12]) for k in range(vc)]
            for nk in range(vc):
                m[o_vert + 12 * (L['fv'] + nk):o_vert + 12 * (L['fv'] + nk) + 12] = rec[old_of[nk]]
            for k in range(vc):
                vmap[L['fv'] + k] = L['fv'] + new_of[k]
        groups = [[[new_of[k] for k in st] for st in g] for g in groups]
        pos = [pos[old_of[nk]] for nk in range(vc)]
        stats['renumbered'] += 1
        out = bytearray(); recs_l = bytearray()
        for g in groups:
            for st in g:
                out.append(len(st)); out.extend(st)
            ks = [k for st in g for k in st]
            lo = [min(pos[k][a] for k in ks) for a in range(3)]; hi = [max(pos[k][a] for k in ks) for a in range(3)]
            recs_l += struct.pack('<6HHBB', *lo, *hi, len(out), min(ks), max(ks))
            stats['nonempty_groups'] += 1; stats['range_sum'] += max(ks) - min(ks) + 1
        assert len(out) == L['sb']
        m[s0:end] = out
        for _ in range(G - len(groups)):  # empty groups: end = previous end, range 1..0
            recs_l += struct.pack('<6HHBB', 0, 0, 0, 0, 0, 0, len(out), 1, 0)
        recs[li] = bytes(recs_l)
        stats['vertex_sum'] += vc
    for li, L in enumerate(lets):
        if not L['sc'] & 0x8000:
            process(li, L)
    for li, L in enumerate(lets):
        if L['sc'] & 0x8000:
            process(li, L)
    recs = b''.join(recs[li] for li in range(nlet))
    stats['group_records'] = len(recs) // 16
    struct.pack_into('<I', m, 12, zlib.crc32(bytes(m[80:])) & 0xffffffff)
    new_crc = struct.unpack_from('<I', m, 12)[0]
    open(a.out_mesh, 'wb').write(m)
    head = struct.pack('<4s7I', b'R4SG', 1, nlet, G, new_crc, len(m), side_crc, zlib.crc32(bytes(recs)) & 0xffffffff)
    open(a.out_groups, 'wb').write(head + recs)
    stats.update(mesh_crc_in='%08x' % crc, mesh_crc_out='%08x' % new_crc, sidecar_crc='%08x' % side_crc,
                 r4sg_bytes=len(head) + len(recs))
    print(json.dumps(stats))
    if a.report:
        json.dump(stats, open(a.report, 'w'), indent=1)


if __name__ == '__main__':
    main()
