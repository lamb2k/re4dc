#!/usr/bin/env python3
"""ps2_objects_tex.py: PS2 pictures for the room objects ps2_objects.py converted (lane objs, 2026-10-14).

ps2_objects.py swaps an object's geometry and keeps its GameCube TPL texture: in the native room payload every TPL
image is already an R4NREF / R4PREF record (prepare_native_ui.py compact_room) whose crc / fnv words name the
dc/tex package the runtime loads (room/texture_package.cpp SourceIdentityTable::lookup; TEX_REF_SELFKEY for records
no NTR row covers). The PS2 version of each object samples the same texture space (the PS2 materials index the same
TPL images, ps2_objects.rebuild pairs them by image index) from smaller PS2 pictures. This tool, per converted model:

  1. finds the TPL its parts sample, as the game binds it (src/game/EtcModel.cpp, obj SetObjSmd):
       room BIN #i            -> the room archive's TPL #i+1          | PS2 .dat TPL after the paired PS2 BIN
       ETM etNNNN.bin + .tpl  -> ETM etNNNN.tpl                       | PS2 ETM etNNNN.tpl
       ETM etNNNN.bin, no tpl -> EspGetEfmTplAddr(id): the TPL of effect model <id> in its etNN.eff (EFM table)
                                                                       | the PS2 etNN.eff effect model <id> TPL
  2. decodes the PS2 TPL image of every image index its parts use (ps2_tpl_decode, GS swizzle, alpha 0x80 = 1.0)
     and writes it as a dc/tex package (RE4DCTX v2): opaque -> VQ RGB565 when smaller, else twiddled RGB565;
     binary alpha -> twiddled ARGB1555; graded alpha -> twiddled ARGB4444 (ps2_room_r4im.py's encoder, the PS2
     world's); the key (file name) is CRC32-FNV1a of the payload, as the PS2 world packages;
  3. rewrites the crc / fnv words of the image's record in the payload to that key. Nothing else in the payload moves
     (record shape words, palettes, sizes, NTR rows unchanged), so heap 4 and every offset stay as the geometry dar.

Material pairs (ps2_objects_tex v2, 2026-10-15; the lane items 421b7251 rules): a part with ModelPart flag 4 (flags
byte 0x0B, alpha texture index at 0x0E) draws from ONE package keyed material_pair_identity(colour key, mask key)
(native_ui.cpp model_mask_key). When its colour image is swapped, the mask record keeps its GC key and a pair package
is written under material_pair_identity(new colour key, GC mask key): the PS2 colour RGB + the mask as alpha. The mask
is the PS2 TPL entry that matches the GC mask best (the entry of the mask's index or the colour entry's offset by the
same amount; mean abs intensity difference to the GC mask <= 16; good matches are <= 6), else the GC mask; PS2 4-bit levels (n * 16) are
expanded to n * 17; resampled (nearest) to the colour's size. A colour image that is also a mask, or whose mask record
is not a native reference, stays GC (listed). Unmasked colour pictures whose GC picture is opaque are packaged opaque
(the kept GC material decides coverage).

A shared image (one TPL image several converted models sample, or an EFM TPL the object's breakable debris also
uses) is converted once; every user then draws the PS2 picture. Indexed (R4PREF) records keep their palette checks.
Runs on Windows Python (numpy + PIL for the encoder):

  (WSL) python3 -c 'see dump_gc_rooms() below' : decoded GC room archives for --gc-room
  py ps2_objects_tex.py --room r101 [--gc-room <decoded GC archive>] --dar <objects dar> --report <ps2_objects report.json> --out <new dar>
                        --texdir <dir for <key>.re4tex> [--json report.json]
"""
import argparse, hashlib, json, re, struct, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parents[2] / 'tools')]
import ps2_objects as po  # noqa: E402
import ps2_bin as pb  # noqa: E402
import room_smd as rs  # noqa: E402
import ps2_room_r4im as wr  # noqa: E402  (encoder: pack16, vq_encode, re4dctx_bytes; PS2 TPL decoder: wr.tpl)
import numpy as np  # noqa: E402

GC_ISO = 'C:/Game Dev/Emulators/Resident Evil 4 Debug (Disc 1)/Resident Evil 4 Debug (Disc 1).iso'
PS2_ISO = 'C:/Game Dev/Emulators/re4_helpers/Resident Evil 4 (USA)/Resident Evil 4 (USA).iso'
SRC_ETC = HERE.parents[2] / 'src' / 'game' / 'EtcModel.cpp'


def sha(b):
    return hashlib.sha256(b).hexdigest()


def etc_bindings():
    """etNNNN.bin -> ('tpl', 'etNNNN.tpl') | ('efm', 'etNN.eff', id), from the source's Et*_init functions."""
    s = SRC_ETC.read_text()
    out = {}
    for f in re.split(r'\n(?=\w[\w\s\*]*\bEt\w*\s*\()', s):
        bins = re.findall(r'GetEtcAddr\(arc, "(et\w+\.bin)"\)', f)
        effs = re.findall(r'GetEtcAddr\(arc, "(et\w+\.eff)"\)', f)
        efm = re.findall(r'EspGetEfmTplAddr\((0x[0-9A-Fa-f]+|\d+)', f)
        tpls = re.findall(r'GetEtcAddr\(arc, "(et\w+\.tpl)"\)', f)
        for b in bins:
            if tpls:
                out.setdefault(b, ('tpl', tpls[0]))
            elif efm and effs:
                out.setdefault(b, ('efm', effs[0], int(efm[0], 0)))
    # window / table-driven etc models: "etNNNN.bin", "etNNNN.tpl" pairs (et00.cpp EtXX_init, emwindow.cpp table)
    for f in (SRC_ETC.parent / 'et00.cpp', SRC_ETC.parent / 'emwindow.cpp'):
        for b, t in re.findall(r'"(et\w+\.bin)",\s*"(et\w+\.tpl)"', f.read_text()):
            out.setdefault(b, ('tpl', t))
    return out


def efm_tpl(d, off, en):
    """(absolute offset of effect model <id>'s TPL body, its end bound) for every id of the EFF block at d[off:]."""
    u32 = lambda o: struct.unpack_from(en + 'I', d, o)[0]
    hdr = [u32(off + 4 * i) for i in range(12)]
    if hdr[0] != 0xB:
        raise ValueError('EFF version %#x' % hdr[0])
    ofs_efm_id, ofs_efm = hdr[5], hdr[11]
    if not ofs_efm_id or not ofs_efm:
        return {}
    n = u32(off + ofs_efm_id)
    ids = [struct.unpack_from(en + 'H', d, off + ofs_efm_id + 4 + 8 * i)[0] for i in range(n)]
    t = off + ofs_efm
    ents = [t + u32(t + 4 + 4 * i) for i in range(u32(t))]
    out = {}
    for i, e in zip(ids, ents):
        o_tpl = u32(e + 8)
        out[i] = e + o_tpl
    return out


def room_bindings(room, gd):
    """{room BIN arc index: ('tpl', TPL arc index) | ('efm', EFF arc index, effect model id) | ('ext', what)} from the
    recovered room code (src/st*/<room>.cpp): SetObjSmd / ModInfoMgr.create / setLock / SetEmHit / SetRock(bin, tpl)
    pairs, a SetRock whose tpl came from EspGetEfmTplAddr(id) after EspDataLoad(room EFF), and BINs bound to another
    archive's TPL (r100 BIN 0x33 + PL_ARC_PTR(pe->subArc, 0x255)). A BIN with no binding in its own room's code but
    byte-identical to one bound in another room takes that binding (r104 BIN 0x20 = the r106 / r10a rock)."""
    out = {}
    def scan(r):
        res = {}
        for f in sorted((HERE.parents[2] / 'src').glob('st*/%s.cpp' % r)):
            t = f.read_text(errors='replace')
            for b, tp in re.findall(r'ROOM_ARC_PTR\(pG->pRoom, (0x[0-9A-Fa-f]+)\),\s*ROOM_ARC_PTR\(pG->pRoom, (0x[0-9A-Fa-f]+)\)', t):
                res.setdefault(int(b, 16), ('tpl', int(tp, 16)))
            for b, what in re.findall(r'ROOM_ARC_PTR\(pG->pRoom, (0x[0-9A-Fa-f]+)\),\s*(PL_ARC_PTR\([^)]*\))', t):
                res.setdefault(int(b, 16), ('ext', what))
            for e, eid, b in re.findall(r'EspDataLoad\(\(u32\) ROOM_ARC_PTR\(pG->pRoom, (0x[0-9A-Fa-f]+)\)[^;]*;\s*'
                                         r'if \(EspGetEfmTplAddr\((0x[0-9A-Fa-f]+), &tpl\)[\s\S]{0,1500}?'  # r11e: SetRock 1 KB after
                                         r'SetRock\(ROOM_ARC_PTR\(pG->pRoom, (0x[0-9A-Fa-f]+)\), tpl', t):
                res.setdefault(int(b, 16), ('efm', int(e, 16), int(eid, 0)))
        return res
    out = scan(room)
    ALIAS = {('r104', 0x20): ('r106', 0x20)}  # checked below: the GC BINs must be byte-identical
    for (r, b), (r2, b2) in ALIAS.items():
        if r == room and b not in out:
            import pathlib
            g2 = pathlib.Path(GC_ROOMS_DIR) / (r2 + '.arc') if GC_ROOMS_DIR else None
            if g2 and g2.exists():
                d2 = g2.read_bytes(); e1 = rs.tagged_entries(gd, '>'); e2 = rs.tagged_entries(d2, '>')
                if gd[e1[b - 4][1]:e1[b - 4][2]] == d2[e2[b2 - 4][1]:e2[b2 - 4][2]]:
                    bb = scan(r2).get(b2)
                    if bb:
                        out[b] = bb
    return out


GC_ROOMS_DIR = None


def room_tpl(tags, i):
    """The room-archive TPL a BIN at entry i samples: the first TPL after it past other BINs (r100 BIN 0x26 and 0x27 share
    TPL 0x28), else the last TPL before it past other BINs (r100 BIN 0x33 after BIN 0x31 / TPL 0x32); None if neither."""
    j = i + 1
    while j < len(tags) and tags[j] == 'BIN':
        j += 1
    if j < len(tags) and tags[j] == 'TPL':
        return j
    j = i - 1
    while j >= 0 and tags[j] == 'BIN':
        j -= 1
    return j if j >= 0 and tags[j] == 'TPL' else None


def pair_identity(color_key, mask_key):
    """prepare_native_ui.material_pair_identity / native_ui.cpp model_mask_key"""
    import zlib
    words = [int(v, 16) for k in (color_key, mask_key) for v in k.split('-')]
    payload = b'R4MPv001' + struct.pack('<4I', *words)
    fnv = 2166136261
    for b in payload:
        fnv = ((fnv ^ b) * 16777619) & 0xffffffff
    return '%08x-%08x' % (zlib.crc32(payload) & 0xffffffff, fnv)


def resample(img, h, w):
    ih, iw = img.shape[:2]
    return img[(np.arange(h) * ih // h)][:, (np.arange(w) * iw // w)]


def mask_picture(pimg, cands, gmask, h, w):
    """-> (h x w intensity uint8, source label, error): the PS2 entry in cands closest to the GC mask, else the GC mask"""
    best = None
    gi = gmask[..., :3].astype(np.int32).mean(2) if gmask is not None else None
    for j in cands:
        if j not in pimg or pimg[j][0] == 'error':
            continue
        pw, ph, rgba, il = pimg[j]
        c = np.ascontiguousarray(rgba.transpose(1, 0, 2)) if il & 1 else rgba
        inten = c[..., :3].astype(np.int32).mean(2)
        vals = np.unique(inten)
        if np.all(vals % 16 == 0):
            inten = (inten // 16) * 17
        if gi is None:
            err = 0.0
        else:
            err = float(np.mean(np.abs(resample(inten, *gi.shape) - gi)))
        if best is None or err < best[2]:
            best = (inten, 'PS2 TPL entry %d%s' % (j, ' (4-bit *17)' if np.all(vals % 16 == 0) else ''), err)
    if best is None or best[2] > 16:
        if gi is None:
            raise ValueError('no mask picture')
        best = (gi, 'GC mask' + ('' if best is None else ' (PS2 best %s err %.1f)' % (best[1], best[2])), 0.0)
    return np.clip(resample(best[0], h, w), 0, 255).astype(np.uint8), best[1], round(best[2], 1)


def source_key(pay, rec, gsrc, j):
    """the identity the runtime gives TPL image j (native_ui.cpp image_key): a native reference record's crc / fnv words,
    else the content hash of the source image (prepare_native_ui.image_identity)"""
    if rec[1] in (b'R4NREF\0\0', b'R4PREF\0\0'):
        return '%08x-%08x' % struct.unpack_from('<II', pay, rec[0] + 8)
    import convert_tpl as ct
    import prepare_native_ui as pnu
    return pnu.image_identity(ct.parse_tpl(gsrc)[j])[0]


def pak_keys(path):
    blob = Path(path).read_bytes()
    _, count, index_offset, _, _ = struct.unpack_from('<5I', blob, 8)
    return {'%08x-%08x' % struct.unpack_from('<II', blob, index_offset + 16 * i) for i in range(count)}


def wr_size(w, h, fmt):
    bpp = {0: 4, 1: 8, 2: 8, 3: 16, 4: 16, 5: 16, 6: 32, 8: 4, 9: 8, 10: 16, 14: 4}.get(fmt, 0)
    return w * h * bpp // 8


def gc_tpl_records(pay, tpl):
    """{image index: (record offset, magic)} of a little-endian (le_mirror) GC TPL at pay[tpl:]."""
    num, desc = struct.unpack_from('<II', pay, tpl + 4)
    out = {}
    for i in range(num):
        tex, clut = struct.unpack_from('<II', pay, tpl + desc + 8 * i)
        if not tex:
            continue
        h, w = struct.unpack_from('<HH', pay, tpl + tex)
        fmt, data = struct.unpack_from('<II', pay, tpl + tex + 4)
        rec = tpl + data
        out[i] = (rec, bytes(pay[rec:rec + 8]), w, h, fmt)
    return out


def tpl_header(pay, tpl, i):
    """payload offset of image i's header (u16 height, u16 width, u32 format, u32 data ...) in the TPL at pay[tpl:]."""
    num, desc = struct.unpack_from('<II', pay, tpl + 4)
    tex, clut = struct.unpack_from('<II', pay, tpl + desc + 8 * i)
    return tpl + tex


def resample_smooth(img, h, w):
    """bilinear resize (PIL) of an RGBA ndarray: the PS2 GS filtered its small pictures bilinearly."""
    from PIL import Image
    return np.asarray(Image.fromarray(np.ascontiguousarray(img), 'RGBA').resize((w, h), Image.BILINEAR))


def ps2_images(d, off):
    """PS2 TPL at d[off:] -> {entry: (w, h, rgba ndarray)} (base level), via ps2_tpl_decode."""
    t = wr.tpl
    body = d[off:]
    hdrs = t.parse_tpl(body)['entries']
    out = {}
    for i, h in enumerate(hdrs):
        try:
            res = t.decode(body, h, 'gs')
        except Exception as ex:  # noqa
            out[i] = ('error', str(ex))
            continue
        w, hh, rgba = res[0], res[1], res[2]
        out[i] = (w, hh, np.frombuffer(bytes(rgba), np.uint8).reshape(hh, w, 4), h['interlace'])
    return out


def gc_image(gc_tpl_bytes, k):
    """RGBA ndarray of GC (big-endian source) TPL image k, or None."""
    import convert_tpl as ct
    try:
        ims = ct.parse_tpl(gc_tpl_bytes)
        im = ims[k]
        px = ct.decode_image(im)
        return np.array(px, np.uint8).reshape(im.height, im.width, 4)
    except Exception:  # noqa
        return None


def orient(ps2, gc, rotate):
    """The PS2 picture laid out as the converted geometry samples it, and its mean abs RGB difference to the GC picture.
    The PS2 TPL rotate flag (entry header interlace bit 0) means the GS samples the stored image transposed: the PS2
    UVs (which the converted geometry keeps) index the transposed picture. Proven on r101 (lane objs 10-14): every
    flagged image matches its GC picture best transposed (mean abs diff 3.3-6.7), every unflagged one as stored."""
    c = np.ascontiguousarray(ps2.transpose(1, 0, 2)) if rotate else ps2
    how = 'transpose(rotate flag)' if rotate else 'as stored'
    if gc is None:
        return c, how + ', no GC image', None
    gh, gw = gc.shape[:2]
    ch, cw = c.shape[:2]
    ys = (np.arange(gh) * ch // gh); xs = (np.arange(gw) * cw // gw)
    err = float(np.mean(np.abs(c[ys][:, xs].astype(np.int32)[..., :3] - gc[..., :3].astype(np.int32))))
    if ch * gw != cw * gh:
        how += ', aspect %dx%d vs GC %dx%d' % (cw, ch, gw, gh)
    return c, how, err


def encode(image, label):
    h, w = image.shape[:2]
    alpha = np.unique(image[..., 3])
    mode = 'opaque' if alpha.min() == 255 else ('cutout' if np.all(np.isin(alpha, [0, 255])) else 'graded')
    fmt = {'opaque': 0, 'cutout': 1, 'graded': 2}[mode]
    target = image.astype(np.float64)
    use_vq = fmt == 0 and 2048 + w * h // 4 < w * h * 2
    if use_vq:
        payload = wr.vq_encode(target, fmt); ptype = 2
    else:
        q = wr.pack16(target, fmt)
        raw = np.empty(w * h, dtype='<u2'); raw[wr.codec.untwiddle_index(w, h).ravel()] = q.ravel()
        payload = raw.tobytes(); ptype = 1
    data, key = wr.re4dctx_bytes(label, w, h, fmt, ptype, payload)
    return data, key, dict(width=w, height=h, alpha_mode=mode, format=fmt, payload='vq' if use_vq else 'native16',
                           vram_bytes=len(payload))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--room', required=True); ap.add_argument('--dar', required=True); ap.add_argument('--report', required=True)
    ap.add_argument('--out', required=True); ap.add_argument('--texdir', required=True); ap.add_argument('--json')
    ap.add_argument('--gc-iso', default=GC_ISO); ap.add_argument('--ps2-iso', default=PS2_ISO); ap.add_argument('--gc-room')
    ap.add_argument('--pak', help='dc/tex.pak: a pair is built only when the GC pair (GC colour + mask key) is in it')
    ap.add_argument('--uv-fold', action='store_true', help='ps2_objects converter v3: fold PS2 triangle UVs into [0, 1]')
    ap.add_argument('--upscale-mismatch', action='store_true',
                    help='a PS2 picture of another size than the GC image is upscaled (bilinear) instead of declared')
    ap.add_argument('--share-gc-pictures', action='store_true',
                    help='old behaviour: also swap an ETM TPL image that an unconverted (GameCube) etc model draws')
    a = ap.parse_args()
    paks = pak_keys(a.pak) if a.pak else None
    from assetpipe.rooms import GcIso
    room = a.room
    po.UV_FOLD = a.uv_fold
    dar = bytearray(Path(a.dar).read_bytes())
    rep = json.loads(Path(a.report).read_text())
    kind, size, dest, off = struct.unpack_from('<4I', dar, 0x20)
    pay = memoryview(dar)[off:off + size]
    global GC_ROOMS_DIR
    if a.gc_room:
        GC_ROOMS_DIR = str(Path(a.gc_room).parent)
    if a.gc_room:  # the decoded GC room archive (decode_das needs the WSL PowerPC toolchain): ps2_objects_tex.py dump
        gd = Path(a.gc_room).read_bytes()
    else:
        g = GcIso(a.gc_iso)
        gd = g.read(dict(g.rooms())[room])
        if gd[:32] == rs.CONTAINER_MAGIC:
            gd = rs.decode_das(gd)
    ge = rs.tagged_entries(gd, '>')
    le = rs.tagged_entries(bytes(pay), '<')
    pd = pb.afs_read(a.ps2_iso, room + '.dat', pb.afs_index(a.ps2_iso))
    pe = {i + 4: (t, b) for i, t, b in pb.dat_entries(pd)}
    binds = etc_bindings()
    room_bind = room_bindings(room, gd)
    texdir = Path(a.texdir); texdir.mkdir(parents=True, exist_ok=True)
    # ETM sub-files (GC big-endian source, payload little-endian, PS2)
    ei = next((i for i, (t, s, e) in enumerate(ge) if t.rstrip(b'\0') == b'ETM'), None)
    g_etm = l_etm = p_etm = {}
    if ei is not None:
        gb = gd[ge[ei][1]:ge[ei][2]]
        g_etm = {n.lower(): gb[s + 0x40:e] for n, s, e in po.etm_entries(gb, '>')}
        l_etm = {n.lower(): (le[ei][1] + s + 0x40, le[ei][1] + e) for n, s, e in po.etm_entries(bytes(pay[le[ei][1]:le[ei][2]]), '<')}
        pbm = next((b for t, b in pe.values() if t == 'ETM'), None)
        p_etm = {n.lower(): pbm[s + 0x40:e] for n, s, e in po.etm_entries(pbm, '<')} if pbm else {}
    # Shared ETM pictures (10-15, r105 test 13 TEXCHK "pair missing"): an ETM TPL image is one record in the payload, so
    # swapping it for a converted model also changes it for every etc model that binds the same TPL. When one of those
    # stays GameCube (window pane et0000 with the frame et0001: et0000.tpl image 0 is the pane's colour with a mask
    # image; breakables) the swap would leave its colour + mask pair without a package, or put the PS2 picture on GC
    # geometry. Such images keep the GC picture (the converted model's PS2 UVs index the GC texture space anyway).
    conv = {o['name'].lower() for o in rep['objects'] if o['kind'] != 'room BIN' and not o.get('skipped') and o.get('name')}
    gc_tpl_users = {}  # tpl name -> {image index: [GC etc model names drawing it]}
    for nm2, b2 in g_etm.items():
        if not nm2.endswith('.bin') or nm2 in conv:
            continue
        bb = binds.get(nm2)
        own2 = bb[1] if bb and bb[0] == 'tpl' else nm2.replace('.bin', '.tpl')
        try:
            parts2 = po.GcModel(b2).parts
        except Exception:
            continue
        for q in parts2:
            if q['tris']:
                for k2 in {q['hdr'][0x0C]} | ({q['hdr'][0x0E]} if q['hdr'][0x0B] & 4 else set()):
                    gc_tpl_users.setdefault(own2, {}).setdefault(k2, set()).add(nm2)
    done = {}  # record offset -> key
    done_gc, done_img, built = {}, {}, {}  # record offset -> GC key / (picture, key, PS2 image) / masks paired
    report = dict(room=room, dar_in=a.dar, dar_in_sha256=sha(bytes(dar)), models=[], images=[], pair_extras=[])
    for o in rep['objects']:
        if o.get('skipped') or o.get('ps2_arc') == 'world':
            continue
        entry = dict(kind=o['kind'], name=o.get('name') or o.get('gc_arc'))
        own_tpl = None
        atl = lay = None
        try:
            if o['kind'] == 'room BIN':
                ga, pa = int(o['gc_arc'], 16), int(o['ps2_arc'], 16)
                gbin = gd[ge[ga - 4][1]:ge[ga - 4][2]]
                ps2bin = pe[pa][1]
                bnd = room_bind.get(ga)
                gtags = [t.rstrip(b'\0').decode() for t, s_, e_ in ge]
                if bnd is None:
                    raise ValueError('no texture binding for this room BIN in the room code (src/st*/%s.cpp)' % room)
                if bnd[0] == 'tpl':
                    gt = bnd[1] - 4; pa_t = pa + (bnd[1] - ga)
                    if gtags[gt] != 'TPL' or pe.get(pa_t, ('',))[0] != 'TPL':
                        raise ValueError('bound TPL #%02x / PS2 #%02x is not a TPL' % (bnd[1], pa_t))
                    gtpl = le[gt][1]
                    gsrc = gd[ge[gt][1]:ge[gt][2]]
                    ptpl_d, ptpl_o = pe[pa_t][1], 0
                    src = 'BIN#%02x->TPL#%02x | PS2 BIN#%02x->TPL#%02x' % (ga, bnd[1], pa, pa_t)
                elif bnd[0] == 'efm':
                    ge_i, eid = bnd[1], bnd[2]; pe_i = pa + (ge_i - ga)
                    if gtags[ge_i - 4] != 'EFF' or pe.get(pe_i, ('',))[0] != 'EFF':
                        raise ValueError('bound EFF #%02x / PS2 #%02x is not an EFF' % (ge_i, pe_i))
                    gmap_ = efm_tpl(bytes(pay), le[ge_i - 4][1], '<')
                    pmap_ = efm_tpl(pe[pe_i][1], 0, '<')
                    if eid not in gmap_ or eid not in pmap_:
                        raise ValueError('effect model %#x not in room EFF #%02x' % (eid, ge_i))
                    gtpl = gmap_[eid]
                    geff = gd[ge[ge_i - 4][1]:ge[ge_i - 4][2]]
                    gsrc = geff[efm_tpl(geff, 0, '>')[eid]:]
                    ptpl_d, ptpl_o = pe[pe_i][1], pmap_[eid]
                    src = 'BIN#%02x->EFF#%02x efm %#x | PS2 EFF#%02x' % (ga, ge_i, eid, pe_i)
                else:
                    raise ValueError('texture from outside the room archive: %s' % bnd[1])
            else:
                nm = o['name'].lower()
                ps2 = o.get('ps2_from')
                p_etm_src = p_etm
                if ps2:
                    sroom = ps2.split('.')[0]
                    spd = pb.afs_read(a.ps2_iso, sroom + '.dat', pb.afs_index(a.ps2_iso))
                    spbm = next(b for i, t, b in pb.dat_entries(spd) if t == 'ETM')
                    p_etm_src = {n.lower(): spbm[s + 0x40:e] for n, s, e in po.etm_entries(spbm, '<')}
                gbin = g_etm[nm]
                ps2bin = p_etm_src[nm]
                b = binds.get(nm)
                own = b[1] if b and b[0] == 'tpl' else nm.replace('.bin', '.tpl')
                if own in g_etm and own in l_etm and own in p_etm_src:
                    gtpl = l_etm[own][0]; ptpl_d, ptpl_o = p_etm_src[own], 0
                    gsrc = g_etm[own]
                    src = 'ETM/%s | PS2 ETM/%s' % (own, own)
                    own_tpl = own
                elif b and b[0] == 'efm' and b[1] in l_etm and b[1] in p_etm_src:
                    eff = b[1]; eid = b[2]
                    lo = l_etm[eff][0]
                    gmap = efm_tpl(bytes(pay), lo, '<')
                    pmap = efm_tpl(p_etm_src[eff], 0, '<')
                    if eid not in gmap or eid not in pmap:
                        raise ValueError('effect model %#x not in %s' % (eid, eff))
                    gtpl = gmap[eid]; ptpl_d, ptpl_o = p_etm_src[eff], pmap[eid]
                    gsrc = g_etm[eff][efm_tpl(g_etm[eff], 0, '>')[eid]:]
                    src = 'ETM/%s efm %#x | PS2 ETM/%s efm %#x' % (eff, eid, eff, eid)
                else:
                    raise ValueError('texture source unknown (binding %s)' % (b,))
            # GC image -> the PS2 image(s) of the triangles the converter put in parts sampling it
            if o['kind'] == 'room BIN' and (room, ga) in po.ATLAS_OBJECTS:
                # PS2 atlas (ps2_objects.ATLAS_OBJECTS, lane purge-props24): the same layout ps2_objects.py mapped the UVs to
                atl, lay = po.room_atlas(gbin, ps2bin, ('TPL', ptpl_d[ptpl_o:]), po.ATLAS_OBJECTS[(room, ga)])
                entry['atlas'] = lay
            newbin, st = po.rebuild(gbin, ps2bin, tex_map=po.TEX_MAPS.get(str(entry['name']).lower()), atlas=atl)
            drawn = [q for q in po.GcModel(newbin).parts if q['tris']]
            pair_of = {}
            for q in drawn:
                if q['hdr'][0x0B] & 4:
                    pair_of.setdefault(q['hdr'][0x0C], set()).add(q['hdr'][0x0E])
            gmap = {}
            for k, (gimg, pimgs) in st['part_images'].items():
                gmap.setdefault(gimg, set()).update(pimgs)
            used = sorted(gmap)
            entry['image_map'] = {str(g_): sorted(v) for g_, v in gmap.items()}
            recs = gc_tpl_records(pay, gtpl)
            pimg = ps2_images(ptpl_d, ptpl_o)
            entry.update(source=src, images=used)
            for k in used:
                if k not in recs:
                    raise ValueError('GC TPL has no image %d' % k)
                rec, magic, gw, gh, gfmt = recs[k]
                def plan_pairs(k, masks, d, shape):
                    jobs = []
                    for m in sorted(masks):
                        if m in used:
                            return None, ('image %d is also the mask of image %d' % (m, k)) if m != k else 'image %d is its own mask' % k
                        if m not in recs:
                            return None, 'mask image %d not in the TPL' % m
                        if recs[m][0] in done:
                            return None, 'mask image %d was swapped as a colour by another model' % m
                        mk = source_key(pay, recs[m], gsrc, m)
                        if paks is not None:
                            gck = source_key(pay, recs[k], gsrc, k) if recs[k][0] not in done else done_gc[recs[k][0]]
                            if pair_identity(gck, mk) not in paks:
                                return None, 'GC pair %s (colour %s + mask %d %s) is not in the pak: mask key unproven' % (
                                    pair_identity(gck, mk), gck, m, mk)
                        inten, msrc, merr = mask_picture(pimg, sorted({m, d + m - k}), gc_image(gsrc, m), *shape)
                        jobs.append((m, mk, inten, msrc, merr))
                    return jobs, None

                def write_pairs(k, rgba, key, jobs, model):
                    out = []
                    for m, mk, inten, msrc, merr in jobs:
                        pr = rgba.copy(); pr[..., 3] = inten
                        pdata, _, pmeta = encode(pr, 'PS2 %s object %s pair %d+%d' % (room, model, k, m))
                        pkey = pair_identity(key, mk)
                        (texdir / (pkey + '.re4tex')).write_bytes(pdata)
                        out.append(dict(mask=m, mask_key=mk, key=pkey, mask_source=msrc, mask_error=merr, sha256=sha(pdata),
                                        bytes=len(pdata), alpha_mode=pmeta['alpha_mode'], vram_bytes=pmeta['vram_bytes']))
                    return out

                if rec in done:
                    # converted for an earlier model: build the pairs this model's parts add
                    extra = set(pair_of.get(k, ())) - built[rec]
                    if extra:
                        rgba0, key0, d0 = done_img[rec]
                        jobs, why = plan_pairs(k, extra, d0, rgba0.shape[:2])
                        if why:
                            raise ValueError('image %d (swapped for an earlier model): %s: PAIR MISSING at run time' % (k, why))
                        report['pair_extras'].append(dict(model=entry['name'], image=k, pairs=write_pairs(k, rgba0, key0, jobs, entry['name'])))
                        built[rec] |= extra
                    continue
                gcu = gc_tpl_users.get(own_tpl, {}).get(k) if own_tpl else None
                if gcu and not a.share_gc_pictures:
                    entry.setdefault('kept_gc_images', []).append(dict(
                        image=k, why='image %d of %s is also drawn by GameCube model(s) %s: colour kept GC' % (
                            k, own_tpl, ','.join(sorted(gcu)))))
                    continue
                native = magic in (b'R4NREF\0\0', b'R4PREF\0\0')
                if not native and (gfmt in (8, 9, 10) or rec & 3 or wr_size(gw, gh, gfmt) < 32):
                    raise ValueError('image %d: resident texels that cannot take a self-key record (fmt %d)' % (k, gfmt))
                if lay and k == lay['gc_image']:
                    if (gw, gh) != tuple(po.ATLAS_OBJECTS[(room, ga)]):
                        raise ValueError('atlas: GC image %d is %dx%d, ATLAS_OBJECTS says %s' % (k, gw, gh, po.ATLAS_OBJECTS[(room, ga)]))
                    W_, H_ = lay['size']
                    canvas = np.zeros((H_, W_, 4), np.uint8)
                    for pi, (x_, y_, w_, h_) in sorted((int(i), r) for i, r in lay['rects'].items()):
                        if pi not in pimg or pimg[pi][0] == 'error':
                            raise ValueError('atlas: PS2 TPL image %d missing or undecodable' % pi)
                        sub, _, _ = orient(pimg[pi][2], None, pimg[pi][3] & 1)
                        if sub.shape[:2] != (h_, w_):
                            raise ValueError('atlas: PS2 image %d is %s, layout %dx%d' % (pi, sub.shape[:2], w_, h_))
                        canvas[y_:y_ + h_, x_:x_ + w_] = sub
                    d = min(int(i) for i in lay['rects'])
                    w, h, rgba, il = W_, H_, canvas, 0
                else:
                    if len(gmap[k]) != 1:
                        raise ValueError('GC image %d is sampled by triangles of PS2 images %s' % (k, sorted(gmap[k])))
                    d = next(iter(gmap[k]))
                    if d not in pimg or pimg[d][0] == 'error':
                        raise ValueError('PS2 TPL image %d missing or undecodable: %s' % (d, pimg.get(d)))
                    w, h, rgba, il = pimg[d]
                # image-order check (tex_size_check.py reads it): the PS2 image the triangles use has another size than
                # the GC image while another PS2 image of the same TPL has the GC size -> the PS2 TPL lists the images
                # in another order; ps2_objects.TEX_MAPS must remap the model (r104 et1700, 10-15)
                same = (w, h) in ((gw, gh), (gh, gw))
                order_suspect = [] if same else [j for j, v in sorted(pimg.items())
                                                 if j != d and v[0] != 'error' and (v[0], v[1]) in ((gw, gh), (gh, gw))]
                gk = gc_image(gsrc, k)
                rgba, how, err = orient(rgba, gk, il & 1)
                declare = None
                if rgba.shape[0] != gh or rgba.shape[1] != gw:
                    # The runtime draws a model part with u/v scale = TPL header size / package size and drops a
                    # wrapping part whose package size differs from the header (native_ui.cpp, `wrap=` rejections):
                    # a PS2 picture of another size was not drawn (objs13 look check 10-15: r119 tree, r10b / r11b
                    # island). v5 (coordinator 10-15, the user saw 4x4 blocks from the nearest upscale):
                    # - default: declare the PS2 size, i.e. the TPL image header and the record carry the PS2 width /
                    #   height (render data only; the payload layout does not move) and the package stays PS2-sized;
                    # - a colour image with material-pair masks (the mask must have the colour's size) or an indexed
                    #   R4PREF record: smooth (bilinear) upscale of the PS2 picture to the GC size.
                    if pair_of.get(k) or magic == b'R4PREF\0\0' or a.upscale_mismatch:
                        how += ', bilinear %dx%d -> %dx%d' % (rgba.shape[1], rgba.shape[0], gw, gh)
                        rgba = resample_smooth(rgba, gh, gw)
                    else:
                        declare = (rgba.shape[1], rgba.shape[0])
                        how += ', PS2 size %dx%d declared (GC %dx%d)' % (declare[0], declare[1], gw, gh)
                pair_jobs, why = plan_pairs(k, pair_of.get(k, ()), d, rgba.shape[:2])
                if why:
                    entry.setdefault('kept_gc_images', []).append(dict(image=k, why=why + ' (pair not built: colour kept GC)'))
                    continue
                opaque_gc = gk is not None and int(gk[..., 3].min()) == 255
                if opaque_gc:
                    rgba = rgba.copy(); rgba[..., 3] = 255
                data, key, meta = encode(rgba, 'PS2 %s object %s image %d' % (room, entry['name'], k))
                meta['gc_alpha_opaque'] = opaque_gc
                done_gc[rec] = source_key(pay, recs[k], gsrc, k)
                meta['pairs'] = write_pairs(k, rgba, key, pair_jobs, entry['name'])
                built[rec] = {j[0] for j in pair_jobs}
                done_img[rec] = (rgba, key, d)
                meta.update(orient=how, mean_abs_diff_vs_gc=err, ps2_size=[w, h], order_suspect=order_suspect,
                            tex_map=bool(po.TEX_MAPS.get(str(entry['name']).lower())))
                (texdir / (key + '.re4tex')).write_bytes(data)
                crc, fnv = (int(x, 16) for x in key.split('-'))
                if native:
                    old = struct.unpack_from('<II', pay, rec + 8)
                    struct.pack_into('<II', pay, rec + 8, crc, fnv)
                else:
                    # resident GC texels: their first 32 bytes become an R4NREF record naming the PS2 package
                    # (TEX_REF_SELFKEY: native_ui.cpp image_key takes an unregistered record's own key after checking
                    # width / height / format against the TPL header, which stays the GC one)
                    old = (0, 0)
                    struct.pack_into('<8s6I', pay, rec, b'R4NREF\0\0', crc, fnv, gw, gh, gfmt, 0)
                    meta['selfkey_record'] = True
                if declare:
                    hdr = tpl_header(pay, gtpl, k)
                    struct.pack_into('<HH', pay, hdr, declare[1], declare[0])      # TPL image header: height, width
                    struct.pack_into('<II', pay, rec + 16, declare[0], declare[1])  # record: width, height
                    meta['declared_size'] = list(declare)
                done[rec] = key
                report['images'].append(dict(model=entry['name'], image=k, ps2_image=d, record=rec, old_key='%08x-%08x' % old, key=key,
                                             gc=dict(width=gw, height=gh, format=gfmt), ps2=meta,
                                             sha256=sha(data), bytes=len(data)))
            entry['ok'] = not entry.get('kept_gc_images')
            if entry.get('kept_gc_images'):
                entry['why'] = '; '.join(x['why'] for x in entry['kept_gc_images'])
        except (ValueError, KeyError, StopIteration) as ex:
            entry.update(ok=False, why=str(ex))
        report['models'].append(entry)
    del pay
    Path(a.out).write_bytes(bytes(dar))
    report.update(dar_out=a.out, dar_out_sha256=sha(bytes(dar)), tool_sha256=sha(Path(__file__).read_bytes()))
    if a.json:
        Path(a.json).write_text(json.dumps(report, indent=1))
    for e in report['models']:
        print('%-10s %-12s %s %s' % (e['kind'], e['name'], 'OK' if e.get('ok') else 'GC-TEX', e.get('why') or e.get('source')))
    gcv = sum(i['gc']['width'] * i['gc']['height'] for i in report['images'])
    print('images %d -> PS2 (VRAM %d bytes); GC texels %d' % (len(report['images']), sum(i['ps2']['vram_bytes'] for i in report['images']), gcv))


if __name__ == '__main__':
    main()
