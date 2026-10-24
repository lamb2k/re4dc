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


def convert(args):
    out = Path(args.out)
    (out / 'files' / 'em').mkdir(parents=True, exist_ok=True)
    src = pi.Sources()
    weapons = args.weapons.split(',') if args.weapons else sorted(WEAPON_PAIRS)
    manifest, prov, report, failed = [], [], {}, []
    prov.append('\t'.join(['weapon', 'kind', 'gc_member', 'gc_sha256', 'ps2_member', 'ps2_sha256', 'output', 'output_sha256', 'note']))
    for w in weapons:
        gcd = src.gc_file('em/%s.drs' % w)
        ps2d = src.ps2_file('%s.dat' % w)
        base_path = Path(args.base) / ('%s.drs' % w)
        base = bytearray(base_path.read_bytes())
        g = drs.Drs(gcd)
        pe = {i + 4: (t, b) for i, t, b in pb.dat_entries(ps2d)}
        wd = out / 'weapons' / w
        wd.mkdir(parents=True, exist_ok=True)
        rep = dict(weapon=w, base=str(base_path), base_sha256=sha(bytes(base)), gc_sha256=sha(gcd), ps2_dat_sha256=sha(ps2d), bins=[], pictures=[])
        used = {}  # tpl arc -> set of images
        pairs = {}
        for arc, tarc in sorted(WEAPON_PAIRS[w].items()):
            name = '%s_bin%02x' % (w, arc)
            gtag, gb = g.entries[arc - 4]
            row = dict(arc=hex(arc), tpl=hex(tarc), name=name, gc_sha256=sha(gb))
            rep['bins'].append(row)
            if gtag.rstrip(b'\0') != b'BIN' or arc not in pe or pe[arc][0] != 'BIN':
                row.update(status='REFUSED', reason='no BIN pair (GC %s, PS2 %s)' % (gtag, pe.get(arc, ('-',))[0]))
                failed.append(name); continue
            pbn = pe[arc][1]
            ok, why = bone_check(gb, pbn)
            row['bones'] = why
            if not ok:
                row.update(status='REFUSED', reason=why); failed.append(name); continue
            s, e, ltag = le_span(base, arc - 4)
            gc_le = po.to_le(gb, name)
            slot = bytes(base[s:e])
            if slot.rstrip(b'\0') != gc_le.rstrip(b'\0') or len(slot) < len(gc_le.rstrip(b'\0')):
                row.update(status='REFUSED', reason='disc slot is not le_mirror(GC BIN)'); failed.append(name); continue
            new, st = pi.convert_geometry(gb, pbn)
            le = po.to_le(new, name)
            if len(le.rstrip(b'\0')) > len(slot):
                row.update(status='REFUSED', reason='PS2 BIN %d B does not fit the %d B slot' % (len(le), len(slot)), stats=st); failed.append(name); continue
            le = le[:len(slot)] if len(le) > len(slot) else le
            base[s:e] = le + bytes(len(slot) - len(le))
            (wd / (name + '.bin')).write_bytes(le)
            m = po.GcModel(new)
            drawn = [p for p in m.parts if p['tris']]
            used.setdefault(tarc, set()).update(p['hdr'][0x0C] for p in drawn)
            pairs.setdefault(tarc, set()).update((p['hdr'][0x0C], p['hdr'][0x0E]) for p in drawn if p['hdr'][0x0B] & 4)
            row.update(status='PS2', slot_bytes=len(slot), gc_le_bytes=len(gc_le), out_bytes=len(le), out_sha256=sha(le), ps2_sha256=sha(pbn),
                       stats=dict((k, st[k]) for k in ('gc_tris', 'ps2_tris', 'out_tris', 'no_tex_part', 'weight_mismatch', 'flipped', 'degenerate', 'appended_weights', 'shift_lowered')))
            prov.append('\t'.join([w, 'BIN', 'em/%s.drs#%x' % (w, arc), sha(gb), 'BIO4DAT.AFS/%s.dat#%x' % (w, arc), sha(pbn), 'em/%s.drs#%x (le_mirror)' % (w, arc), sha(le), 'geometry PS2, GC joints/parts kept']))
        for tarc, imgs in sorted(used.items()):
            gtag, gt = g.entries[tarc - 4]
            if tarc not in pe or pe[tarc][0] != 'TPL':
                rep['pictures'].append(dict(tpl=hex(tarc), status='GC', reason='no PS2 TPL at this arc')); continue
            ptp = pe[tarc][1]
            tname = '%s_tpl%02x' % (w, tarc)
            swaps, kept, pair_list = pi.convert_pictures(gt, ptp, sorted(imgs), wd, tname, sorted(pairs.get(tarc, ())))
            ts, te, _ = le_span(base, tarc - 4)
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
                prov.append('\t'.join([w, 'TPL', 'em/%s.drs#%x/img%d (key %s)' % (w, tarc, sw['j'], gc_key), sha(gc_texels), 'BIO4DAT.AFS/%s.dat#%x/img%d' % (w, tarc, sw['j']), sha(ptp),
                                       'key %s (re4tex)' % sw['key'], sha(data), 'PS2 picture %dx%d CMPR identity, %s' % (sw['w'], sw['h'], how)]))
            rep['pictures'].append(dict(tpl=hex(tarc), used=sorted(imgs), swaps=written, kept=kept, pairs=pair_list))
            if written:
                manifest.append(dict(room='common', name=tname, swaps=written, pairs=[]))
        (out / 'files' / 'em' / ('%s.drs' % w)).write_bytes(bytes(base))
        rep['out_sha256'] = sha(bytes(base))
        rep['changed'] = rep['out_sha256'] != rep['base_sha256']
        report[w] = rep
        print('%s: bins %s pictures %s %s' % (w, ' '.join('%s=%s' % (r['arc'], r['status']) for r in rep['bins']),
                                              sum(len(p.get('swaps', [])) for p in rep['pictures']), 'changed' if rep['changed'] else 'UNCHANGED'))
    # ps2_items_tex.py reads <lib>/<class>/manifest.json and the PNGs under <lib>/<class>/<room>/
    (out / 'weapons' / 'manifest.json').write_text(json.dumps(dict(tool=TOOL_VERSION, assets=[dict(a, room=a['name'].split('_')[0]) for a in manifest]), indent=1))
    (out / 'provenance.tsv').write_text('\n'.join(prov) + '\n')
    (out / 'report.json').write_text(json.dumps(report, indent=1))
    if failed:
        print('REFUSED:', ' '.join(failed))
    return 1 if failed else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    c = sp.add_parser('convert')
    c.add_argument('--base', required=True)
    c.add_argument('--out', required=True)
    c.add_argument('--weapons')
    a = ap.parse_args()
    sys.exit(convert(a))


if __name__ == '__main__':
    main()
