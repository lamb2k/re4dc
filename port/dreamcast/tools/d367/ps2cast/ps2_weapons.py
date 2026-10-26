#!/usr/bin/env python3
"""ps2_weapons.py: PS2 weapon models and pictures in Leon's weapon archives (lane purge-weapons24, 2026-10-24).

Coordinator decision C (2026-10-24): an offline rewrite of the GameCube weapon BINs. Each weapon archive em/wepNN.drs
keeps every GameCube identity and all of its logic data: the archive table, the REL, the motions (FCV / SEQ), the
effects (EFF / UWF), the sound bank, Leon's hand BINs (attach ids 9 / 10, 15 / 16: Leon's model, not the weapon) and
every entry offset and size. Only two kinds of bytes change, in place, inside the DISC file (the release's own
em/wepNN.drs, le_mirror form, with its rebuilt sound bank and compacted REL):
  geometry  each weapon BIN the module draws (modelInit / SetObj10 call sites, WEAPON_PAIRS below) is rebuilt with the
            PS2 BIN's triangles (ps2_objects.rebuild through ps2_items.convert_geometry: GC header, joints, part
            headers, order and joint tables kept), converted by le_mirror and written over the GC BIN's slot, zero
            padded. Refused unless the PS2 bone table equals the GC part table (id = GC attach, parent, rest
            translation within BONE_TOL mm), the slot holds exactly le_mirror(GC BIN) and the new BIN fits the slot.
  pictures  every GC TPL image a converted part samples is replaced by the PS2 TPL entry of the same index
            (ps2_items.convert_pictures: orientation check, CMPR encode). Only a swap at the GC picture's size and
            format (CMPR) is written: the CMPR texels go over the GC texels (the TPL header is unchanged), so the
            runtime's image key becomes the PS2 picture's identity (ps2_items.identity_key); its <key>.re4tex comes
            from ps2_items_tex.py (Windows Python) over <out>/weapons/manifest.json. Anything else keeps the GC picture.

The GC <-> PS2 file map is identity by name: the PS2 ELF's Leon weapon file table (SLUS_211.34 0x229e58, 46 x
{u16 AFS index dat, u16 rel, u32 0}) names wepNN.dat for every slot the GC table (src/game/read.cpp wep_data_leon +
dvd.cpp FileTbl) names em/wepNN.das (weapon-map.json in the lane evidence).

  ps2_weapons.py convert --base <dir with the release's em/wepNN.drs> --out <dir> [--weapons wep02,...]
      writes <out>/files/em/wepNN.drs, <out>/weapons/<wep>/ (PNG / CMPR per swap, rebuilt BINs), manifest.json
      (ps2_items_tex.py's input), provenance.tsv (PS2 source member + sha256, output sha256 per rewritten BIN / picture)
      and report.json. Exit 1 when a requested weapon has a refused BIN.
  ps2_weapons.py convert-ss --base <dir with the release's ss/cmn/ss_wepNN.dat> --out <dir> [--weapons ss_wep02,...]
      the same for the sub screen's weapon models (inventory / examine): <out>/files/ss/cmn/ss_wepNN.dat.
  ps2_weapons.py convert-pl --base <dir with the release's em/plNN.drs> --out <dir> [--weapons pl00,pl08]
      the same for the weapon models in Leon's own archives (PLAYER_PAIRS: grenades, eggs, rocket launcher, rocket).
"""
import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parents[1]
sys.path[:0] = [str(TOOLS), str(TOOLS.parents[2] / 'tools')]
import drs  # noqa: E402
import ps2_bin as pb  # noqa: E402
import ps2_items as pi  # noqa: E402
import ps2_objects as po  # noqa: E402
from motion import modelbin  # noqa: E402

TOOL_VERSION = 'ps2_weapons-v1'
BONE_TOL = 0.01
# BIN arc -> TPL arc of every weapon model the module draws, by the code that reads the file (the REL named by
# wep_data_leon): modelInit(bin, tpl) and SetObj10(bin, tpl) call sites. Hand BINs (initWepHand) are Leon's model.
WEAPON_PAIRS = {
    'wep01': {0x6: 0x5, 0x7: 0x5, 0x8: 0x9},              # wep01/objFn57.cpp 49-56, 195
    'wep02': {0x6: 0x5, 0x7: 0x5, 0x8: 0x9},              # wep02/objMauser.cpp 54-62, 161; wep/objRuger.cpp 52-58, 195
    'wep03': {0x6: 0x5, 0x7: 0x5, 0x8: 0x9, 0x43: 0x44},  # rel wep02: objMauser.cpp + 272
    'wep04': {0x6: 0x5, 0x7: 0x5, 0x8: 0x9},              # wep04/wep04.cpp 86-92, 245
    'wep05': {0x6: 0x5},                                  # wep05/objCivilian.cpp 38
    'wep06': {0x6: 0x5, 0x7: 0x5, 0x3F: 0x40},            # wep06/wep06.cpp 68-78, 202
    'wep07': {0x5: 0x6, 0x8: 0x9},                        # wep07/wep07.cpp 65, 195
    'wep08': {0x5: 0x6, 0x8: 0x9},                        # wep08/wep08.cpp 65, 167
    'wep09': {0xA: 0x9, 0xB: 0xC},                        # wep09/objSniper.cpp 44, 112
    'wep10': {0xA: 0x9},                                  # wep10/objHkSniper.cpp 32
    'wep11': {0x6: 0x5, 0x7: 0x5, 0x8: 0x5, 0x9: 0x5, 0xA: 0xB},  # wep/objMachinegun.cpp 37-49, 161
    'wep12': {0x6: 0x5, 0xA: 0xB},                        # wep12/objTompson.cpp 29, 137
    'wep14': {0x8: 0x7},                                  # wep14/objMine.cpp 59
    'wep15': {0x6: 0x5},                                  # wep15/wep15.cpp 61
    'wep16': {0x6: 0x5},                                  # wep16/wep16.cpp 50
    'wep17': {0x6: 0x5, 0x7: 0x8},                        # wep17/objVp70.cpp 46, 187
    'wep18': {0x6: 0x5, 0x7: 0x5, 0x8: 0x9, 0x43: 0x44},  # rel wep02 (Red9 with stock)
    'wep20': {0x6: 0x5, 0x7: 0x5, 0x8: 0x5, 0x9: 0x5, 0xA: 0xB},  # rel wep11 (TMP with stock)
    'wep21': {0xA: 0x9, 0xB: 0xC},                        # rel wep09 (rifle, scope)
    'wep24': {0xA: 0x9, 0xB: 0xC},                        # rel wep09 (rifle, scope)
    'wep25': {0x8: 0x7},                                  # rel wep14
    'wep31': {0xA: 0x9},                                  # rel wep10
    'wep32': {0xA: 0x9},                                  # rel wep10
    'wep33': {0x5: 0x6, 0x8: 0x9},                        # wep33/wep33.cpp 64, 183
}


def sha(b):
    return hashlib.sha256(b).hexdigest()


def le_body(d):
    """(body offset, body size, count, rel offset, [entry offsets], [tags]) of a le_mirror DRS (records LE)."""
    t, size, _, ofs = struct.unpack_from('<4I', d, 32)
    if t != 0:
        raise ValueError('DRS record 0 is not the body')
    count, rel = struct.unpack_from('<2I', d, ofs)
    offs = list(struct.unpack_from('<%dI' % count, d, ofs + 16))
    tags = [d[ofs + 16 + 4 * count + 4 * i:ofs + 20 + 4 * count + 4 * i] for i in range(count)]
    return ofs, size, count, rel, offs, tags


def le_span(d, i):
    ofs, size, count, rel, offs, tags = le_body(d)
    end = min([o for o in offs if o > offs[i]] + [rel or size])
    return ofs + offs[i], ofs + end, tags[i]


def fill_empty_parts(d):
    """A part the PS2 mesh leaves without triangles keeps its GC header but gets one position-degenerate 0x90
    triangle (record 0 three times) in its 32-byte list. An empty list is declined by the native actor path
    (native_actor_fast.cpp parse(): count == 0) and falls to the generic draw, whose first opaque part
    allocates the 128 KB retained preparation from room heap 4 (ui_bridge.cpp re4dc_model_retained_storage):
    the Test 24 r100 s30 heap-4 shortfall. The triangle has zero area, so nothing is drawn."""
    d = bytearray(d)
    m = po.GcModel(bytes(d))
    cur, filled = m.parts_off, 0
    for k in range(m.nd):
        size = struct.unpack_from('>I', d, cur + 0x18)[0]
        body = cur + 0x20
        if not any(d[body:body + size]):
            need = 3 + 3 * m.stride
            assert size >= need, ('empty part too small', k, size)
            d[body] = 0x90
            struct.pack_into('>H', d, body + 1, 3)
            filled += 1
        cur = body + size
    return bytes(d), filled


def bone_check(gc_bin, ps2_bin):
    gm = modelbin.parse(gc_bin)
    pm = pb.parse_bin(ps2_bin)
    g = [(p.attach, p.parent, p.pos) for p in gm.parts]
    p = [(b['id'], b['parent'], b['pos']) for b in pm.bones]
    if len(g) != len(p):
        return False, 'bone count GC %d PS2 %d' % (len(g), len(p))
    for a, b in zip(g, p):
        if a[0] != b[0] or a[1] != b[1]:
            return False, 'bone %d: GC id/parent %d/%d, PS2 %d/%d' % (g.index(a), a[0], a[1], b[0], b[1])
        dt = max(abs(x - y) for x, y in zip(a[2], b[2]))
        if dt > BONE_TOL:
            return False, 'bone %d: rest translation differs by %.3f mm' % (g.index(a), dt)
    return True, 'match (%d bones)' % len(g)


def skeleton_fit(gc_bin, ps2_bin):
    """gc-audit25 (10-25): the PS2 mesh fitted to the GC skeleton. When the bone tables differ only by ONE translation
    d shared by every child of the root (ids, parents and every deeper rest translation within BONE_TOL), the PS2 model
    is the GC model moved by d in model space (wep05 Broken Butterfly: d = (-14.97, -4.42, 8.32)). Moving every PS2
    vertex by -d puts it on the GC skeleton exactly. -> (offset or None, why)."""
    gm = modelbin.parse(gc_bin)
    pm = pb.parse_bin(ps2_bin)
    g = [(p.attach, p.parent, p.pos) for p in gm.parts]
    p = [(b['id'], b['parent'], b['pos']) for b in pm.bones]
    if len(g) != len(p) or any(a[0] != b[0] or a[1] != b[1] for a, b in zip(g, p)):
        return None, 'bone ids / parents differ'
    root = g[0][0]
    d = None
    for a, b in zip(g, p):
        dt = tuple(y - x for x, y in zip(a[2], b[2]))
        if a[1] == root and a[1] >= 0:
            d = d or dt
            if max(abs(x - y) for x, y in zip(d, dt)) > BONE_TOL:
                return None, 'root children move by different translations'
        elif max(abs(x) for x in dt) > BONE_TOL:
            return None, 'bone %d rest differs below the root children' % a[0]
    if not d:
        return None, 'no root child'
    off = tuple(-x for x in d)
    return off, 'fit: PS2 mesh moved by (%.3f, %.3f, %.3f) onto the GC skeleton' % off


def em_units(args, src):
    """Leon's weapon archives em/wepNN.drs (DRS body; archive numbers = entry index + 4)."""
    for w in (args.weapons.split(',') if args.weapons else sorted(WEAPON_PAIRS)):
        gcd = src.gc_file('em/%s.drs' % w)
        ps2d = src.ps2_file('%s.dat' % w)
        g = drs.Drs(gcd)
        yield dict(w=w, rel='em/%s.drs' % w, gc_rel='em/%s.drs' % w, ps2_name='%s.dat' % w, gcd=gcd, ps2d=ps2d,
                   base=Path(args.base) / ('%s.drs' % w), gc_entry=lambda arc, g=g: g.entries[arc - 4],
                   pe={i + 4: (t, b) for i, t, b in pb.dat_entries(ps2d)},
                   span=lambda base, arc: le_span(base, arc - 4), pairs=WEAPON_PAIRS[w])


# wep19-26 (2026-10-26): weapon models that live in Leon's own archive (em/pl00.drs, and pl08 for the no-jacket
# costume), drawn by the weapon code from PL_ARC_PTR(pG->pPlayer, ...): BIN arc -> the TPL arcs it is drawn with.
#   0x6A grenade body with 0x6B hand / 0x6D incendiary / 0x6F flash (wep19.cpp cObjHandGre::init, objSubWep.cpp thrown)
#   0x7D egg with 0x7E / 0x7F / 0x80 (same call sites, weapon numbers 0x19 / 0x1F / 0x20)
#   0x70 with 0x71 (objRocket.cpp 38 launcher, wep28.cpp 256 / SetMine)   0x76 with 0x75 (objRocket.cpp 226 rocket)
#   (0x77 / 0x78 is the radio, sscrn.cpp 1116: not a weapon)
PLAYER_PAIRS = {
    'pl00': {0x6A: (0x6B, 0x6D, 0x6F), 0x7D: (0x7E, 0x7F, 0x80), 0x70: 0x71, 0x76: 0x75},
    'pl08': {0x6A: (0x6B, 0x6D, 0x6F), 0x7D: (0x7E, 0x7F, 0x80), 0x70: 0x71, 0x76: 0x75},
}


def pl_units(args, src):
    """Weapon models in Leon's archives em/plNN.drs (PLAYER_PAIRS; archive numbers = entry index + 4)."""
    for w in (args.weapons.split(',') if args.weapons else sorted(PLAYER_PAIRS)):
        gcd = src.gc_file('em/%s.drs' % w)
        ps2d = src.ps2_file('%s.dat' % w)
        g = drs.Drs(gcd)
        yield dict(w=w, rel='em/%s.drs' % w, gc_rel='em/%s.drs' % w, ps2_name='%s.dat' % w, gcd=gcd, ps2d=ps2d,
                   base=Path(args.base) / ('%s.drs' % w), gc_entry=lambda arc, g=g: g.entries[arc - 4],
                   pe={i + 4: (t, b) for i, t, b in pb.dat_entries(ps2d)},
                   span=lambda base, arc: le_span(base, arc - 4), pairs=PLAYER_PAIRS[w])


def ss_units(args, src):
    """The sub screen's weapon models ss/cmn/ss_wepNN.dat (inventory / examine views; tagged archive, entry index =
    SS_ARC number). The weapon BINs are the ones whose root part attaches to 0 (the others, attach 9 / 15, are Leon's
    hands, drawn with his own picture); every ss_wep file has one TPL, which the weapon BINs sample."""
    import room_smd as rs
    # Leon's sub screen weapons (ss_model.cpp ss_wep%02ld by weapon number); ss_wep28+ belong to the other players
    names = args.weapons.split(',') if args.weapons else ['ss_wep%02d' % n for n in range(0, 20)
                                                          if src.g.find('ss/cmn/ss_wep%02d.dat' % n)]
    for w in names:
        gcd = src.gc_file('ss/cmn/%s.dat' % w)
        ps2d = src.ps2_file('%s.dat' % w)
        if ps2d is None:
            print('%s: no PS2 file' % w)
            continue
        ge = [(t, gcd[s:e]) for t, s, e in rs.tagged_entries(gcd, '>')]
        tpls = [i for i, (t, b) in enumerate(ge) if t.rstrip(b'\0') == b'TPL']
        pairs = {}
        for i, (t, b) in enumerate(ge):
            if t.rstrip(b'\0') == b'BIN' and modelbin.parse(b).parts[0].attach == 0:
                if len(tpls) > 1:
                    raise ValueError('%s: %d TPL entries' % (w, len(tpls)))
                # wep19-26: ss_wep13 / ss_wep19 carry no TPL (the model samples a picture the sub screen loads
                # elsewhere): geometry only (pictures follow their own owner)
                pairs[i] = tpls[0] if tpls else ()
        if not pairs:
            continue

        def span(base, i):
            t, s, e = rs.tagged_entries(bytes(base), '<')[i]
            return s, e, t
        yield dict(w=w, rel='ss/cmn/%s.dat' % w, gc_rel='ss/cmn/%s.dat' % w, ps2_name='%s.dat' % w, gcd=gcd, ps2d=ps2d,
                   base=Path(args.base) / ('%s.dat' % w), gc_entry=lambda i, ge=ge: ge[i],
                   pe={i: (t, b) for i, t, b in pb.dat_entries(ps2d)}, span=span, pairs=pairs)


def convert(args):
    out = Path(args.out)
    src = pi.Sources()
    manifest, prov, report, failed = [], [], {}, []
    prov.append('\t'.join(['weapon', 'kind', 'gc_member', 'gc_sha256', 'ps2_member', 'ps2_sha256', 'output', 'output_sha256', 'note']))
    for u in {'convert-ss': ss_units, 'convert-pl': pl_units}.get(args.cmd, em_units)(args, src):
        w, gcd, ps2d, pe = u['w'], u['gcd'], u['ps2d'], u['pe']
        base_path = u['base']
        base = bytearray(base_path.read_bytes())
        le_span_ = u['span']
        wd = out / 'weapons' / w
        wd.mkdir(parents=True, exist_ok=True)
        rep = dict(weapon=w, file=u['rel'], base=str(base_path), base_sha256=sha(bytes(base)), gc_sha256=sha(gcd), ps2_dat_sha256=sha(ps2d), bins=[], pictures=[])
        used = {}  # tpl arc -> set of images
        pairs = {}
        for arc, tarc in sorted(u['pairs'].items()):
            name = '%s_bin%02x' % (w, arc)
            gtag, gb = u['gc_entry'](arc)
            tarcs = tarc if isinstance(tarc, tuple) else (tarc,)   # one BIN drawn with several TPLs (convert-pl)
            row = dict(arc=hex(arc), tpl=' '.join(hex(t) for t in tarcs), name=name, gc_sha256=sha(gb))
            rep['bins'].append(row)
            if gtag.rstrip(b'\0') != b'BIN' or arc not in pe or pe[arc][0] != 'BIN':
                row.update(status='REFUSED', reason='no BIN pair (GC %s, PS2 %s)' % (gtag, pe.get(arc, ('-',))[0]))
                failed.append(name); continue
            pbn = pe[arc][1]
            ok, why = bone_check(gb, pbn)
            off = None
            if not ok and getattr(args, 'fit_skeleton', False):
                off, fwhy = skeleton_fit(gb, pbn)
                if off:
                    ok, why = True, why + '; ' + fwhy
            row['bones'] = why
            if not ok:
                row.update(status='REFUSED', reason=why); failed.append(name); continue
            s, e, ltag = le_span_(base, arc)
            gc_le = po.to_le(gb, name)
            slot = bytes(base[s:e])
            if slot.rstrip(b'\0') != gc_le.rstrip(b'\0') or len(slot) < len(gc_le.rstrip(b'\0')):
                row.update(status='REFUSED', reason='disc slot is not le_mirror(GC BIN)'); failed.append(name); continue
            new, st = pi.convert_geometry(gb, pbn, pos_offset=off)
            new, st['empty_parts_filled'] = fill_empty_parts(new)
            le = po.to_le(new, name)
            if len(le.rstrip(b'\0')) > len(slot):
                row.update(status='REFUSED', reason='PS2 BIN %d B does not fit the %d B slot' % (len(le), len(slot)), stats=st); failed.append(name); continue
            le = le[:len(slot)] if len(le) > len(slot) else le
            base[s:e] = le + bytes(len(slot) - len(le))
            (wd / (name + '.bin')).write_bytes(le)
            m = po.GcModel(new)
            drawn = [p for p in m.parts if p['tris']]
            for tarc in tarcs:
                used.setdefault(tarc, set()).update(p['hdr'][0x0C] for p in drawn)
                pairs.setdefault(tarc, set()).update((p['hdr'][0x0C], p['hdr'][0x0E]) for p in drawn if p['hdr'][0x0B] & 4)
            row.update(status='PS2', slot_bytes=len(slot), gc_le_bytes=len(gc_le), out_bytes=len(le), out_sha256=sha(le), ps2_sha256=sha(pbn),
                       stats=dict((k, st[k]) for k in ('gc_tris', 'ps2_tris', 'out_tris', 'no_tex_part', 'weight_mismatch', 'flipped', 'degenerate', 'appended_weights', 'shift_lowered', 'empty_parts_filled')))
            prov.append('\t'.join([w, 'BIN', '%s#%x' % (u['gc_rel'], arc), sha(gb), 'BIO4DAT.AFS/%s#%x' % (u['ps2_name'], arc), sha(pbn), '%s#%x (le_mirror)' % (u['rel'], arc), sha(le), 'geometry PS2, GC joints/parts kept']))
        for tarc, imgs in sorted(used.items()):
            gtag, gt = u['gc_entry'](tarc)
            if tarc not in pe or pe[tarc][0] != 'TPL':
                rep['pictures'].append(dict(tpl=hex(tarc), status='GC', reason='no PS2 TPL at this arc')); continue
            ptp = pe[tarc][1]
            tname = '%s_tpl%02x' % (w, tarc)
            swaps, kept, pair_list = pi.convert_pictures(gt, ptp, sorted(imgs), wd, tname, sorted(pairs.get(tarc, ())))
            ts, te, _ = le_span_(base, tarc)
            gimg = {x['j']: x for x in pi.gc_tpl_images(gt)}
            written = []
            for sw in swaps:
                gi = gimg[sw['j']]
                if sw.get('role') == 'mask' or (sw['w'], sw['h']) != (gi['w'], gi['h']) or gi['fmt'] != pi.CMPR:
                    kept.append(dict(j=sw['j'], reason='PS2 %dx%d vs GC %dx%d fmt %d: not written in place' % (sw['w'], sw['h'], gi['w'], gi['h'], gi['fmt'])))
                    continue
                data = (wd / sw['cmpr']).read_bytes()
                n = pi.image_size(gi['w'], gi['h'], gi['fmt'])
                assert len(data) == n, (tname, sw['j'], len(data), n)
                # LE TPL: header offsets are LE, the data offset is relative to the TPL start
                desc = struct.unpack_from('<I', base, ts + 8)[0]
                th = struct.unpack_from('<I', base, ts + desc + 8 * sw['j'])[0]
                hh, ww, fmt, doff = struct.unpack_from('<2H2I', base, ts + th)
                assert (ww, hh, fmt) == (gi['w'], gi['h'], gi['fmt']), (tname, sw['j'], ww, hh, fmt)
                gc_texels = gt[gi['data']:gi['data'] + n]
                gc_key = pi.identity_key(gi['w'], gi['h'], gi['fmt'], gc_texels)
                at = ts + doff
                kc, kf = (int(x, 16) for x in sw['key'].split('-'))
                if bytes(base[at:at + 8]) == b'R4NREF\0\0':
                    # prepared archive: the texels are externalised; the record names the package (crc, fnv, w, h, fmt,
                    # bytes). Only the key words change: the record, the image header and the NTR rows stay in place.
                    m_, c0, f0, rw, rh, rf, rn = struct.unpack_from('<8s6I', base, at)
                    assert '%08x-%08x' % (c0, f0) == gc_key and (rw, rh, rf, rn) == (gi['w'], gi['h'], gi['fmt'], n), (tname, sw['j'], 'record is not the GC image')
                    struct.pack_into('<8s6I', base, at, b'R4NREF\0\0', kc, kf, rw, rh, rf, rn)
                    how = 'record'
                else:
                    assert bytes(base[at:at + n]) == gc_texels, (tname, sw['j'], 'disc texels are not the GC texels')
                    base[at:at + n] = data
                    how = 'texels'
                sw = dict(sw, written=how, gc_key=gc_key)
                written.append(sw)
                prov.append('\t'.join([w, 'TPL', '%s#%x/img%d (key %s)' % (u['gc_rel'], tarc, sw['j'], gc_key), sha(gc_texels), 'BIO4DAT.AFS/%s#%x/img%d' % (u['ps2_name'], tarc, sw['j']), sha(ptp),
                                       'key %s (re4tex)' % sw['key'], sha(data), 'PS2 picture %dx%d CMPR identity, %s' % (sw['w'], sw['h'], how)]))
            rep['pictures'].append(dict(tpl=hex(tarc), used=sorted(imgs), swaps=written, kept=kept, pairs=pair_list))
            if written:
                manifest.append(dict(room=w, name=tname, swaps=written, pairs=[]))
        dst = out / 'files' / u['rel']
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(bytes(base))
        rep['out_sha256'] = sha(bytes(base))
        rep['changed'] = rep['out_sha256'] != rep['base_sha256']
        report[w] = rep
        print('%s: bins %s pictures %s %s' % (w, ' '.join('%s=%s' % (r['arc'], r['status']) for r in rep['bins']),
                                              sum(len(p.get('swaps', [])) for p in rep['pictures']), 'changed' if rep['changed'] else 'UNCHANGED'))
    # ps2_items_tex.py reads <lib>/<class>/manifest.json and the PNGs under <lib>/<class>/<room>/
    (out / 'weapons').mkdir(parents=True, exist_ok=True)
    (out / 'weapons' / 'manifest.json').write_text(json.dumps(dict(tool=TOOL_VERSION, assets=manifest), indent=1))
    (out / 'provenance.tsv').write_text('\n'.join(prov) + '\n')
    (out / 'report.json').write_text(json.dumps(report, indent=1))
    bad = self_check(report)
    if bad:
        print('SELF-CHECK FAILED:', '; '.join(bad))
    if failed:
        print('REFUSED:', ' '.join(failed))
    return 1 if failed or bad else 0


# wep19-26 (10-26): the Dreamcast steps every converted weapon BIN must have taken. Pictures: ps2_items_tex.py
# encodes VQ (or twiddled 16-bit only when VQ is not smaller) and checks its own output; geometry stripping and LOD
# levels are built by the native actor path at load (native_actor_fast.cpp: strips + relod), not offline.
STEPS = ('degenerate', 'empty_parts_filled')


def self_check(report):
    bad = []
    for w, rep in report.items():
        for r in rep['bins']:
            if r.get('status') != 'PS2':
                continue
            if r['out_bytes'] > r['slot_bytes']:
                bad.append('%s %s: output %d B larger than the %d B slot it replaces' % (w, r['arc'], r['out_bytes'], r['slot_bytes']))
            miss = [k for k in STEPS if k not in r.get('stats', {})]
            if miss:
                bad.append('%s %s: reduction step(s) skipped: %s' % (w, r['arc'], ','.join(miss)))
            st = r.get('stats', {})
            if st.get('out_tris', 0) > st.get('ps2_tris', 0):
                bad.append('%s %s: %d triangles out of %d PS2 source' % (w, r['arc'], st['out_tris'], st['ps2_tris']))
    return bad


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    for nm in ('convert', 'convert-ss', 'convert-pl'):
        c = sp.add_parser(nm)
        c.add_argument('--base', required=True)
        c.add_argument('--out', required=True)
        c.add_argument('--weapons')
        c.add_argument('--fit-skeleton', action='store_true',
                       help='fit a PS2 mesh whose root children are uniformly translated onto the GC skeleton (wep05)')
    a = ap.parse_args()
    sys.exit(convert(a))


if __name__ == '__main__':
    main()
