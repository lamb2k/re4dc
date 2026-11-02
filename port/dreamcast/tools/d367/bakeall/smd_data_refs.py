#!/usr/bin/env python3
"""smd_data_refs.py (lane bakeall, phase 2): per room, the SMD scroll ids (0..249) that a NON-room-code data path
can address, so bake_classify.py's 'addr-unref' rows can be proven bakeable (static analysis only).

Consumers (game source -> data):
  eff_parent   esp_sub.cpp EspSeqSet / esp_efm.cpp EfmSeqSet / t_esp/db_port.cpp espgen: SmdGetObjPtr(rec.Parent_no-1)
               for every EspGenWork record (include/esp.h, 0x12C bytes, Parent_no u8 @0x06) of every EspSeqData
               (u16 num @0, 0x30 head) in the est AND sst sections of an EFF file (version 0xB; header = 12 u32
               offsets, le_mirror.py fmt_eff layout). The info flag 0x1000 bypass is ignored (conservative).
  eff_scrmodel esp_efm.cpp:364 SmdGetGroupObjPtr(rec.Tex_id) when rec.Id == 0xFC (efm move kind 3).
               Sources: the room's own EFF members (PS2 rNNN.dat, little endian; GC StN/rNNN.das, big endian) and,
               as a GLOBAL set applied to every room, every EFF found anywhere else (PS2 AFS: core/pl/wep/enemy/
               event dats walked recursively, event.eff, id101.eff; GC: ss/*.dat, etc/Eng/*.eff).
  lit_parent   light.cpp calcParent/getNormal: ParentType 2 -> SmdGetGroupObjPtr(ParentNo & 0xFFFF). cLightWork
               (include/light.h, 0x12C bytes @ cut+0x104, ParentType u8 @0x1C, ParentNo u32 @0x20), cLit header
               u16 CutNum, u32 cut offsets @4, light count u32 @ cut+4. Room LIT members (PS2 + GC) per room; core LIT
               members (PS2 core.dat) global.
  ctrl14       ctrl14.cpp GetCtrlDragon(0/1/2): ids 0xA,0xB,0xD,0xE / 0xF,0x10,0x12,0x13 / 0x14,0x15,0x16,0x17, reached
               only from em10 set 0x27/0x28/0x29 (em10.cpp switch (em->set)): GC etc/*.esl entries (include/em_set.h
               EmListData) with id 0x10 and set 0x27..0x29 for the room, plus r222 (room code).
  em3e         em3e.cpp cEmMark types 0xA..0xF: ids 5,6,0x33..0x36: rooms whose ESL lists em 0x3E or whose room code
               includes em3e.h / cEmMark.
  objRobo      objRobo.cpp R0WalkBridge smdNo[]: 0x43,0x44,0x4F..0x52: rooms whose room code uses cObjRobo/objRobo.h
               (ObjMgr type 0x37 is created only from room code).
  sce_com      sce_com.cpp OpenBoxMain(id1,id2) / SceElevator(d->objId): every caller is room code (src/stN/*.cpp:
               constants or room-code tables), already covered by bake_classify code-const / code-var -> [].
Not consumers: t_light/t_scroll.cpp (debug scroll editor, walks every id), light.cpp setParent(cModel*) (pointer search,
not an id from data), block.cpp (per block, not per id), AEV/ITA (sce_at.cpp: no Smd call).
A consumer whose data cannot be decoded with confidence is "UNPROVEN: reason" and the room keeps every addr-unref row.
"""
import json, re, struct, sys
from pathlib import Path

REPO = Path('/root/work/lanes/bakeall')
sys.path.insert(0, str(REPO / 'port/dreamcast/tools'))
import ps2_room_extract as X            # noqa: E402  (PS2 ISO + AFS index)
import room_smd                          # noqa: E402  (GC .das decode / tagged entries)
from assetpipe.rooms import GcIso        # noqa: E402

GC_ISOS = ['/root/work/re4-dreamcast/orig/G4BE08/re4_debug_disc1.iso',      # stages 1, 2, 4, core, em, evd
           '/mnt/c/Game Dev/Emulators/Resident Evil 4 (USA) (Disc 2).iso']     # stage 3 rooms + their evd (retail)
CLASSIFY = Path('/root/probe/lanes/bakeall/classify/bake-classify.json')
OUT = Path('/root/probe/lanes/bakeall/t2/smd-data-refs.json')


class Bad(Exception):
    pass


# ---------------------------------------------------------------- EFF
def eff_ids(b, end):
    """(parent_ids, scrmodel_ids, nrecords) of one EFF block; raises Bad when the layout does not hold."""
    E = '<' if end == 'le' else '>'
    if len(b) == 0:
        return set(), set(), 0          # empty file (PS2 event.eff / id101.eff are 0 bytes)
    if len(b) < 48:
        raise Bad('short EFF')
    hdr = struct.unpack_from(E + '12I', b, 0)
    if hdr[0] != 0xB:
        raise Bad('EFF version %#x' % hdr[0])
    size = len(b)
    for v in hdr[1:]:
        if v > size:
            raise Bad('EFF offset past end')
    par, scr, nrec = set(), set(), 0
    _, _, o_est, o_sst, _, _, _, _, d_est, d_sst, _, _ = hdr
    for o_list, o_data in ((o_est, d_est), (o_sst, d_sst)):
        if not o_list:
            continue
        n = struct.unpack_from(E + 'I', b, o_list)[0]
        if n == 0:
            continue
        if n > 4096 or not o_data:
            raise Bad('EFF list count %d / no data table' % n)
        m = struct.unpack_from(E + 'I', b, o_data)[0]
        if m != n:
            raise Bad('EFF list/data counts differ %d/%d' % (n, m))
        blocks = [o_data + v for v in struct.unpack_from(E + '%dI' % n, b, o_data + 4)]
        later = [v for v in hdr[1:] if v > o_data]
        sec_end = min(later + [size])
        starts = sorted(set(blocks))
        for i, s in enumerate(starts):
            e = starts[i + 1] if i + 1 < len(starts) else sec_end
            if s < o_data + 4 + 4 * n or e > sec_end:
                raise Bad('EFF block overlaps table / section')
            num = struct.unpack_from(E + 'H', b, s)[0]
            if 48 + 300 * num > e - s:
                raise Bad('EFF sequence of %d records exceeds block (%d bytes)' % (num, e - s))
            for k in range(num):
                r = s + 48 + 300 * k
                rid, tex, pno = b[r + 1], b[r + 2], b[r + 6]
                nrec += 1
                if pno and pno - 1 < 250:
                    par.add(pno - 1)
                if rid == 0xFC and tex < 250:
                    scr.add(tex)
    return par, scr, nrec


# ---------------------------------------------------------------- LIT
def lit_ids(b, end):
    E = '<' if end == 'le' else '>'
    if len(b) < 8:
        raise Bad('short LIT')
    ncut = struct.unpack_from(E + 'H', b, 0)[0]
    if ncut == 0:
        return set(), 0
    if ncut > 256 or 4 + 4 * ncut > len(b):
        raise Bad('LIT cut count %d' % ncut)
    ids, nl = set(), 0
    for o in struct.unpack_from(E + '%dI' % ncut, b, 4):
        if not o:
            continue
        if o + 0x104 > len(b):
            raise Bad('LIT cut offset past end')
        cnt = struct.unpack_from(E + 'I', b, o + 4)[0]
        if cnt > 512 or o + 0x104 + 0x12C * cnt > len(b):
            raise Bad('LIT cut light count %d does not fit' % cnt)
        for j in range(cnt):
            w = o + 0x104 + 0x12C * j
            ptype = b[w + 0x1C]
            pno = struct.unpack_from(E + 'I', b, w + 0x20)[0]
            # calcParent / getNormal switch on ParentType: only 2 reaches SmdGetGroupObjPtr; other values
            # (core LIT cut 45 carries 63) never touch the scroll table
            nl += 1
            if ptype == 2:
                ids.add(pno & 0xFFFF)
    return ids, nl


# ---------------------------------------------------------------- containers
def ps2_dat(d):
    if len(d) < 32:
        return None
    n = struct.unpack_from('<I', d, 0)[0]
    if not 0 < n < 4096 or 16 + 8 * n > len(d):
        return None
    offs = struct.unpack_from('<%dI' % n, d, 16)
    eo = 16 + 4 * n
    ext = [d[eo + 4 * i:eo + 4 * i + 4].rstrip(b'\0') for i in range(n)]
    if not any(ext) or not all(e.isalnum() and e.isupper() for e in ext if e) or any(o > len(d) for o in offs):
        return None
    out = []
    for i in range(n):
        s = offs[i]
        if s:
            t = min([o for o in offs if o > s] + [len(d)])
            out.append((ext[i].decode('latin-1'), s, t))
    return out


def ps2_walk(d, path, depth=0):
    m = ps2_dat(d)
    if not m:
        return
    for e, s, t in m:
        if e in ('EFF', 'LIT'):
            yield path + '/' + e, e, d[s:t]
        elif depth < 3 and e in ('DAT', 'DAS', ''):
            yield from ps2_walk(d[s:t], path + '/' + e, depth + 1)
        elif depth < 3:
            # unknown member: recurse only when it parses as a container
            if ps2_dat(d[s:t]):
                yield from ps2_walk(d[s:t], path + '/' + e, depth + 1)


def gc_tagged(d):
    """Big-endian tagged archive (u32 count, 12 zero bytes, u32 offsets[count], tags[count][4]) -> [(tag, blob)];
    zero offsets are empty slots. None when the bytes are not one."""
    if len(d) < 32:
        return None
    n = struct.unpack_from('>I', d, 0)[0]
    if not 0 < n <= 4096 or any(d[8:16]) or 16 + 8 * n > len(d):   # +4: total size in enemy drs
        return None
    offs = struct.unpack_from('>%dI' % n, d, 16)
    tags = [d[16 + 4 * n + 4 * i:20 + 4 * n + 4 * i] for i in range(n)]
    if any(o > len(d) or (o and o < 16 + 8 * n) for o in offs):
        return None
    if not all(re.fullmatch(rb'[A-Z0-9 ]{3,4}\0?|\0{4}', t) for t in tags):
        return None
    out = []
    for i in range(n):
        if offs[i]:
            later = [o for o in offs if o > offs[i]]
            out.append((tags[i].rstrip(b'\0').strip().decode(), d[offs[i]:min(later) if later else len(d)]))
    return out


def gc_walk(d, path, depth=0):
    for tag, blob in gc_tagged(d) or []:
        if tag in ('EFF', 'LIT'):
            yield path + '/' + tag, tag, blob
        elif depth < 3 and gc_tagged(blob):
            yield from gc_walk(blob, path + '/' + tag, depth + 1)


def gc_container(d):
    """DVD container (das / drs / dat): the kind-0 payloads (YZ2 decoded when compressed), else the bytes."""
    from decode_yz2 import decode
    if d[:4] in (b'\xca\xb6\xbe\x20', b'\x83\x6e\x83\x4a'):
        out = []
        for pos in range(0x20, 0x400, 0x20):
            kind, size, _, off = struct.unpack_from('>4I', d, pos)
            if kind == 0xFFFFFFFF:
                break
            if kind == 0:
                raw = d[off:off + size]
                try:
                    out.append(bytes(decode(raw)))
                except ValueError:
                    out.append(raw)
        return out
    return [d]


def evd_assets(d):
    """evd (event.h EvtHeader, assetpipe/events.py): asset table at u32 @0x4C, count @0x48, 64-byte rows
    {name[48], u32 start @+48}; asset extent = up to the next asset start."""
    if d[:5] != b'event':
        raise Bad('not an evd')
    _, _, count, bo = struct.unpack_from('>4I', d, 64)
    rows = sorted((struct.unpack_from('>I', d, bo + 64 * i + 48)[0], d[bo + 64 * i:bo + 64 * i + 48].split(b'\0')[0]
                   .decode('latin-1')) for i in range(count))
    for i, (s, name) in enumerate(rows):
        e = rows[i + 1][0] if i + 1 < len(rows) else len(d)
        yield name, d[s:e]


def main():
    rows = json.loads(CLASSIFY.read_text())
    rooms = [r['room'] for r in rows]
    res = {r: {} for r in rooms}
    unproven = {r: {} for r in rooms}
    srcinfo = {r: [] for r in rooms}

    def add(room, cons, ids):
        res[room].setdefault(cons, set()).update(ids)

    def bad(room, cons, why):
        unproven[room].setdefault(cons, []).append(why)

    glob = {'eff_parent': set(), 'eff_scrmodel': set(), 'lit_parent': set()}
    glob_bad = {}
    glob_src = []

    def handle(room, path, kind, blob, end):
        try:
            if kind == 'EFF':
                p, s, n = eff_ids(blob, end)
                ent = dict(src=path, kind=kind, records=n, parent=sorted(p), scrmodel=sorted(s))
                if room:
                    add(room, 'eff_parent', p); add(room, 'eff_scrmodel', s)
                else:
                    glob['eff_parent'] |= p; glob['eff_scrmodel'] |= s
            else:
                ids, n = lit_ids(blob, end)
                ent = dict(src=path, kind=kind, lights=n, parent=sorted(ids))
                if room:
                    add(room, 'lit_parent', ids)
                else:
                    glob['lit_parent'] |= ids
            (srcinfo[room] if room else glob_src).append(ent)
        except Bad as ex:
            cons = 'eff_parent' if kind == 'EFF' else 'lit_parent'
            why = '%s: %s' % (path, ex)
            if room:
                bad(room, cons, why)
                if kind == 'EFF':
                    bad(room, 'eff_scrmodel', why)
            else:
                glob_bad.setdefault(cons, []).append(why)
                if kind == 'EFF':
                    glob_bad.setdefault('eff_scrmodel', []).append(why)

    # ---- PS2 AFS: every member
    f = open(X.ISO, 'rb')
    afs, _ = X.afs_index(f)
    ps2_room_seen = set()
    for name, r in sorted(afs.items()):
        f.seek(r['offset'])
        d = f.read(r['size'])
        m = re.fullmatch(r'(r[0-9a-f]{3})\.dat', name)
        room = m.group(1) if m else None
        if name.endswith('.eff'):
            handle(None, 'ps2:' + name, 'EFF', d, 'le')
            continue
        for path, kind, blob in ps2_walk(d, 'ps2:' + name):
            if kind == 'LIT':
                continue            # PS2 LIT is a different (packed) layout the runtime cLit never reads: the
                                    # shipped room / core LITs are the GC ones (le_mirror), decoded below
            if room is not None and room not in res:
                continue            # a room outside the classified set
            if room:
                ps2_room_seen.add(room)
            handle(room, path, kind, blob, 'le')
    for room in rooms:
        if room not in ps2_room_seen:
            bad(room, 'eff_parent', 'no PS2 %s.dat EFF found' % room)

    # ---- GC ISOs (the runtime's room archives are the GC ones, mirrored by le_mirror)
    code_l = {}
    for room in rooms:
        p = REPO / 'src' / ('st' + room[1]) / (room + '.cpp')
        code_l[room] = p.read_text(errors='replace').lower() if p.exists() else ''
    gc_undecoded = []
    gc_room_tags = {r: set() for r in rooms}
    esl = {}
    for iso in GC_ISOS:
        g = GcIso(iso)
        tagiso = Path(iso).stem
        for key in sorted(g.files):
            low = key.lower()
            if low.endswith('.esl'):
                d = g.read(key)
                for no in range(len(d) // 0x20):
                    be, eid, typ, st = d[no * 0x20:no * 0x20 + 4]
                    rm = struct.unpack_from('>H', d, no * 0x20 + 0x18)[0]
                    if eid:
                        esl.setdefault('r%03x' % rm, []).append((eid, typ, st, tagiso + ':' + key))
                continue
            m = re.fullmatch(r'st\d/(r[0-9a-f]{3})\.das', low)
            room = m.group(1) if m else None
            if room is not None and room not in res:
                continue
            src = 'gc:%s:%s' % (tagiso, key)
            if low.endswith('.eff'):
                handle(None, src, 'EFF', g.read(key), 'be')
                continue
            if low.endswith('.evd'):
                m = re.fullmatch(r'evd/(r[0-9a-f]{3})s[0-9a-f]{2}\.evd', low)
                base = Path(low).stem
                # an evd plays in the room named by its prefix and in any room whose script names it
                targets = {r for r in rooms if base in code_l[r]}
                if m and m.group(1) in res:
                    targets.add(m.group(1))
                if not targets:
                    continue
                try:
                    assets = list(evd_assets(g.read(key)))
                except Bad as ex:
                    for r in targets:
                        bad(r, 'eff_parent', '%s: %s' % (src, ex))
                        bad(r, 'eff_scrmodel', '%s: %s' % (src, ex))
                        bad(r, 'lit_parent', '%s: %s' % (src, ex))
                    continue
                for name, blob in assets:
                    ext = name.rsplit('.', 1)[-1].upper()
                    if ext in ('EFF', 'LIT'):
                        for r in sorted(targets):
                            handle(r, '%s/%s' % (src, name), ext, blob, 'be')
                continue
            if not low.endswith(('.das', '.dat', '.drs')):
                continue
            parsed = False
            for part in gc_container(g.read(key)):
                parsed = parsed or gc_tagged(part) is not None
                for path, tag, blob in gc_walk(part, src):
                    handle(room, path, tag, blob, 'be')
                    if room:
                        gc_room_tags[room].add(tag)
            if not parsed:
                gc_undecoded.append(src)
    for room in rooms:
        for t in ('EFF', 'LIT'):
            if t not in gc_room_tags[room]:
                for c in (('eff_parent', 'eff_scrmodel') if t == 'EFF' else ('lit_parent',)):
                    bad(room, c, 'no GC StN/%s.das %s decoded (the runtime loads the GC room archive)' % (room, t))
    dragon = {0x27: [0xA, 0xB, 0xD, 0xE], 0x28: [0xF, 0x10, 0x12, 0x13], 0x29: [0x14, 0x15, 0x16, 0x17]}
    code = {}
    for room in rooms:
        p = REPO / 'src' / ('st' + room[1]) / (room + '.cpp')
        code[room] = p.read_text(errors='replace') if p.exists() else ''
    for room in rooms:
        ids = set()
        for eid, typ, st, _ in esl.get(room, []):
            if eid == 0x10 and st in dragon:
                ids |= set(dragon[st])
        if room == 'r222':
            ids |= {i for v in dragon.values() for i in v}
        add(room, 'ctrl14', ids)
        ids = set()
        if any(eid == 0x3E for eid, *_ in esl.get(room, [])) or re.search(r'em3e\.h|cEmMark', code[room]):
            ids = {5, 6, 0x33, 0x34, 0x35, 0x36}
        add(room, 'em3e', ids)
        add(room, 'objRobo', {0x43, 0x44, 0x4F, 0x50, 0x51, 0x52} if re.search(r'objRobo\.h|cObjRobo', code[room]) else set())
        add(room, 'sce_com', set())

    # ---- assemble
    out = {'_meta': dict(script=str(Path(__file__)), classify=str(CLASSIFY),
                         global_sets={k: sorted(v) for k, v in glob.items()},
                         global_unproven=glob_bad, global_sources=glob_src,
                         gc_containers_not_decoded=gc_undecoded[:400], gc_containers_not_decoded_count=len(gc_undecoded)),
           'rooms': {}}
    total = 0
    for r in rows:
        room = r['room']
        cons = {}
        for k, v in res[room].items():
            cons[k] = sorted(v | glob.get(k, set()))
        allbad = {}
        for k, whys in list(unproven[room].items()) + list(glob_bad.items()):
            allbad.setdefault(k, []).extend(whys)
        for k, whys in allbad.items():
            cons[k] = 'UNPROVEN: ' + '; '.join(sorted(set(whys)))[:600]
        addr = [x for x in r.get('live', []) if x['why'] == 'addr-unref']
        anyun = any(isinstance(v, str) for v in cons.values())
        live_ids = set()
        for v in cons.values():
            if not isinstance(v, str):
                live_ids |= set(v)
        bakeable = [] if anyun else [x for x in addr if x['id'] not in live_ids]
        total += len(bakeable)
        out['rooms'][room] = dict(consumers=cons, sources=srcinfo[room],
                                  addr_unref_rows=len(addr),
                                  addr_unref_ids=sorted({x['id'] for x in addr}),
                                  data_ref_ids_hit=sorted({x['id'] for x in addr} & live_ids),
                                  provably_bakeable_rows=len(bakeable),
                                  provably_bakeable=[dict(smd=x['smd'], id=x['id']) for x in bakeable],
                                  unproven=anyun)
    out['_meta']['total_provably_bakeable_rows'] = total
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1))
    print('total provably bakeable addr-unref rows', total)
    print('global', {k: sorted(v) for k, v in glob.items()}, 'global unproven', {k: len(v) for k, v in glob_bad.items()})
    print('gc undecoded containers', len(gc_undecoded))
    for room, v in out['rooms'].items():
        un = [k for k, c in v['consumers'].items() if isinstance(c, str)]
        print(room, 'addr-unref', v['addr_unref_rows'], 'bakeable', v['provably_bakeable_rows'],
              'hit', v['data_ref_ids_hit'], 'UNPROVEN' if un else '', un)


if __name__ == '__main__':
    main()
