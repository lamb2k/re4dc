"""HUD widgets of a NAT3 pack, made right for the Dreamcast (lane eng-e1i). Run on a pack after the bake:

    hud_fix.py <pack in> <pack out> <tex.pak> <capture resource-ram-*.raw> [--control-cut]

1. Atlas cuts. The bake's 'source' texture packages are the GameCube pictures padded to a power of two (a 143 x 90 gauge
   frame lives in a 256 x 128 package), but the widget records keep the GameCube texture coordinates (0..1 of the
   unpadded picture), so the renderer drew the padded package whole: the gauge frame shrunk and off its centre, the
   bullet icon and the name plates cut. Each widget's coordinates are scaled to the picture inside its package. The
   GameCube size of each texture key comes from the capture's own RAM (its TPLs, keyed as the capture keys them).
2. Ammo digits. The capture holds the digit widgets with the two pictures it saw ('1' and '0', all 300 pictures), so the
   count could not change. The ten PS2 digit pictures (the PS2 replacements, in tex.pak, of the ten images of the
   GameCube digit TPL that holds the captured digits) are appended to the pack's texture and header tables; each digit
   widget (class 0x21, units 0x0B ones, 0x0A tens, 0x17 hundreds, cockpit.cpp BulletInfo::move) gets in its record word
   7 (mask[1], unused after the bake) the header of the '0' picture plus one; the renderer adds the live digit. The PS2
   pictures are 16 x 32 with the 16 x 24 glyph of the GameCube picture at rows 5..28: their coordinates are cut to the
   glyph rows (measured from the pictures' alpha), where the bake drew the whole canvas (the glyph squeezed to 3/4 of
   the cell, the unlit segments of the PS2 art over the bright lens).
--control-cut: step 2 without the glyph cut (the old atlas cut, texture coordinates 0..1): the digit check's control.

    hud_fix.py --verify <pack>      exit 0 when every digit widget is linked, 1 when not (the step was not run)

native_pack.build (so hill_pack.py too) runs fix_capture as its last step, and native_pack.py, hill_pack.py and
fight/pack_trim.py refuse to write a pack that fails verify: a re-bake cannot lose the fix silently.
"""
import struct, sys, zlib
from pathlib import Path
from pack_scene import block, pack
from logic_delta import Changes

def blocks(b, at=0):
    n = struct.unpack_from("<I", b, at)[0]
    offs = struct.unpack_from(f"<{n + 1}I", b, at + 4)
    base = at + 4 + 4 * (n + 1)
    return [bytes(b[base + offs[i]:base + offs[i + 1]]) for i in range(n)]

def apply(words, row):
    n = struct.unpack_from("<I", row)[0]
    words = (words + [0] * n)[:n]
    at = 4
    while at < len(row):
        i, mask = struct.unpack_from("<2I", row, at); at += 8
        for j in range(32):
            if mask >> j & 1:
                words[i + j] = struct.unpack_from("<I", row, at)[0]; at += 4
    return words

def ram_tpls(ram):
    """(crc, fnv) -> (w, h) of every TPL image in a capture's RAM, and the TPLs as lists of keys (bench/r3_capture.hpp
    texture_key: crc32 and FNV-1a of <5I w,h,format,palette format,palette bytes> + pixels + palette)"""
    BPP = {0: 4, 1: 8, 2: 8, 3: 16, 4: 16, 5: 16, 6: 32, 8: 4, 9: 8, 10: 16, 14: 4}
    BLK = {4: (8, 8), 8: (8, 4), 16: (4, 4), 32: (4, 4)}
    def addr(v, base): return (v & 0xffffff) if 0x8c000000 <= v < 0x8d000000 else base + v
    sizes, tpls = {}, []
    for magic, e in ((b"\x00\x20\xaf\x30", ">"), (b"\x30\xaf\x20\x00", "<")):
        at = 0
        while True:
            at = ram.find(magic, at)
            if at < 0: break
            try:
                n, table = struct.unpack_from(e + "2I", ram, at + 4)
                if not 0 < n < 256: raise ValueError
                keys = []
                for i in range(n):
                    ih, ph = struct.unpack_from(e + "2I", ram, addr(table, at) + 8 * i)
                    h, w = struct.unpack_from(e + "2H", ram, addr(ih, at)); f, d = struct.unpack_from(e + "2I", ram, addr(ih, at) + 4)
                    if f not in BPP or not (0 < w <= 1024 and 0 < h <= 1024): raise ValueError
                    b = BPP[f]; bw, bh = BLK[b]
                    pix = ram[addr(d, at):addr(d, at) + ((w + bw - 1) // bw * bw) * ((h + bh - 1) // bh * bh) * b // 8]
                    pal = b""; pf = 0xffffffff
                    if ph and f in (8, 9, 10):
                        po = addr(ph, at); ne = struct.unpack_from(e + "H", ram, po)[0]; pf, pd = struct.unpack_from(e + "2I", ram, po + 4)
                        pal = ram[addr(pd, at):addr(pd, at) + ne * 2]
                    payload = struct.pack("<5I", w, h, f, pf, len(pal)) + pix + pal
                    fnv = 2166136261
                    for x in payload: fnv = ((fnv ^ x) * 16777619) & 0xffffffff
                    k = (zlib.crc32(payload) & 0xffffffff, fnv)
                    sizes[k] = (w, h); keys.append(k)
                tpls.append(keys)
            except (ValueError, struct.error, IndexError):
                pass
            at += 4
    return sizes, tpls

DIGIT_MARKS = (0x0B, 0x0A, 0x17)   # ones, tens, hundreds (cockpit.cpp BulletInfo::move)

def fix(data, texpak, ram, control_cut=False, log=print):
    magic, ver, room, n, crc = struct.unpack_from("<4s4I", data)
    if magic != b"NAT3" or zlib.crc32(data[20:]) != crc: raise ValueError("not a NAT3 pack")
    if linked_digits(data)[0]: raise ValueError("HUD fix: the pack is fixed already (a second run would scale twice)")
    secs = blocks(data, 20)
    if len(secs) != 15: raise ValueError("pack sections")
    textures, headers, frames = blocks(secs[0]), blocks(secs[1]), blocks(secs[3])
    hud_rows = blocks(secs[4 + 5])
    count, idx = struct.unpack_from("<2I", texpak, 12)
    lookup = {(a, b): (c, d) for a, b, c, d in struct.iter_unpack("<4I", texpak[idx:idx + 16 * count])}
    sizes, tpls = ram_tpls(ram)
    by_fnv = {}
    for k, wh in sizes.items(): by_fnv.setdefault(k[1], set()).add(wh)
    def pkg_info(pkg):
        at = struct.unpack_from("<I", pkg, 24)[0]
        return pkg[at:at + 64].split(b"\0")[0], struct.unpack_from("<2I", pkg, at + 64)
    # the ten PS2 digit pictures: the TPL whose image 0 and 1 are the captured '0' and '1'
    states, w = [], []
    for f in frames:
        w = apply(w, hud_rows[struct.unpack_from("<10I", f)[6]]); states.append(list(w))
    first = states[0]
    digit_fnv = set()
    for at in range(4, len(first), 24):
        if (first[at] >> 8 & 255) == 0x21 and (first[at] >> 16 & 255) in DIGIT_MARKS: digit_fnv.add(first[at + 5])
    tpl = next((t for t in tpls if len(t) >= 10 and {k[1] for k in t[:10]} >= digit_fnv and digit_fnv), None)
    if tpl is None: raise ValueError(f"no digit TPL in the capture RAM for {sorted(map(hex, digit_fnv))}")
    first_digit = len(headers)
    template = None
    for at in range(4, len(first), 24):
        if first[at + 5] in digit_fnv and first[at + 4] != 0xffffffff: template = headers[first[at + 4]]; break
    rows_top, rows_bottom = 32, 0
    import numpy as np, dctex
    for d in range(10):
        if tpl[d] not in lookup: raise ValueError(f"digit {d} key {tpl[d]} not in tex.pak")
        off, size = lookup[tpl[d]]; pkg = bytes(texpak[off:off + size])
        name, (pw, ph) = pkg_info(pkg)
        if name != b"ps2-source": raise ValueError(f"digit {d}: tex.pak holds {name!r}, not a PS2 picture")
        a = dctex.decode(pkg)[..., 3]; ys = np.nonzero(a.max(axis=1))[0]
        rows_top = min(rows_top, int(ys.min())); rows_bottom = max(rows_bottom, int(ys.max()) + 1)
        tid = len(textures); textures.append(pkg)
        headers.append(struct.pack("<I", tid) + template[4:])
    gw, gh = sizes[tpl[0]]
    cut = (0.0, 0.0, 1.0, 1.0) if control_cut else (0.0, rows_top / ph, 1.0, rows_bottom / ph)
    log(f"digits: TPL of {len(tpl)} images, GameCube {gw}x{gh}, PS2 {pw}x{ph} glyph rows {rows_top}..{rows_bottom - 1}; "
        f"headers {first_digit}..{first_digit + 9}; cut {'0..1 (CONTROL: the old cut)' if control_cut else 'v %.4f..%.4f' % cut[1::2]}")
    if rows_bottom - rows_top != gh: log(f"WARNING: glyph rows {rows_bottom - rows_top} != GameCube height {gh}")
    scaled = {}
    for s in states:
        for at in range(4, len(s), 24):
            if (s[at] >> 8 & 255) == 0x21 and (s[at] >> 16 & 255) in DIGIT_MARKS:
                s[at + 7] = first_digit + 1
                s[at + 20:at + 24] = [struct.unpack("<I", struct.pack("<f", v))[0] for v in cut]
                continue
            h = s[at + 4]
            if h == 0xffffffff or h >= first_digit: continue
            name, (pw2, ph2) = pkg_info(textures[struct.unpack_from("<I", headers[h])[0]])
            src = by_fnv.get(s[at + 5])
            if name != b"source" or not src or len(src) != 1: continue
            (sw, sh), = src
            if (sw, sh) == (pw2, ph2) or sw > pw2 or sh > ph2: continue
            uv = list(struct.unpack("<4f", struct.pack("<4I", *s[at + 20:at + 24])))
            uv = [uv[0] * sw / pw2, uv[1] * sh / ph2, uv[2] * sw / pw2, uv[3] * sh / ph2]
            s[at + 20:at + 24] = list(struct.unpack("<4I", struct.pack("<4f", *uv)))
            scaled[s[at] & 255] = (sw, sh, pw2, ph2)
    for i, (sw, sh, pw2, ph2) in sorted(scaled.items()):
        log(f"widget {i}: picture {sw}x{sh} in a {pw2}x{ph2} package, coordinates scaled")
    # re-encode the HUD stream and the frame table
    enc = Changes(); table, ids, new_frames = [], {}, []
    for f, s in zip(frames, states):
        row = enc.encode(struct.pack(f"<{len(s)}I", *s))
        if row not in ids: ids[row] = len(table); table.append(row)
        v = list(struct.unpack("<10I", f)); v[6] = ids[row]; new_frames.append(pack("10I", *v))
    secs[0], secs[1], secs[3], secs[4 + 5] = block(textures), block(headers), block(new_frames), block(table)
    body = block(secs)
    out = pack("4s4I", b"NAT3", ver, room, len(body), zlib.crc32(body)) + body
    verify(out)
    return out

def linked_digits(data):
    """(the digit widgets of picture 1 linked to the PS2 digit pictures (record word 7), all digit widgets)"""
    magic, ver, room, n, crc = struct.unpack_from("<4s4I", data)
    if magic != b"NAT3" or zlib.crc32(data[20:]) != crc: raise ValueError("not a NAT3 pack")
    secs = blocks(data, 20)
    w = apply([], blocks(secs[4 + 5])[struct.unpack_from("<10I", blocks(secs[3])[0])[6]])
    digits = [at for at in range(4, len(w), 24) if (w[at] >> 8 & 255) == 0x21 and (w[at] >> 16 & 255) in DIGIT_MARKS]
    return [at for at in digits if w[at + 7]], digits

def verify(data):
    """refuse a pack whose digit widgets are not linked (the bake ended without this step); -> the linked count"""
    linked, digits = linked_digits(data)
    if not digits or len(linked) != len(digits):
        raise ValueError(f"HUD fix missing: {len(linked)} of {len(digits)} digit widgets linked to the PS2 digit pictures "
                         "(run bake/hud_fix.py as the bake's last step)")
    return len(linked)

def fix_capture(data, disc, capture, log=print):
    """the bake's last step (native_pack.build): tex.pak from the disc tree, the capture's own RAM snapshot"""
    rams = sorted(Path(capture).glob("resource-ram-*.raw"))
    if not rams: raise ValueError(f"HUD fix: no resource-ram-*.raw in {capture}")
    return fix(data, (Path(disc) / "tex.pak").read_bytes(), rams[0].read_bytes(), log=log)

if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["--verify"] and len(a) == 2:   # exit 0 when the step was run, 1 when not
        try: print(f"{a[1]}: {verify(Path(a[1]).read_bytes())} digit widgets linked: PASS")
        except ValueError as e: print(f"{a[1]}: {e}: FAIL"); sys.exit(1)
        sys.exit(0)
    if len(a) < 4: sys.exit(__doc__)
    out = fix(Path(a[0]).read_bytes(), Path(a[2]).read_bytes(), Path(a[3]).read_bytes(), "--control-cut" in a)
    Path(a[1]).write_bytes(out); print("wrote", a[1], len(out))
