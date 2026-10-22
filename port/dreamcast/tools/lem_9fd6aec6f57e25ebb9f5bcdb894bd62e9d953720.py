#!/usr/bin/env python3
"""Build a little-endian mirror of the GameCube data tree for the Dreamcast
game target.

--decode-rooms also writes decoded, converted st*/r*.arc sidecars using the
recovered offline decoder. They remain unqualified until --require coverage
passes for each sidecar. --native-rooms additionally emits qualified .dar DVD
containers for the native loader, retaining the original sound dispatch. A
rejected room has no .dar output (including removal of an older generated one).

--compact-static-rel removes unused PowerPC bodies only for the native modules
listed in the existing game registry/Makefile, after whole-file qualification.
It retains source archive slots, assets and sound. Use a separate output tree for
this selectable candidate; the default mirror remains the full reference.

    le_mirror.py <src-tree> <dst-tree> [--force] [--require <deps.txt>]

--require names a file listing the disc paths a boot fixture actually reads
(one per line, # comments); the run fails (exit 2) unless every part of every
listed file was converted completely or carries an explicit safe-raw contract
(ARAM sample bytes, text). Formats the fixture does not touch may stay raw.

The recovered game code overlays its structures straight onto the files it
reads (include/dvd.h DvdHeader, include/snd.h, include/snd_drv.h, the
tagged archives of include/global.h, mes.cpp, include/tpl.h, include/id_sys.h
...).  On the SH-4 those structures are little-endian, so every scalar the
game reads from a file has to be byte-swapped once, offline, with the layout
left untouched.  Each format gets a handler that walks the layout the game
headers describe; bytes no handler covers are copied as they are and listed
in <dst-tree>/le_mirror_report.json, which is how the boot log's next
failure is mapped to the next format to cover.

Two archive shapes carry almost everything:

* the DVD container (dvd.cpp): 32 bytes of magic, then 32-byte DvdHeader
  entries (type, size, dest, ofs, sndType, sndArg, sndNo) up to 0xFFFFFFFF,
  one nesting level (type 4);
* the tagged archive (read.cpp GetDataExt, global.h ArcFile, title.h
  TitleArc, card.h CardArc): u32 count, 12 bytes, u32 offsets[count],
  char tags[count][4]; the tag names the sub-file's format (TPL, MDT, UWF,
  EFF, LIT, SAT, ...).

The tree and the mirror are private game data; only this tool is committed.
"""
import fnmatch
import json
import math
import os
import re
from pathlib import Path
import struct
import sys

CONTAINER_MAGIC = b"\xca\xb6\xbe\x20" * 8
HEADER_TABLE = 0x400
ENTRY_SIZE = 0x20
END_OF_TABLE = 0xFFFFFFFF
SKIP_ENTRY = 0xFFFFFFFE
NESTED = 4

# Optional asset-builder observer sees the bounded original TPL before mutation.
TPL_OBSERVER = None
# Optional prepared-resource relocation observer: field, relative base, value.
OFFSET_OBSERVER = None
SEQUENCE_OBSERVER = None  # qualified EST/SST records, before optional native compaction
MODEL_OBSERVER = None  # qualified source BIN layout and UV index fields; offline only


class Swapper:
    """In-place byte swapper over a bytearray with double-swap protection and
    a bounds stack: every handler runs inside `bounded(off, size)` and can
    neither read nor swap a byte outside that region, so a corrupt or
    unexpected offset in one sub-file is an error for that sub-file only and
    never reaches a neighbour."""

    def __init__(self, data, label):
        self.data = data
        self.label = label
        self.done = bytearray(len(data))
        self.lo = 0
        self.hi = len(data)
        self._stack = []

    class _Bound:
        def __init__(self, sw, lo, hi):
            self.sw, self.lo, self.hi = sw, lo, hi

        def __enter__(self):
            sw = self.sw
            sw._stack.append((sw.lo, sw.hi))
            sw.lo, sw.hi = self.lo, self.hi
            return sw

        def __exit__(self, *exc):
            self.sw.lo, self.sw.hi = self.sw._stack.pop()
            return False

    def bounded(self, off, size):
        """Context manager narrowing the accessible region to [off, off+size),
        which must lie inside the current region."""
        if size < 0 or off < self.lo or off + size > self.hi:
            raise ValueError("%s: region %#x/%d outside the current region %#x..%#x" %
                             (self.label, off, size, self.lo, self.hi))
        return Swapper._Bound(self, off, off + size)

    def _check(self, off, size):
        if off < self.lo or off + size > self.hi:
            raise ValueError("%s: field at %#x/%d outside the region %#x..%#x" %
                             (self.label, off, size, self.lo, self.hi))

    def _mark(self, off, size):
        self._check(off, size)
        if any(self.done[off:off + size]):
            raise ValueError("%s: byte %#x swapped twice" % (self.label, off))
        for o in range(off, off + size):
            self.done[o] = 1

    def peek32(self, off):
        self._check(off, 4)
        return struct.unpack_from(">I", self.data, off)[0]

    def peek16(self, off):
        self._check(off, 2)
        return struct.unpack_from(">H", self.data, off)[0]

    def swapped(self, off):
        self._check(off, 1)
        return bool(self.done[off])

    def val32(self, off):
        """The original (big-endian) value of a u32 whether or not it has been swapped."""
        self._check(off, 4)
        return struct.unpack_from("<I" if self.done[off] else ">I", self.data, off)[0]

    def val16(self, off):
        self._check(off, 2)
        return struct.unpack_from("<H" if self.done[off] else ">H", self.data, off)[0]

    def u32(self, off):
        """Swap the u32 at off; returns its (big-endian, original) value."""
        self._mark(off, 4)
        v = struct.unpack_from(">I", self.data, off)[0]
        struct.pack_into("<I", self.data, off, v)
        return v

    def offset32(self, off, base):
        value = self.u32(off)
        if OFFSET_OBSERVER is not None and value:
            OFFSET_OBSERVER(self.label, off, base, value)
        return value

    def u16(self, off):
        self._mark(off, 2)
        v = struct.unpack_from(">H", self.data, off)[0]
        struct.pack_into("<H", self.data, off, v)
        return v

    def u32s(self, off, count):
        return [self.u32(off + 4 * i) for i in range(count)]

    def u16s(self, off, count):
        return [self.u16(off + 2 * i) for i in range(count)]

    f32 = u32

    def f32s(self, off, count):
        return self.u32s(off, count)


# ----------------------------------------------------------------- formats

def fmt_u32_array(sw, off, size, ctx):
    """A plain u32 table (bgm/bio4midi.hed: SndMem.bgm_file[no] file offsets)."""
    sw.u32s(off, size // 4)


def fmt_bio4str_hed(sw, off, size, ctx):
    """bgm/bio4str.hed: two stream blocks (snd.cpp SndInit, snd_sub3.cpp
    Snd_str_blk_init): u32 block_ofs[2]; block = {u32 num, shd_tbl_ofs,
    rit_ofs}; rit = SND_RIT[num]; shd table = u32 offsets (relative to the
    table) to SND_SHD records (include/snd_drv.h)."""
    blocks = sw.u32s(off, 2)
    for b in blocks:
        base = off + b
        num, shd_tbl, rit = sw.u32s(base, 3)
        max_shd = -1
        for i in range(num):
            r = base + rit + 0x10 * i
            shd_no = sw.u16(r)
            if shd_no != 0xFFFF:
                max_shd = max(max_shd, shd_no)
            sw.u16(r + 0x0C)
        tbl = base + shd_tbl
        seen = set()
        for i in range(max_shd + 1):
            o = sw.u32(tbl + 4 * i)
            if o in seen:
                continue
            seen.add(o)
            shd = tbl + o
            sw.u32s(shd, 8)             # flag .. offset
            sw.u16s(shd + 0x20, 0x2E)   # coef[16], coefR[16], gain, ps, yn1, yn2, lps, lyn1, lyn2


def fmt_doorse_hed(sw, off, size, ctx):
    """bgm/doorse.hed: SndDoorTbl {u32 file_ofs, num_ofs}; u16 count at
    num_ofs; u32 file offsets[count] at file_ofs (snd.cpp 1735/1753)."""
    file_ofs, num_ofs = sw.u32s(off, 2)
    count = sw.u16(off + num_ofs)
    sw.u32s(off + file_ofs, count)


def fmt_bgmtbl_dat(sw, off, size, ctx):
    """bgm/bgmtbl.dat: SndBgmTbl {u32 room_ofs, list_ofs}; u16 room id list
    (0xFFFF terminated) at list_ofs; u32 offsets[n] at room_ofs (relative to
    that array) to SndBgmRoom {u32 num; SndBgmEnt e[num]} (13 u32 each)."""
    room_ofs, list_ofs = sw.u32s(off, 2)
    n = 0
    while True:
        v = sw.u16(off + list_ofs + 2 * n)
        n += 1
        if v == 0xFFFF:
            break
    n -= 1
    offs = sw.u32s(off + room_ofs, n)
    seen = set()
    for o in offs:
        if o in seen:
            continue
        seen.add(o)
        room = off + room_ofs + o
        num = sw.u32(room)
        sw.u32s(room + 4, 13 * num)


def fmt_mdt(sw, off, size, ctx):
    """Message table (mes.cpp MessageData::getAddr): u32 languages, u32
    block_ofs[languages]; block = MesTblBlock {u32 x0, u32 count, u32
    ofs[count]} followed by the u16 code streams of its messages."""
    nlang = sw.u32(off)
    if nlang == 0 or nlang > 16:
        raise ValueError("%s: MDT with %d languages" % (sw.label, nlang))
    block_ofs = sw.u32s(off + 4, nlang)
    bounds = sorted(set(block_ofs)) + [size]
    for b in sorted(set(block_ofs)):
        end = bounds[bounds.index(b) + 1]
        blk = off + b
        sw.u32(blk)
        count = sw.u32(blk + 4)
        offs = sw.u32s(blk + 8, count)
        if count == 0:
            continue
        first = min(offs)
        # message streams: u16 codes from the first message to the block end
        n16 = ((end - b) - first) // 2
        sw.u16s(blk + first, n16)


def fmt_tpl(sw, off, size, ctx):
    """TPL texture palette (include/tpl.h): TEXPalette {u32 version, u32
    num, u32 desc_ofs}; TEXDescriptor[num] {u32 tex_ofs, u32 clut_ofs};
    TEXHeader {u16 h, u16 w, u32 fmt, u32 data, u32 wrapS, wrapT, minF,
    magF, f32 lod, 4 bytes}; CLUTHeader {u16 n, 2 bytes, u32 fmt, u32 data}.
    Image and palette data stay in their GameCube layout (the renderer
    converts them)."""
    if TPL_OBSERVER is not None:
        TPL_OBSERVER(sw.label, off, bytes(sw.data[off:off + size]), ctx)
    sw.u32(off)
    num = sw.u32(off + 4)
    desc = sw.offset32(off + 8, off)
    seen_tex = set()
    seen_clut = set()
    for i in range(num):
        d = off + desc + 8 * i
        tex, clut = (sw.offset32(d + j * 4, off) for j in range(2))
        if tex and tex not in seen_tex:
            seen_tex.add(tex)
            h = off + tex
            sw.u16s(h, 2)
            sw.u32(h + 4)
            sw.offset32(h + 8, off)
            sw.u32s(h + 12, 5)
        if clut and clut not in seen_clut:
            seen_clut.add(clut)
            c = off + clut
            sw.u16(c)
            sw.u32(c + 4)
            sw.offset32(c + 8, off)


def fmt_uwf(sw, off, size, ctx):
    """Id data table (include/id_sys.h, id_sys.cpp IDSystem::set):
    IdDataHeader {char version[5] "1.00"/"2.00", u8 num, 2 bytes}; entries
    from 0x08 (0x88 bytes for version 1, 0x8C for version 2): bytes, Vec pos
    at 0x14, Vec vtx[4] at 0x20, f32 sizeX/sizeY at 0x50, colour bytes, Vec
    rot, bytes, u32 ofs[6] (path0, path1, curve[4]; offsets from the table
    start). path0 = FuncPathData {s8 k, 6 bytes, s8 n, Vec pos[n]}, path1 =
    FuncPathWork {int k, int n, Vec alpha[n]}, curves = Hermite1 {s32 num,
    HermiteKey {f32 t, v, out, in}[num]}."""
    version = bytes(sw.data[off:off + 4])
    num = sw.data[off + 5]
    if version == b"1.00":
        stride, rot, ofs = 0x88, 0x5C, 0x70
    elif version == b"2.00":
        stride, rot, ofs = 0x8C, 0x60, 0x74
    else:
        raise ValueError("%s: UWF version %r" % (sw.label, version))
    seen = set()
    for i in range(num):
        e = off + 8 + stride * i
        sw.f32s(e + 0x14, 3 + 12 + 2)   # pos, vtx[4], sizeX, sizeY
        sw.f32s(e + rot, 3)
        refs = sw.u32s(e + ofs, 6)
        for k, r in enumerate(refs):
            if r == 0 or (k, r) in seen:
                continue
            seen.add((k, r))
            p = off + r
            if k == 0:
                n = sw.data[p + 7]
                sw.f32s(p + 8, 3 * n)
            elif k == 1:
                if sw.swapped(p):
                    continue
                n = sw.peek32(p + 4)
                if n > 256:
                    continue
                sw.u32s(p, 2)
                sw.f32s(p + 8, 3 * n)
            else:
                n = sw.u32(p)
                sw.f32s(p + 4, 4 * n)


def fmt_fnt(sw, off, size, ctx):
    """Font file (mes.cpp setupFont): MesFontFile {u32 tplOfs, u32 widthOfs,
    ...}; a TPL at tplOfs, glyph width bytes at widthOfs."""
    tpl_ofs, width_ofs = sw.u32s(off, 2)
    fmt_tpl(sw, off + tpl_ofs, size - tpl_ofs, ctx)


def fmt_snd_mram(sw, off, size, ctx, bgm=False):
    """Sound (ISS) block, the MRAM half of a container sound part
    (snd.cpp SndBlkInit, snd_sub3.cpp Snd_iss_blk_init, include/snd_drv.h,
    include/dolphin/syn.h): u32 block_ofs, u32 x4 (BGM blocks start at the
    header directly); header {u32 num, dls_ofs, sit_ofs, seq_ofs}; SIT[num]
    (0x18: u16 prog, bytes, u16 pitch_l/pitch_hi at 0x0A/0x0C, u16 flag at
    0x16); wavetable SND_WT_HDR {6 u32} then WTINST u16 note table, WTREGION
    (0x18), WTART (0x50), WTSAMPLE (0x10), WTADPCM (0x2E) sections in offset
    order; sequence table {u32 count, u32 ofs[count]} with raw MIDI bodies."""
    if bgm:
        hdr = off
    else:
        block_ofs = sw.u32(off)
        sw.u32(off + 4)
        hdr = off + block_ofs
    num, dls, sit, seq = sw.u32s(hdr, 4)
    end = off + size
    starts = sorted(x for x in (dls, sit, seq) if x)
    def section_end(o):
        later = [x for x in starts if x > o]
        return hdr + later[0] if later else end
    for i in range(num):
        r = hdr + sit + 0x18 * i
        sw.u16(r)
        sw.u16(r + 0x0A)
        sw.u16(r + 0x0C)
        sw.u16(r + 0x16)
    if dls:
        wt = hdr + dls
        wt_end = section_end(dls)
        x0, inst, rgn, art, smp, adpcm = sw.u32s(wt, 6)
        secs = sorted(x for x in (inst, rgn, art, smp, adpcm) if x)
        def wt_sec_end(o):
            later = [x for x in secs if x > o]
            return wt + later[0] if later else wt_end
        if inst:
            sw.u16s(wt + inst, (wt_sec_end(inst) - (wt + inst)) // 2)
        for k in range((wt_sec_end(rgn) - (wt + rgn)) // 0x18 if rgn else 0):
            r = wt + rgn + 0x18 * k
            sw.u16(r + 2)
            sw.u32s(r + 4, 5)
        if art:
            sw.u32s(wt + art, (wt_sec_end(art) - (wt + art)) // 4)
        for k in range((wt_sec_end(smp) - (wt + smp)) // 0x10 if smp else 0):
            r = wt + smp + 0x10 * k
            sw.u16s(r, 2)
            sw.u32s(r + 4, 2)
            sw.u16(r + 0x0C)
        for k in range((wt_sec_end(adpcm) - (wt + adpcm)) // 0x2E if adpcm else 0):
            sw.u16s(wt + adpcm + 0x2E * k, 23)
    if seq:
        t = hdr + seq
        count = sw.u32(t)
        sw.u32s(t + 4, count)



def motion_codec():
    # Reuse the byte-exact source codec behind build_real_motion_fixture.py.
    tools_path = str(Path(__file__).resolve().parents[3] / 'tools')
    if tools_path not in sys.path:
        sys.path.insert(0, tools_path)
    from motion import fcv
    return fcv


def fmt_fcv(sw, off, size, ctx):
    """Original compressed Hermite keys; preserve layout and numeric values."""
    fcv = motion_codec()
    sw._check(off, size)
    original = bytes(sw.data[off:off + size])
    try:
        motion = fcv.parse(original)
    except KeyError as exc:
        raise ValueError('unsupported FCV key type: ' + str(exc)) from exc
    if fcv.serialise(motion, '>') != original:
        raise ValueError('FCV source roundtrip differs; refusing conversion')
    native = fcv.serialise(motion, '<')
    if len(native) != size:
        raise ValueError('FCV conversion changed source layout size')
    sw._mark(off, size)
    sw.data[off:off + size] = native


def fmt_fcvseq(sw, off, size, ctx):
    """MotionSeqKey timing plus byte-sized sound/event fields; not EspSeqData."""
    fcv = motion_codec()
    sw._check(off, size)
    original = bytes(sw.data[off:off + size])
    sequence = fcv.parse_seq(original)
    if fcv.serialise_seq(sequence) != original:
        raise ValueError('motion sequence source roundtrip differs')
    count = sw.u16(off)
    for i in range(count):
        sw.u16(off + 4 + 4 * i)


def fmt_term_seq(sw, off, size, ctx):
    """op/opNN.das SEQ sub-files (Sscrn ss_term.cpp OpeMesTblInit / OpeSeqMove):
    TermSeq records {u16 x0, s16 x2, s32 time, s32 mesNo, s32 arg}, 16 bytes
    each; the record whose arg is -1 ends the op. The bytes after it are
    0 / 0xCD padding and stay as they are. Not the FCV MotionSeqKey layout
    that the SEQ tag names elsewhere."""
    count = 0
    while True:
        p = off + 16 * count
        if p + 16 > off + size:
            raise ValueError('term sequence has no end record (arg -1)')
        arg = struct.unpack_from('>i', sw.data, p + 12)[0]
        sw.u16s(p, 2)
        sw.u32s(p + 4, 3)
        count += 1
        if arg == -1:
            break
    tail = bytes(sw.data[off + 16 * count:off + size])
    if any(b not in (0, 0xCD) for b in tail):
        raise ValueError('term sequence trailing bytes are not 0 / 0xCD padding')


def fmt_itm(sw, off, size, ctx):
    """item_model.cpp: source id table and table-relative BIN/TPL pairs."""
    version = sw.u32(off)
    oi, ob, ot = (sw.offset32(off + 4*i, off) for i in range(1,4))
    if version != 3:
        raise ValueError('unsupported item model pack version')
    bases = [off + v for v in (oi, ob, ot)]
    if len(set(bases)) != 3 or min(bases) < off + 16:
        raise ValueError('invalid item model tables')
    limits = sorted(bases) + [off + size]
    ends = {a: b for a, b in zip(limits, limits[1:])}
    ids = bases[0]
    with sw.bounded(ids, ends[ids] - ids):
        count = sw.u32(ids)
        sw._check(ids + 4, count * 8)
        for i in range(count):
            p = ids + 4 + i * 8
            if sw.u16(p) >= 256:
                raise ValueError('item model id exceeds source registry')
            sw.u16(p + 2)
            sw.u32(p + 4)
    for base, handler in zip(bases[1:], (fmt_bin, fmt_tpl)):
        with sw.bounded(base, ends[base] - base):
            if sw.u32(base) != count:
                raise ValueError('item model table counts differ')
            targets = [base + sw.offset32(base + 4 + 4*i, base) for i in range(count)]
            starts = sorted(set(targets))
            for i, start in enumerate(starts):
                if start < base + 4 + count * 4:
                    raise ValueError('item model payload overlaps its offset table')
                end = starts[i + 1] if i + 1 < len(starts) else ends[base]
                with sw.bounded(start, end - start):
                    raw = handler(sw, start, end - start, ctx + '/item')
                if raw:
                    raise ValueError('incomplete item model: ' + str(raw))


def fmt_etm(sw, off, size, ctx):
    """EtcModel.cpp GetEtcAddr: size includes each 64-byte named header.

    Unknown member formats remain explicit blockers for the entire room.
    Never promote an archive merely because its directory was converted.
    """
    sw._check(off, 32)
    count = sw.u32(off)
    cursor = off + 32
    raw = []
    for i in range(count):
        sw._check(cursor, 64)
        # GetEtcAddr advances by this member-relative end offset. Compaction
        # inside a member must rebase its size as well as its payload offsets.
        length = sw.offset32(cursor, cursor)
        if length < 64:
            raise ValueError('etc member length does not include its header')
        sw._check(cursor, length)
        name = bytes(sw.data[cursor + 32:cursor + 64])
        if b'\0' not in name:
            raise ValueError('unterminated etc member name')
        name = name.split(b'\0', 1)[0].decode('ascii')
        handler = {'.bin': fmt_bin, '.tpl': fmt_tpl, '.eff': fmt_eff,
                   '.fcv': fmt_fcv, '.seq': fmt_fcvseq}.get(
            os.path.splitext(name)[1].lower())
        if handler is None:
            raw.append('etc member ' + name)
        else:
            with sw.bounded(cursor + 64, length - 64):
                pending = handler(sw, cursor + 64, length - 64, ctx + '/' + name)
            raw.extend(name + ': ' + reason for reason in (pending or []))
        cursor += length
    return raw


def fmt_blk(sw, off, size, ctx):
    """block.h / block.cpp: authored residency links, areas and working sets."""
    sw._check(off, 24)
    if sw.data[off:off + 4] != b'BLK\0' or sw.u16(off + 4) != 0x100:
        raise ValueError('unsupported block residency header')
    blocks = sw.data[off + 7]
    areas, connects = sw.u16s(off + 8, 2)
    offsets = sw.u32s(off + 12, 3)
    if blocks > 32:
        raise ValueError('block count exceeds source working-set bitmap')
    ranges = sorted((off + o, n * stride) for o, n, stride in
                    zip(offsets, (blocks, areas, connects), (12, 56, 20)) if n)
    end = off + 24
    for start, length in ranges:
        if start < end:
            raise ValueError('overlapping block residency tables')
        sw._check(start, length)
        end = start + length
    def block_refs(p, n):
        if any(v != 255 and v >= blocks for v in sw.data[p:p + n]):
            raise ValueError('invalid block residency reference')
    for i in range(blocks):
        block_refs(off + offsets[0] + 12 * i + 4, 8)
    for i in range(areas):
        p = off + offsets[1] + 56 * i
        sw.u32(p)  # runtime OT link; source overwrites it during registration
        if sw.data[p + 5] not in (0, 1, 2, 3):
            raise ValueError('unsupported block area type')
        sw.u16(p + 6)
        sw.f32s(p + 8, 11)
        if sw.data[p + 55] >= 8 or sw.data[p + 54] >= connects:
            raise ValueError('invalid block area priority or connection')
    for i in range(connects):
        p = off + offsets[2] + 20 * i
        if sw.data[p] & 1:
            if sw.data[p + 1] >= blocks:
                raise ValueError('invalid connection owner block')
            block_refs(p + 4, 16)
    # Signed byte block lists (including -1), flags and ordering stay unchanged.


def fmt_tex(sw, off, size, ctx):
    """texture.h TexData and texture.cpp cTexSys::DataLoad."""
    version, oi, ot, oa = sw.u32s(off, 4)
    if version != 3:
        raise ValueError('unsupported TexData version')
    ids = off + oi
    count = sw.u32(ids)
    for i in range(count):
        sw.u16s(ids + 4 + i * 8, 2)
        sw.u32(ids + 8 + i * 8)
    if not count:
        return
    tables = []
    for rel in (ot, oa):
        base = off + rel
        if sw.u32(base) != count:
            raise ValueError('TexData table counts differ')
        tables.append([base + v for v in sw.u32s(base + 4, count)])
    for t in set(tables[0]):
        fmt_tpl(sw, t, off + size - t, ctx + '/tpl')
    for a in set(tables[1]):
        sw.u16s(a, 5)  # TexAnm dimensions/centre/frame count; rest bytes


def fmt_shd(sw, off, size, ctx):
    """shadow.h ShdHeader/ShdEntry; table-relative ModelData."""
    sw._check(off, 16)
    if sw.data[off] > 0x41:
        raise ValueError('unsupported shadow version')
    count = sw.u16(off + 2)
    table = off + sw.u32(off + 4)
    sw._check(off + 16, count * 72)
    models = []
    for i in range(count):
        p = off + 16 + i * 72
        sw.f32s(p, 9)
        models.append(sw.data[p + 36])
    if not models:
        return
    offsets = sw.u32s(table, max(models) + 1)
    starts = sorted(set(table + offsets[m] for m in models))
    for i, start in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else off + size
        with sw.bounded(start, end - start):
            raw = fmt_bin(sw, start, end - start, ctx + '/model')
        if raw:
            raise ValueError('incomplete shadow model: ' + str(raw))


def fmt_fse(sw, off, size, ctx):
    """flr_at.h; a zero header is the source reader's empty sentinel."""
    sw._check(off, 16)
    if not any(sw.data[off:off + 16]):
        return
    if sw.data[off:off + 4] != b'FSE\0' or sw.u16(off + 4) != 0x103:
        raise ValueError('unsupported floor attribute header')
    count = sw.u16(off + 6)
    sw._check(off + 16, count * 132)
    for i in range(count):
        p = off + 16 + i * 132
        a = p + 20
        if sw.data[a + 1] not in (0, 1, 2, 3):
            raise ValueError('unsupported floor area type')
        sw.u16(a + 2)
        sw.f32s(a + 4, 11)
        if sw.data[p + 1] == 2:
            sw.u32s(p + 72, 2)
            sw.u16s(p + 80, 2)
            sw.u32(p + 84)
        elif sw.data[p + 1] not in (0, 1, 3):
            raise ValueError('unsupported floor attribute type')


def fmt_osd(sw, off, size, ctx):
    """Only the observed all-zero OSD is endian-invariant and qualified.

    ReadAreaData retains its pointer; the recovered source has no dereference.
    A nonzero/new-sized variant still needs a source consumer/layout contract.
    """
    sw._check(off, size)
    if size != 1408 or any(sw.data[off:off + size]):
        raise ValueError('nonzero or unknown OSD requires source layout recovery')


def fmt_empty_evs(sw, off, size, ctx):
    """Only the bounded empty room EVS; nonempty event bundles stay unsupported.

    game.cpp passes this to EventMgr::SetEvs (event.cpp). SetEvs forms the
    table pointer even with num == 0, but neither dereferences nor retains it.
    Canonicalize that unused offset to an in-bounds empty table, rather than
    propagating the observed r101 0xCD debug-fill pointer. No event is registered
    and consequently there is no EVS-owned cleanup or retained event pointer.
    """
    sw._check(off, size)
    if size != 32 or sw.peek32(off) != 0:
        raise ValueError('nonempty or unknown EVS requires source layout recovery')
    tail = bytes(sw.data[off + 4:off + 32])
    if tail not in (bytes(28), b'\xcd' * 28):
        raise ValueError('empty EVS has unqualified header/padding')
    sw.u32(off)
    sw.u32(off + 4)
    struct.pack_into('<I', sw.data, off + 4, 8)


def fmt_sce_at(sw, off, size, ctx):
    """sce_at.h SceAtWork: shared trigger header plus typed source payload."""
    sw._check(off, 16)
    tag = bytes(sw.data[off:off + 4])
    version = sw.u16(off + 4)
    if (tag, version) not in ((b'AEV\0', 0x104), (b'ITA\0', 0x105)):
        raise ValueError('unsupported scenario/item trigger header')
    count = sw.u16(off + 6)
    sw._check(off + 16, count * 156)
    raw = []
    def null_pointer(p):
        if sw.u32(p):
            raise ValueError('scenario file contains a runtime/PPC pointer')
    for i in range(count):
        p = off + 16 + i * 156
        sw.u32(p)  # replaced by source OT registration
        fmt_area(sw, p + 4)
        kind = sw.data[p + 53]
        if sw.data[p + 68] >= 16:
            raise ValueError('scenario ordering-table index outside source table')
        sw.u32(p + 60)
        null_pointer(p + 64)
        null_pointer(p + 76)
        sw.u16(p + 80)
        d = p + 92
        if kind in (0, 2, 6, 7, 20):
            # Normal hit-model list or source-installed callback, never an
            # executable pointer copied from the GameCube data file.
            if any(sw.data[d:d + 64]):
                raw.append('scenario%d runtime work is nonzero' % i)
        elif kind == 1:  # SceAtDoor
            sw.f32s(d, 4)
            null_pointer(d + 20)
            sw.u32(d + 28)
        elif kind == 3:  # SceAtItem
            sw.f32s(d, 3)
            null_pointer(d + 12)
            sw.f32s(d + 16, 3)
            sw.u16s(d + 28, 4)
            sw.u16(d + 42)
            sw.f32s(d + 44, 4)
        elif kind == 4:
            sw.u16(d + 2)
        elif kind == 5:  # SceAtMesData
            sw.u16s(d, 2)
            sw.u16(d + 6)
        elif kind == 8:
            sw.u32(d)
        elif kind == 11:  # runtime SAT/EAT objects plus authored collision attrs
            null_pointer(d)
            null_pointer(d + 4)
            sw.u32s(d + 12, 4)
        elif kind == 13:
            sw.u32(d)
            null_pointer(d + 4)
        elif kind == 16:
            sw.f32s(d, 4)
        elif kind == 17:
            sw.u16s(d, 2)
        else:
            raw.append('scenario%d type%d payload' % (i, kind))
    return raw


def fmt_rtp(sw, off, size, ctx):
    """route_ck.h: keep the authored graph and signed-byte next-hop matrix."""
    sw._check(off, 24)
    if sw.data[off:off + 4] != b'2RTP':
        raise ValueError('unsupported route point header')
    sw.u16(off + 4)
    count = sw.u16(off + 6)
    links, hops = sw.u16s(off + 8, 2)
    points, lines, nexts = [off + v for v in sw.u32s(off + 12, 3)]
    if count > 128 or hops != count * count:
        raise ValueError('route next-hop dimensions disagree')
    ranges = sorted((a, n) for a, n in ((points, count*16), (lines, links*4), (nexts, hops)) if n)
    end = off + 24
    for start, n in ranges:
        if start < end:
            raise ValueError('overlapping route tables')
        sw._check(start, n)
        end = start + n
    for i in range(count):
        p = points + i * 16
        sw.f32s(p, 3)
        first, n = sw.u16s(p + 12, 2)
        if first + n > links:
            raise ValueError('route point link range outside table')
    for i in range(links):
        target, _ = sw.u16s(lines + i * 4, 2)
        if target != 65535 and target >= count:
            raise ValueError('invalid route link target')
    if any(v != 255 and v >= count for v in sw.data[nexts:nexts + hops]):
        raise ValueError('invalid route next hop')


def fmt_stb(sw, off, size, ctx):
    """snd.h SndRoomHdr: reverb, byte curve selectors, shared numeric curves."""
    sw._check(off, 576)
    for i in range(2):
        sw.u16s(off + i * 32, 4)
        sw.f32s(off + i * 32 + 8, 6)
    offsets = sw.u32s(off + 64, 128)
    targets = sorted(set(off + v for v in offsets if v))
    for start in targets:
        if start < off + 576:
            raise ValueError('sound curve overlaps room header')
        sw._check(start, 1)
    limits = dict(zip(targets, targets[1:] + [off + size]))
    selectors = set(off + v for v in offsets[:32] if v)
    curves = set(off + v for v in offsets[32:] if v)
    if selectors & curves:
        raise ValueError('sound selector aliases numeric curve')
    for start in selectors:
        with sw.bounded(start, limits[start] - start):
            sw._check(start, 6)  # all signed byte selectors, -1 means none
    for start in curves:
        with sw.bounded(start, limits[start] - start):
            count = sw.u32(start)
            sw.f32(start + 4)
            sw._check(start + 8, count * 8)
            for i in range(count):
                p = start + 8 + 8 * i
                sw.f32(p)
                sw.u16s(p + 4, 2)  # val read numerically, then cast by snd.cpp


def fmt_ese(sw, off, size, ctx):
    """snd.h SeAtHead/SeAt; timers, repeats and source sound identifiers."""
    sw._check(off, 16)
    if sw.data[off:off + 4] != b'ESE\0' or sw.u16(off + 4) != 0x100:
        raise ValueError('unsupported sound emitter header')
    count = sw.u16(off + 6)
    sw._check(off + 16, count * 44)
    for i in range(count):
        p = off + 16 + i * 44
        sw.u16(p + 2)
        sw.f32s(p + 4, 3)
        sw.u16s(p + 16, 10)


def fmt_dse(sw, off, size, ctx):
    """snd.cpp SndDoorSe: destination room plus five source door sound ids."""
    count = sw.u32(off)
    sw._check(off + 4, count * 12)
    sw.u16s(off + 4, count * 6)


def fmt_esl(sw, off, size, ctx):
    """stage.cpp readEmList -> em_set.h EmListData, at most 256 records.

    Files have no header/count; the opening list contains 255 records. Keep
    byte flags, IDs, character selectors and reserved bytes unchanged. Source
    room IDs are numeric u16 values, not a pair of native-order byte fields.
    """
    if not size or size > 0x2000 or size % 0x20:
        raise ValueError('invalid ESL record extent for source enemy list')
    for p in range(off, off + size, 0x20):
        sw.u32(p + 4)       # cEm flags
        sw.u16(p + 8)       # HP
        sw.u16s(p + 12, 8)  # signed position/rotation, room, signed guard radius


def fmt_emi(sw, off, size, ctx):
    """embarrel.h EmiData/Entry; reject extra work with no established layout."""
    count = sw.u32(off)
    sw.u32(off + 4)
    sw._check(off + 8, count * 64)
    raw = []
    for i in range(count):
        p = off + 8 + i * 64
        sw.f32s(p + 4, 4)
        if any(sw.data[p + 20:p + 64]):
            raw.append('enemy info%d additional work' % i)
    return raw


def fmt_dra(sw, off, size, ctx):
    """Tools/t_dr.cpp DrHeader; only the authored empty list is qualified."""
    sw._check(off, 16)
    if sw.data[off:off + 4] != b'DRA\0' or sw.u16(off + 4) != 0x100:
        raise ValueError('unsupported dynamic read area header')
    areas, files, _ = sw.u16s(off + 6, 3)
    sw.u32(off + 12)
    if areas or files:
        return ['dynamic read areas and file names']


def fmt_ets(sw, off, size, ctx):
    """EtcModelListSet / EtcSetData: count, source ids, angles and positions."""
    count = sw.u16(off)
    sw._check(off + 16, count * 40)
    for i in range(count):
        p = off + 16 + i * 40
        ident, slot = sw.u16s(p, 2)
        if ident >= 0x68 or slot >= 0x40:
            raise ValueError('invalid source etc model id or slot')
        # +4..+15 is opaque pad_4 in the recovered consumer, never read by
        # EtcModelSet/Et*_init. Retain it; do not invent an applied scale.
        sw.f32s(p + 16, 6)


def fmt_area(sw, off):
    """area.h AreaData, common to source effect and light trigger volumes."""
    sw._check(off, 48)
    if sw.data[off + 1] not in (0, 1, 2, 3):
        raise ValueError('unsupported source area type')
    sw.u16(off + 2)
    sw.f32s(off + 4, 11)


def fmt_ear(sw, off, size, ctx):
    """espgen.h SstArea/SstAreaEnt; preserve source effect display flags."""
    count, version = sw.u32s(off, 2)
    sw._check(off + 16, count * 152)
    for i in range(count):
        p = off + 16 + i * 152
        fmt_area(sw, p + 4)
        sw.u32(p + 52)
        # The remaining record bytes are opaque padding in SstAreaEnt.


def fmt_sar(sw, off, size, ctx):
    """light_area.cpp LightAreaHed/Data; class ids and signed power are bytes."""
    count = sw.u32(off)
    sw._check(off + 16, count * 216)
    for i in range(count):
        fmt_area(sw, off + 16 + i * 216 + 4)


def fmt_sequence(sw, off, size, ctx):
    """esp.h EspSeqData/EspGenWork, with source-semantic parameter word lanes."""
    raw = []
    count = sw.u16(off)
    sw.u16(off + 8)
    sw.f32s(off + 12, 6)
    sw._check(off + 48, count * 300)
    for i in range(count):
        p = off + 48 + i * 300
        sw.u16(p + 4)
        sw.u32(p + 8)
        sw.f32s(p + 12, 36)
        sw.f32s(p + 160, 4)
        sw.u16s(p + 176, 6)
        sw.u16(p + 190)
        # EspGenPrm native halfword/byte views retain each source word lane.
        sw.u32s(p + 204, 2)
        sw.u32(p + 212)
        sw.f32s(p + 216, 9)
        sw.u16s(p + 272, 4)
        sw.f32s(p + 280, 3)
    if SEQUENCE_OBSERVER is not None:
        SEQUENCE_OBSERVER(sw.label, off, bytes(sw.data[off:off + size]), ctx)
    return raw


def fmt_eff_path(sw, off, size, ctx):
    """path.h Path/PathVtx used by EspGetPathAddr and PathGetPos[Em].

    Keep the 12 byte-sized part/weight/padding lanes unchanged. These are
    distance poly-lines, not id_sys FuncPath spline data or EST/SST sequences.
    """
    count = sw.u16(off)
    if count < 2:
        raise ValueError('effect path needs at least two vertices')
    sw._check(off + 4, count * 40)
    previous = 0.0
    for i in range(count):
        p = off + 4 + i * 40
        values = struct.unpack_from('>7f', sw.data, p)
        if not all(math.isfinite(v) for v in values):
            raise ValueError('non-finite effect path vertex')
        distance = values[6]
        if distance < previous or (i == 0 and distance != 0):
            raise ValueError('invalid effect path distances')
        if sw.data[p + 31] > 3:
            raise ValueError('effect path weight count exceeds source arrays')
        sw.f32s(p, 7)
        previous = distance
    if previous <= 0:
        raise ValueError('effect path has no positive length')


def fmt_eff(sw, off, size, ctx):
    """Effect data file, version 0xB (src/game/eff_sys.cpp EffData; the ID
    layout system reads the same block through src/game/id_tex.cpp
    IdTexDataLoad): twelve u32 offsets from the block start, then
      - the texture id table (TexIdTbl: u32 num, {u16 id, u16 x2, u32 x4}[num]),
      - the TPL offset table (TexOfsTbl: u32 num, u32 ofs[num] relative to the
        table) whose targets are TPL palettes (fmt_tpl; a target shared by
        several entries is converted once),
      - the animation offset table (same shape) whose targets are EspAnmData
        records (u16 Width, Height, s16 Cx, Cy, u16 Frames at +8, bytes at
        +0xA..+0xF, then the byte pattern / frame-time tables, untouched),
      - the effect model id table and the model offset table (EffEfmEnt: five
        u32 from the entry, model / TPL / motion bodies relative to it) whose
        BIN/TPL/motion bodies use the existing source codecs; shape extras
        remain explicit incomplete coverage,
      - EST/SST sequences and Path/PathVtx distance paths through their
        source-specific codecs (unsupported sequence records stay explicit).
    Image and palette data keep their GameCube encoding (fmt_tpl contract)."""
    hdr = [sw.u32(off)] + [sw.offset32(off + 4*i, off) for i in range(1, 12)]
    (version, ofs_tex_id, ofs_est_list, ofs_sst_list, ofs_path_list, ofs_efm_id,
     ofs_tpl, ofs_anm, ofs_est_data, ofs_sst_data, ofs_path_data, ofs_efm) = hdr
    if version != 0xB:
        raise ValueError("%s: EFF version %#x, expected 0xB" % (ctx, version))
    raw = []

    def id_table(o):
        n = sw.u32(o)
        ids = []
        for i in range(n):
            e = o + 4 + 8 * i
            ids.append(sw.u16(e))
            sw.u16(e + 2)
            sw.u32(e + 4)
        return ids

    def ofs_table(o):
        n = sw.u32(o)
        return [o + sw.offset32(o + 4 + 4*i, o) for i in range(n)]

    tex_ids = id_table(off + ofs_tex_id)
    # The game forms the table pointers unconditionally but dereferences them
    # only inside the per-id loops; a file without textures carries offset 0
    # (which would alias the header) and is left alone the same way.
    if tex_ids:
        if not (ofs_tpl and ofs_anm):
            raise ValueError("%s: %d texture ids but no TPL / animation table" % (ctx, len(tex_ids)))
        tpls = ofs_table(off + ofs_tpl)
        anms = ofs_table(off + ofs_anm)
    else:
        tpls = anms = []
    if not (len(tex_ids) == len(tpls) == len(anms)):
        raise ValueError("%s: texture tables disagree (%d ids, %d TPLs, %d animations)" %
                         (ctx, len(tex_ids), len(tpls), len(anms)))
    seen_tpl = set()
    for i, t in enumerate(tpls):
        if t in seen_tpl:
            continue  # shared reference: one conversion, both entries resolve to it
        seen_tpl.add(t)
        fmt_tpl(sw, t, off + size - t, ctx + "/tpl%d" % i)
    seen_anm = set()
    for i, a in enumerate(anms):
        if a in seen_anm:
            continue
        seen_anm.add(a)
        width, height, cx, cy, frames = sw.u16s(a, 5)
        if frames == 0:
            raise ValueError("%s: animation %d has no frames" % (ctx, i))
        n_desc = sw.val32(tpls[i] + 4)
        if n_desc != frames:
            raise ValueError("%s: animation %d frames %d != TPL images %d" % (ctx, i, frames, n_desc))
    efm_ids = id_table(off + ofs_efm_id) if ofs_efm_id else []
    if efm_ids:
        if not ofs_efm:
            raise ValueError("%s: %d effect model ids but no model table" % (ctx, len(efm_ids)))
        efms = ofs_table(off + ofs_efm)
        if len(efm_ids) != len(efms):
            raise ValueError("%s: effect model tables disagree" % ctx)
        for i, e in enumerate(sorted(set(efms))):
            x0, o_model, o_tpl, o_mot, o_x = [sw.u32(e)] + [sw.offset32(e + 4*i, e) for i in range(1, 5)]
            if not o_model or not o_tpl:
                raise ValueError('effect model has no model or texture body')
            end = min(p for p in [off + size] + efms +
                      [off + v for v in hdr[1:] if v] if p > e)
            bodies = [(e + v, kind) for v, kind in
                      ((o_model, 'model'), (o_tpl, 'tpl'), (o_mot, 'motion'), (o_x, 'shape')) if v]
            bodies.sort()
            for j, (start, kind) in enumerate(bodies):
                limit = bodies[j + 1][0] if j + 1 < len(bodies) else end
                if start < e + 20 or limit <= start:
                    raise ValueError('overlapping effect model bodies')
                with sw.bounded(start, limit - start):
                    if kind in ('model', 'tpl'):
                        pending = (fmt_bin if kind == 'model' else fmt_tpl)(
                            sw, start, limit - start, ctx + '/efm%d/%s' % (i, kind))
                        raw.extend('efm%d %s' % (i, item) for item in (pending or []))
                    elif kind == 'motion':
                        motions = sorted(set(ofs_table(start)))
                        for k, motion in enumerate(motions):
                            stop = motions[k + 1] if k + 1 < len(motions) else limit
                            if motion < start + 4 + 4 * sw.val32(start):
                                raise ValueError('effect motion overlaps table')
                            with sw.bounded(motion, stop - motion):
                                fmt_fcv(sw, motion, stop - motion, ctx + '/efm%d/motion%d' % (i, k))
                    else:
                        raw.append('efm%d shape body' % i)
    for name, o_list, o_data in (("est", ofs_est_list, ofs_est_data), ("sst", ofs_sst_list, ofs_sst_data),
                                 ("path", ofs_path_list, ofs_path_data)):
        if not o_list:
            continue
        ids = id_table(off + o_list)
        if not ids:
            continue
        if not o_data:
            raise ValueError('effect list has no data table')
        blocks = ofs_table(off + o_data)
        if len(blocks) != len(ids):
            raise ValueError('effect sequence table counts differ')
        starts = sorted(set(blocks))
        section_end = min([off + value for value in hdr[1:] if value > o_data] + [off + size])
        for i, start in enumerate(starts):
            end = starts[i + 1] if i + 1 < len(starts) else section_end
            if start < off + o_data + 4 + 4 * len(blocks) or end > section_end:
                raise ValueError('effect data overlaps table or next section')
            with sw.bounded(start, end - start):
                if name == 'path':
                    fmt_eff_path(sw, start, end - start, ctx + '/path')
                else:
                    raw.extend(fmt_sequence(sw, start, end - start, ctx + '/' + name))
    return raw



def fmt_roominfo(sw, off, size, ctx):
    """debug/roomInfo.dat (src/game/room_jmp.cpp cRoomJmp, include/room_jmp.h
    CRoomInfo): u32 stage count, u32 ofs[count] from the table start (0 = no
    table), and per stage u32 record count followed by 0x20-byte records
    {u16 flag, u16 roomNo (stage << 8 | room), Vec pos, f32 angle, u32 name,
    scr, soft string offsets from the table start}. The strings stay raw.
    getIndexNum reads the record count's low byte and the record's `room`
    byte through a union; the Dreamcast build of those accessors follows the
    swapped layout (room_jmp.cpp / room_jmp.h)."""
    count = sw.u32(off)
    offs = sw.u32s(off + 4, count)
    for stage, o in enumerate(offs):
        if o == 0:
            continue
        base = off + o
        n = sw.u32(base)
        for i in range(n):
            r = base + 4 + 0x20 * i
            sw.u16s(r, 2)
            sw.f32s(r + 4, 4)
            sw.u32s(r + 0x14, 3)



def fmt_rel(sw, off, size, ctx):
    """REL module header (include/main_sub.h OSModuleHeader, the SDK
    OSModuleInfo + OSModuleHeader v3): sixteen u32 words (id, link, section
    count / table offset, name offset / size, version, bss size, relocation
    / import offsets, prolog / epilog / unresolved section and offsets ...).
    The code and relocation bodies are PowerPC and stay raw: on the Dreamcast
    the module is compiled into the image and OSLink binds the header's entry
    points to it (platform/modules.cpp)."""
    sw.u32s(off, 16)
    return ["PowerPC code, data and relocations (static module in the image)"]


def fmt_cns(sw, off, size, ctx):
    """cons.cpp ConsRoom: count, (count >> 5)+1 bitmap words, values."""
    count = sw.u32(off)
    words = (count >> 5) + 1
    sw._check(off + 4, 4 * (words + count))
    sw.u32s(off + 4, words + count)


def fmt_sat(sw, off, size, ctx):
    """atari.h/cSat::operator=: retain native source layout and block graph.

    SAT and EAT share this format but remain separate source resources/managers.
    Attribute words use the native AtPoly half-word view in include/at_sub.h.
    No coordinate scaling, welding, reordering or hierarchy rebuilding occurs.
    """
    sw._check(off, 4)
    version = sw.data[off]
    if version != 0xFF and version & 0x80:
        # The shipped archive's byte 1 counts offset entries (same format used
        # by convert_sat.py); the runtime indexes them with the source type.
        count = sw.data[off + 1]
        if count == 0:
            raise ValueError('empty multi-SAT header')
        offsets = sw.u32s(off + 4, count)
        if any(x < 4 + 4 * count or x + 20 > size for x in offsets):
            raise ValueError('SAT section offset outside archive')
        unique = sorted(set(offsets))
        for i, start in enumerate(unique):
            end = unique[i + 1] if i + 1 < len(unique) else size
            with sw.bounded(off + start, end - start):
                _fmt_sat_file(sw, off + start, end - start)
    else:
        _fmt_sat_file(sw, off, size)


def _fmt_sat_file(sw, off, size):
    nv, nn, ne, unused, np, nf, ns, nw, nb = sw.u16s(off + 2, 9)
    if np > 0x1FFF or nf + ns + nw != np:
        raise ValueError('invalid SAT polygon counts')
    vectors = off + 20
    sw._check(vectors, (nv + nn + ne) * 12 + np * 20)
    sw.f32s(vectors, (nv + nn + ne) * 3)
    polygons = vectors + (nv + nn + ne) * 12
    for i in range(np):
        p = polygons + i * 20
        indices = sw.u16s(p, 7)
        if any(x >= nv for x in indices[:3]) or indices[3] >= nn or any(x >= ne for x in indices[4:]):
            raise ValueError('SAT polygon index outside source table')
        sw.u32(p + 16)
    first = polygons + np * 20
    todo = [first] if nb else []
    visited = set()
    while todo:
        p = todo.pop()
        if p in visited:
            raise ValueError('shared or cyclic SAT block')
        if len(visited) >= nb or p < first:
            raise ValueError('SAT block count or offset invalid')
        sw._check(p, 36)
        visited.add(p)
        sw.f32s(p, 6)
        floor, slope, wall, flags = sw.u16s(p + 24, 4)
        following = sw.u32(p + 32)
        count = floor + slope + wall
        if flags & 1:
            if count:
                raise ValueError('SAT parent contains polygon indices')
            todo.append(p + 36)
        else:
            indices = sw.u16s(p + 36, count)
            if any(x >= np for x in indices):
                raise ValueError('SAT leaf polygon outside source table')
        if following:
            if following < 36 or following & 3:
                raise ValueError('invalid SAT next relative offset')
            todo.append(p + following)
    if len(visited) != nb:
        raise ValueError('SAT block count does not match graph')

def fmt_light_paths(sw, off, size, ctx):
    """ArcFile.ofs_3C: light.h LightPathHeader, despite its generic BIN tag."""
    sw._check(off, 4)
    count = sw.data[off]
    offsets = sw.u32s(off + 4, count)
    for relative in offsets:
        if not relative:
            continue  # source getPathPtr returns NULL
        if relative < 4 + 4 * count or relative >= size:
            raise ValueError('light path offset outside data')
        if 0xFF not in sw.data[off + relative:off + size]:
            raise ValueError('unterminated light brightness path')


def fmt_cam(sw, off, size, ctx):
    """cam_ctrl.h and CameraControl::calcAddr; file-relative links stay offsets."""
    sw._check(off, 16)
    version = bytes(sw.data[off:off + 4])
    if version == b'EMPT':
        return  # cameraDataVersion rejects the sentinel before reading counts
    if version not in (b'B402', b'B403', b'B404'):
        raise ValueError('unsupported camera data version %r' % version)
    cuts, areas, lerps = sw.data[off + 4:off + 7]
    recs = off + 16
    infos = recs + areas * 16
    keys = infos + areas * 48
    transitions = keys + cuts * 52
    sw._check(recs, areas * 64 + cuts * 52 + lerps * 16)
    seen = set()

    def array(relative, count, width):
        if count == 0:
            return
        p = off + relative
        sw._check(p, count * width)
        if count and p < transitions + lerps * 16:
            raise ValueError('camera key array overlaps record table')
        for i in range(count):
            field = p + i * width
            if (field, width) in seen:
                continue
            (sw.u32 if width == 4 else sw.u16)(field)
            seen.add((field, width))

    for i in range(areas):
        area, cut = sw.u32s(recs + i * 16 + 8, 2)
        if not infos <= off + area < keys or (off + area - infos) % 48:
            raise ValueError('camera area link outside area records')
        if cut and (not keys <= off + cut < transitions or (off + cut - keys) % 52):
            raise ValueError('camera cut link outside cut records')
        p = infos + i * 48
        sw.f32(p + 4)
        sw.f32s(p + 32, 2)
        count, points = sw.u32s(p + 40, 2)
        array(points, count * 3, 4)
    for i in range(cuts):
        p = keys + i * 52
        sw.f32s(p + 4, 3)
        frames = sw.u32(p + 16)
        sw.f32(p + 20)
        count = sw.u32(p + 32)
        pos, at, roll, fovy = sw.u32s(p + 36, 4)
        # Only Hermite camera types consume frame times. Shoulder cuts retain
        # stale debug pointers in this unused field in the original files.
        if sw.data[p + 2] in (6, 7) and frames:
            array(frames, count, 2)
        for target, stride in [(pos, 3), (at, 3), (roll, 1), (fovy, 1)]:
            array(target, count * stride, 4)
    for i in range(lerps):
        sw.u32(transitions + i * 16 + 8)


def fmt_lit(sw, off, size, ctx):
    """Source cLit/cLightEnv/cLightWork, preserving byte colors and light order."""
    sw._check(off, 4)
    count = sw.u16(off)
    version = sw.data[off + 2]
    if not 0x20 <= version <= 0x2C:
        raise ValueError('unsupported light version %#x' % version)
    offsets = sw.u32s(off + 4, count)
    raw = []
    for cut, relative in enumerate(offsets):
        if not relative:
            continue
        p = off + relative
        if relative < 4 + 4 * count:
            raise ValueError('light cut overlaps offset table')
        if sw.swapped(p + 4):
            continue  # shared cut: convert once
        sw._check(p, 260)
        lights = sw.u32(p + 4)
        sw.u32s(p + 8, 3)    # fog type/start/end, colors remain RGBA bytes
        sw.u32s(p + 24, 3)   # mirror fog
        sw.u32(p + 40)      # focus depth
        sw.f32(p + 68)      # far plane ratio
        sw.f32(p + 248)     # texture LOD bias
        # cLightEnv::pad_49 and other reserved bytes have no typed consumer;
        # retain them verbatim, including stale debug-export padding.
        sw._check(p + 260, lights * 300)
        for i in range(lights):
            w = p + 260 + i * 300
            kind = sw.data[w + 2]
            sw.f32s(w + 4, 4)  # position, radius
            sw.f32(w + 24)     # intensity
            sw.u32(w + 32)     # numeric parent id/parts
            sw.u16s(w + 36, 2)
            sw.u32(w + 40)
            sw.u32s(w + 44, 9)  # direction, spot/parallel union, attenuation
            # LightSpot::pad_24 is reserved and copied as opaque bytes.
            sub = w + 108
            known = 0
            if kind == 1: known = 5  # color bytes + signed flicker range
            elif kind == 2: sw.f32s(sub, 4); known = 16
            elif kind in (3, 6): sw.f32s(sub, 3); known = 12
            elif kind == 4: sw.u16s(sub + 4, 2); known = 9
            elif kind == 5: known = 14  # runtime pointers initialized by setPath
            elif kind == 7: sw.f32s(sub, 6); known = 24
            elif kind == 8: known = 3  # tracking type/enemy/part bytes
            elif kind >= 16:
                raw.append('cut%d light%d type%d work' % (cut, i, kind))
            # LightFuncTbl[0,9..15] is static and does not read work. The
            # unused tail and LightPath byte block are copied, not interpreted.
    return raw

def fmt_bin(sw, off, size, ctx):
    """ModelData CPU arrays in source layout; GX command streams stay BE bytes.

    Positions, normals and UV identities stay separate. No flattening, skinning,
    quantization change or geometry reduction takes place here.
    """
    sw._check(off, 64)
    version = sw.peek32(off + 60)
    if version not in (0x20010801, 0x20030818):
        raise ValueError('unsupported ModelData version %#x' % version)
    head = sw.offset32(off, off)
    color, tex, weight = (sw.offset32(off + i, off) for i in (12, 16, 20))
    nw, nj = sw.data[off + 24:off + 26]
    nd = sw.u16(off + 26)
    parts = sw.offset32(off + 28, off)
    flags, ntex = sw.u32s(off + 32, 2)
    ext = sw.u16(off + 42)
    shape, vertices, normals = (sw.offset32(off + i, off) for i in (44, 48, 52))
    nv, nn = sw.u16s(off + 56, 2)
    sw.u32(off + 60)
    blend, flip = ([sw.offset32(off + i, off) for i in (64, 68)]
                   if version == 0x20030818 else (0, 0))
    raw = []
    for i in range(nj):
        # Joint identity/parent bytes are not the numeric ModelDataHead union.
        sw.f32s(off + head + i * 16 + 4, 3)
    sw.u16s(off + vertices, nv * 4)
    if flags & 0x20000000:
        sw._check(off + normals, nn * 4)  # signed-byte normal and byte palette id
    else:
        sw.u16s(off + normals, nn * 4)
    if ext > 0xFF:
        for i in range(ext):
            p = off + weight + 12 * i
            ids = sw.u16s(p, 3)
            n = sw.u16(p + 6)
            sw._check(p + 8, 4)
            if not 1 <= n <= 3:
                raise ValueError('invalid extended weight record')
    else:
        sw._check(off + weight, nw * 8)
        for i in range(nw):
            p = off + weight + i * 8
            n = sw.data[p + 3]
            if not 1 <= n <= 3:
                raise ValueError('invalid weight record')
    # Material header is bytes except its size/statistics words. Parse only the
    # established indexed GX primitives; the stream itself remains unchanged.
    cursor = off + parts
    uv_indices = [] if MODEL_OBSERVER is not None else None
    max_tex = max_color = -1
    stride = 8 if flags & 0x80000000 else 6
    for i in range(nd):
        sw._check(cursor, 32)
        length = sw.u32(cursor + 24)
        sw.u32(cursor + 28)
        start, end = cursor + 32, cursor + 32 + length
        sw._check(start, length)
        p = start
        while p < end:
            opcode = sw.data[p]; p += 1
            if opcode == 0:
                continue
            if opcode not in (0x80, 0x90, 0x98, 0xA0, 0xA8, 0xB0, 0xB8):
                raise ValueError('unsupported model GX opcode %#x' % opcode)
            if p + 2 > end:
                raise ValueError('truncated GX count')
            count = sw.peek16(p); p += 2
            if p + count * stride > end:
                raise ValueError('GX primitive exceeds part')
            for _ in range(count):
                vi, ni = sw.peek16(p), sw.peek16(p + 2)
                if vi >= nv or ni >= nn:
                    raise ValueError('GX position/normal index outside array')
                ti = sw.peek16(p + stride - 2)
                max_tex = max(max_tex, ti)
                if uv_indices is not None:
                    uv_indices.append((p + stride - 2, ti))
                if stride == 8:
                    max_color = max(max_color, sw.peek16(p + 4))
                p += stride
        cursor = end
    sw.u16s(off + tex, (max_tex + 1) * 2)
    if max_color >= 0:
        sw._check(off + color, (max_color + 1) * 4)  # RGBA8 bytes, not words
    if blend:
        count = sw.u32(off + blend)
        sw.u16s(off + blend + 4, count * 4)
    if flip:
        count = sw.u32(off + flip)
        sw.u16s(off + flip + 4, count)
    if shape:
        # shape.cpp CalculateShape_new: entries are {offset,count} relative to
        # the entry table (four bytes after the shape-count header), followed by
        # {vertex index,s16 dx,dy,dz}. Keep every authored shape and delta.
        count = sw.u32(off + shape)
        table = off + shape + 4
        sw._check(table, count * 8)
        entries = [(sw.offset32(table + i * 8, table),
                    sw.u32(table + i * 8 + 4)) for i in range(count)]
        converted = {}
        for relative, number in entries:
            target = table + relative
            if relative < count * 8:
                raise ValueError('morph delta list overlaps entries')
            sw._check(target, number * 8)
            if not number:
                continue
            if target in converted:
                if converted[target] != number:
                    raise ValueError('shared morph list has inconsistent size')
                continue
            converted[target] = number
            for i in range(number):
                values = sw.u16s(target + i * 8, 4)
                if values[0] >= nv:
                    raise ValueError('morph vertex outside source position array')
    if MODEL_OBSERVER is not None:
        # The existing bounded parser provides the layout. Consumers must still
        # select a reviewed family and reject unsupported/mutable contracts.
        occupied = [(off, off + (72 if version == 0x20030818 else 64)),
                    (off + head, off + head + nj * 16),
                    (off + weight, off + weight + (ext * 12 if ext > 255 else nw * 8)),
                    (off + vertices, off + vertices + nv * 8),
                    (off + normals, off + normals + nn * (4 if flags & 0x20000000 else 8)),
                    (off + parts, cursor)]
        if max_color >= 0:
            occupied.append((off + color, off + color + (max_color + 1) * 4))
        MODEL_OBSERVER(sw.label, off, size, ctx, dict(
            version=version, joints=nj, weights=nw, extended_weights=ext,
            shape=shape, blend=blend, flip=flip, uv_offset=off + tex,
            uv_count=max_tex + 1, uv_indices=uv_indices, occupied=occupied))
    return raw

def fmt_smd(sw, off, size, ctx):
    """scroll.h cSmd/SmdWork: source instances and table-relative resources.

    Referenced BIN/TPL/FCV bodies use the existing source-layout handlers.
    Any incomplete nested payload keeps the whole SMD unqualified.
    """
    sw._check(off, 16)
    flag = sw.data[off + 1]
    count = sw.u16(off + 2)
    tables = [sw.offset32(off + 4 + 4*i, off) for i in range(3)]
    work = off + 16
    total = count
    if flag & 1:
        groups = sw.u32(work)
        sizes = sw.u32s(work + 4, groups)
        # Group counts reserve runtime slots for separately loaded blocks;
        # this file still contains exactly nModel placement records.
        work += 4 + 4 * groups
    sw._check(work, total * 72)
    local_ids = [set(), set(), set()]
    for i in range(total):
        p = work + i * 72
        sw.f32s(p, 9)
        flags = sw.u32(p + 68)
        ids = sw.data[p + 36:p + 39]
        # Retain every placement, including unused records. Resource references
        # with common-model flags resolve from the other SMD at runtime.
        for j, common in enumerate((0x10, 0x10, 0x40)):
            if not flags & common and ids[j] != 0xFF:
                local_ids[j].add(ids[j])
    raw = []
    for kind, table, ids in zip(('BIN', 'TPL', 'FCV'), tables, local_ids):
        if not ids:
            continue
        if not 16 <= table < size:
            raise ValueError('SMD referenced table outside file')
        # Count comes from source references, not padding before the first body.
        n = max(ids) + 1
        base = off + table
        offsets = [sw.offset32(base + 4*i, base) for i in range(n)]
        for ident in sorted(ids):
            relative = offsets[ident]
            target = base + relative
            if relative < 4 * n or target >= off + size:
                raise ValueError('SMD resource offset outside file')
            limits = [off + size] + [off + t for t in tables if off + t > target]
            limits += [base + value for value in offsets if base + value > target]
            end = min(limits)
            if not sw.swapped(target):
                with sw.bounded(target, end - target):
                    pending = {'TPL': fmt_tpl, 'BIN': fmt_bin, 'FCV': fmt_fcv}[kind](
                        sw, target, end - target, ctx + '/%s%d' % (kind, ident))
                raw.extend('%s%d %s' % (kind, ident, item) for item in (pending or []))
    return raw


def fmt_smx(sw, off, size, ctx):
    """scroll.h SmxWork plus obj02.cpp's rotate/swing work layouts."""
    sw._check(off, 16)
    count = sw.data[off + 1]
    sw._check(off + 16, count * 144)
    raw = []
    for i in range(count):
        p = off + 16 + i * 144
        kind = sw.data[p + 1]
        sw.u32s(p + 4, 3)  # selection mask, flags, packed numeric RGBA
        sw.u32(p + 132)    # packed numeric color2
        sw.f32s(p + 136, 2)
        work = p + 16
        if kind == 1:
            sw.f32s(work, 3)  # rotation speed; byte flag at +12 stays byte
            if any(sw.data[work + 13:work + 116]):
                raw.append('SMX%d extra rotate work' % i)
        elif kind == 2:
            sw.f32s(work, 13)  # phase/amplitude/frequency/time/base rotation
            if any(sw.data[work + 52:work + 116]):
                raw.append('SMX%d extra swing work' % i)
        elif kind == 0 and ctx.startswith('st1/r120.arc#'):
            # r120.cpp never installs a scroll callback or reads object work;
            # obj02::moveNormal is empty. Preserve opaque unused authoring bytes.
            pass
        elif any(sw.data[work:work + 116]):
            # Type zero's normal mover ignores work, but room callbacks may
            # consume it. Do not guess its scalar layout from nonzero bytes.
            raw.append('SMX%d type%d callback work' % (i, kind))
    return raw

TAG_FORMATS = {
    b"OSD\0": fmt_osd,
    b"EVS\0": fmt_empty_evs,
    b"AEV\0": fmt_sce_at,
    b"ITA\0": fmt_sce_at,
    b"RTP\0": fmt_rtp,
    b"STB\0": fmt_stb,
    b"ESE\0": fmt_ese,
    b"DSE\0": fmt_dse,
    b"EMI\0": fmt_emi,
    b"DRA\0": fmt_dra,
    b"ETS\0": fmt_ets,
    b"EAR\0": fmt_ear,
    b"SAR\0": fmt_sar,
    b"FCV\0": fmt_fcv,
    b"SEQ\0": fmt_fcvseq,
    b"ITM\0": fmt_itm,
    b"ETM\0": fmt_etm,
    b"BLK\0": fmt_blk,
    b"SHD\0": fmt_shd,
    b"TEX\0": fmt_tex,
    b"FSE\0": fmt_fse,
    b"CAM\0": fmt_cam,
    b"LIT\0": fmt_lit,
    b"BIN\0": fmt_bin,
    b"SMD\0": fmt_smd,
    b"SMX\0": fmt_smx,
    b"CNS\0": fmt_cns,
    b"SAT\0": fmt_sat,
    b"EAT\0": fmt_sat,
    # Sub screen map room hit (ss_map.cpp mapHitAddr -> cSatHeader, read by
    # mapPositionCheck through cSat::init/getSat): the SAT layout.
    b"MHT\0": fmt_sat,
    # Sub screen font (sscrn.cpp / ss_file.cpp / ss_term.cpp setupFont with
    # SS_ARC_PTR(arc, 4)): the MesFontFile of font/*.fnt.
    b"FNT\0": fmt_fnt,
    b"MDT\0": fmt_mdt,
    b"TPL\0": fmt_tpl,
    b"UWF\0": fmt_uwf,
    b"EFF\0": fmt_eff,
}


def looks_like_tagged(data, off, size, max_count=0x100):
    if size < 0x18:
        return False
    n = struct.unpack_from(">I", data, off)[0]
    if n == 0 or n > max_count or 0x10 + 8 * n > size:
        return False
    if any(struct.unpack_from(">3I", data, off + 4)):
        return False
    offs = struct.unpack_from(">%dI" % n, data, off + 0x10)
    if offs[0] < 0x10 + 8 * n or any(b > size for b in offs):
        return False
    if any(offs[i] > offs[i + 1] for i in range(n - 1)):
        return False
    tags = data[off + 0x10 + 4 * n: off + 0x10 + 8 * n]
    for i in range(n):
        t = tags[4 * i:4 * i + 4]
        # Player archives retain empty source slots (tools/drs.py): a zero
        # tag is valid only when this slot owns no bytes. Keep its offset and
        # index; removing it would change PL_ARC_PTR identities.
        end = offs[i + 1] if i + 1 < n else size
        if t == bytes(4) and offs[i] == end:
            continue
        if not (t[:3].isalpha() and t[:3].isupper() and t[3] == 0):
            return False
    return True


def fmt_tagged(sw, off, size, ctx):
    """Tagged archive: u32 count, 12 bytes, u32 ofs[count], char tag[count][4];
    every sub-file is dispatched on its tag."""
    n = sw.u32(off)
    offs = [sw.offset32(off + 0x10 + 4*i, off) for i in range(n)]
    tags = [bytes(sw.data[off + 0x10 + 4 * n + 4 * i: off + 0x10 + 4 * n + 4 * i + 4]) for i in range(n)]
    order = sorted(range(n), key=lambda i: offs[i])
    for rank, i in enumerate(order):
        start = offs[i]
        end = offs[order[rank + 1]] if rank + 1 < n else size
        if end <= start:
            continue
        sub_ctx = "%s#%d" % (ctx, i)
        handler = TAG_FORMATS.get(tags[i])
        for pattern, table in FILE_TAG_FORMATS:
            if tags[i] in table and fnmatch.fnmatchcase(sw.label, pattern):
                handler = table[tags[i]]
        # CoreData's fixed offset is authoritative; BIN here is not ModelData.
        if sub_ctx == 'etc/core.das:0#11':
            handler = fmt_light_paths
        entry = {"file": sw.label, "sub": sub_ctx, "tag": tags[i][:3].decode("ascii", "replace"),
                 "ofs": off + start, "size": end - start, "handled": handler is not None}
        if handler is fmt_light_paths:
            entry['format'] = 'LightPathHeader'
        if handler:
            if not sw.swapped(off + start):
                guarded(sw, handler, off + start, end - start, sub_ctx, entry)
        elif looks_like_tagged(sw.data, off + start, end - start):
            entry["tag"] = "ARC"
            entry["handled"] = True
            guarded(sw, fmt_tagged, off + start, end - start, sub_ctx, entry)
        REPORT.append(entry)


def fmt_ss_arc(sw, off, size, ctx):
    """ss_pzzl.dat (ss_pzzl.cpp pieceTblInit / SsPzzlMain::init, ss_shop.cpp):
    the tagged archive shape (SsArc: SS_ARC_PTR(arc, n) = ofs[n] + arc, so
    SsArc index n is sub-file n - 4), but with 424 slots: a BIN / TPL pair per
    item id at 4 + 2 * id / 5 + 2 * id (zero-tag empty slots keep their
    index), then MDT 0x1A4, TPL 0x1A5, BIN 0x1A6..0x1A9, EFF 0x1AA, UWF 0x1AB.
    Only the slot limit differs from the generic detector."""
    if not looks_like_tagged(sw.data, off, size, max_count=0x200):
        raise ValueError('not a sub screen tagged archive')
    return fmt_tagged(sw, off, size, ctx)


def guarded(sw, handler, off, size, ctx, entry):
    """Runs a handler confined to [off, off+size); on a layout error that
    region (and only that region) is restored raw and the error recorded, so
    one unexpected sub-file never aborts the mirror or damages a neighbour.
    A handler may return a list of "raw parts" it left untouched on purpose
    (an explicit safe-raw contract); they are recorded and the entry is
    marked incomplete."""
    backup = bytes(sw.data[off:off + size])
    marks = bytes(sw.done[off:off + size])
    try:
        with sw.bounded(off, size):
            raw = handler(sw, off, size, ctx)
        if raw:
            entry["raw_parts"] = list(raw)
            # a static-module REL is complete by contract: only its header is data
            entry["complete"] = handler is fmt_rel
        else:
            entry["complete"] = True
    except (ValueError, IndexError, struct.error) as e:
        sw.data[off:off + size] = backup
        sw.done[off:off + size] = marks
        entry["handled"] = False
        entry["complete"] = False
        entry["error"] = str(e)


# Files the game reads but never overlays a structure on (or only through a
# consumer outside the boot fixture): copied verbatim under a named contract.
RAW_CONTRACTS = {
    "etc/sizetbl.dat": "stored in cDvd::pSizeTbl by SizeTableRead and never dereferenced (src/game/dvd.cpp)",
}

# Tag handlers that hold only inside one file family (the same tag names
# another layout elsewhere): the codec screen's op/opNN.das SEQ sub-files are
# ss_term TermSeq tables, not FCV motion sequences.
FILE_TAG_FORMATS = [
    ("op/op*.das", {b"SEQ\0": fmt_term_seq}),
]

FILE_FORMATS = [
    ("bgm/bio4str.hed", fmt_bio4str_hed),
    ("bgm/bio4midi.hed", fmt_u32_array),
    ("bgm/doorse.hed", fmt_doorse_hed),
    ("bgm/bgmtbl.dat", fmt_bgmtbl_dat),
    ("debug/roominfo.dat", fmt_roominfo),
    ("rel/*.rel", fmt_rel),
    ("font/*.fnt", fmt_fnt),
    # Loose chapter-title ID data (r101.cpp r101_Event30_TitleCall: IdTexDataLoad / IdSys.set).
    ("etc/*/id*.eff", fmt_eff),
    ("etc/*/*.uwf", fmt_uwf),
    # Sub screen: item examine models (ss_main.cpp SS/item/idm%03x.bin,
    # cap%02d.bin), pick-up models (sce_at.cpp SS/cmn/itm%02x.bin) and the
    # attache case archive; all are ModelData / tagged layouts.
    ("ss/item/*.bin", fmt_bin),
    ("ss/cmn/itm*.bin", fmt_bin),
    ("ss/*/ss_pzzl.dat", fmt_ss_arc),
    ("*.tpl", fmt_tpl),
]

REPORT = []


def find_handler(table, key):
    for pattern, handler in table:
        if fnmatch.fnmatchcase(key, pattern):
            return handler
    return None


def fmt_evd(sw, off, size, ctx):
    """event.h EvtHeader/packet stream/named assets. Source layout, no event skip."""
    sw._check(off, 80)
    if bytes(sw.data[off:off+5]) != b'event':
        raise ValueError('invalid event header tag')

    def name_at(pos, count):
        sw._check(pos, count)
        raw = bytes(sw.data[pos:pos+count])
        if b'\0' not in raw:
            raise ValueError('unterminated event name')
        return raw.split(b'\0')[0].decode('ascii')

    name_at(off, 32); name_at(off+32, 8); name_at(off+40, 12)
    sw.u32(off+52)  # sndFlag; the event name and sound-id byte stay intact
    po, ps, count, bo = sw.u32s(off+64, 4)
    if po < 80 or ps < 16 or bo < po+ps or count > size//64:
        raise ValueError('invalid event packet/bin regions')
    sw._check(off+po, ps); sw._check(off+bo, count*64)
    sizes = {0:16, 3:128, 4:144, 6:64, 9:80, 11:80, 12:80, 13:48,
             14:64, 15:32, 17:32, 26:16, 27:16, 28:64, 32:64}
    pos, end = off+po, off+po+ps
    terminated = False
    while pos < end:
        with sw.bounded(pos, end-pos):
            kind, flags = sw.u32s(pos, 2)
            cut, frame, length, pad = sw.u16s(pos+8, 4)
            if kind not in sizes or length != sizes[kind] or pos+length > end:
                raise ValueError('unsupported/invalid event packet %d size %d' % (kind,length))
            if kind in (6,14,28,32): name_at(pos+16,48)
            elif kind in (3,11,12):
                name_at(pos+16,12); name_at(pos+28,48)
                if kind == 3: name_at(pos+76,48)
            elif kind == 4:
                name_at(pos+16,12); name_at(pos+28,12)
                name_at(pos+40,48); name_at(pos+88,48)
            elif kind == 9:
                name_at(pos+16,12); name_at(pos+28,12); sw.u32s(pos+40,7)
            elif kind in (15,17): sw.u32s(pos+16,3)
            elif kind == 13:
                # ExePacket_Esp (event.cpp): esp.name[0xC] @0x10, s32 type @0x1C,
                # u8 parts @0x23 (byte, no swap); 0x24..0x2F are never read.
                name_at(pos+16,12); sw.u32(pos+0x1C)
            if kind == 27:
                if pos+length != end:
                    raise ValueError('event EndPac does not terminate stream')
                terminated = True
        pos += length
    if not terminated: raise ValueError('event stream lacks EndPac')
    assets = []
    for i in range(count):
        entry = off+bo+64*i
        name = name_at(entry,48)
        start = sw.u32(entry+48)
        if start < bo+64*count or start >= size:
            raise ValueError('event asset overlaps tables or outside file')
        assets.append((name,start))
    bounds = sorted(set(o for _,o in assets)) + [size]
    formats = {'bin':fmt_bin, 'tpl':fmt_tpl, 'fcv':fmt_fcv,
               'eff':fmt_eff, 'lit':fmt_lit, 'mdt':fmt_mdt}
    aliases = {}
    for i,(name,start) in enumerate(assets):
        length = bounds[bounds.index(start)+1]-start
        ext = name.rsplit('.',1)[-1].lower()
        handler = formats.get(ext)
        if start in aliases and aliases[start] != ext:
            raise ValueError('conflicting event asset types at shared offset')
        aliases[start] = ext
        entry = {'file':sw.label,'sub':ctx+'#%d'%i, 'name':name,
                 'ofs':off+start,'size':length,'tag':ext.upper(),
                 'handled':handler is not None}
        if handler and not sw.swapped(off+start):
            # Shape and skeletal FCV share this byte/key layout; the original
            # packet selects ShapeSet vs MotionSetCore, unchanged by conversion.
            guarded(sw,handler,off+start,length,ctx+'#%d'%i,entry)
        elif handler:
            entry['complete'] = True
        REPORT.append(entry)


def fmt_drs_body(sw, off, size, ctx):
    # tools/drs.py validated the original container before any endian edits.
    # The final tagged entry ends at rel_offset, not at the end of PPC code.
    rel_offset = sw.peek32(off + 4)
    fmt_tagged(sw, off, rel_offset or size, ctx)
    sw.u32(off + 4)
    if rel_offset:
        entry = {"file": sw.label, "sub": ctx + "#REL", "tag": "REL",
                 "ofs": off + rel_offset, "size": size - rel_offset,
                 "handled": True, "module_id": sw.peek32(off + rel_offset),
                 "native_binding_required": True}
        guarded(sw, fmt_rel, off + rel_offset, size - rel_offset, ctx + "#REL", entry)
        REPORT.append(entry)


def fmt_drs(sw, off, size, ctx):
    # Use the repository's existing archive parser, including its REL boundary
    # and sound-bank checks. Do not infer DVD containers from arbitrary bytes.
    tools_dir = str(Path(__file__).resolve().parents[3] / 'tools')
    if tools_dir not in sys.path:
        sys.path.insert(0, tools_dir)
    import drs
    original = bytes(sw.data[off:off + size])
    try:
        archive = drs.Drs(original)
        if archive.pack() != original:
            raise ValueError('DRS source roundtrip differs')
    except (AssertionError, IndexError, struct.error) as exc:
        raise ValueError('invalid source DRS: ' + str(exc)) from exc
    convert_container(sw, ctx, drs_body=True)


def convert_part(sw, rel, key, part_off, size, entry, drs_body=False):
    if entry["type"] == 1:  # sound block, MRAM half (type 2 is the ARAM sample data)
        entry["format"] = "SND"
        entry["handled"] = True
        guarded(sw, lambda sw_, o, n, c: fmt_snd_mram(sw_, o, n, c, bgm=entry["snd"][0] == 3),
                part_off, size, "%s:%s" % (rel, key), entry)
    elif drs_body and entry["type"] == 0:
        entry["format"] = "DRS_ARC"
        entry["handled"] = True
        guarded(sw, fmt_drs_body, part_off, size, "%s:%s" % (rel, key), entry)
    elif looks_like_tagged(sw.data, part_off, size):
        entry["format"] = "ARC"
        entry["handled"] = True
        guarded(sw, fmt_tagged, part_off, size, "%s:%s" % (rel, key), entry)
    elif entry["type"] == 2:
        # ARAM sample data: raw PCM / ADPCM bytes the sound DSP consumes as a
        # byte stream; no game structure is overlaid on it (explicit safe-raw).
        entry["format"] = "ARAM"
        entry["handled"] = True
        entry["complete"] = True
        entry["safe_raw"] = "sample bytes"


def convert_container(sw, rel, drs_body=False):
    data = sw.data

    def walk(base, key_prefix, depth):
        off = base + ENTRY_SIZE  # entry 0 is the magic block
        i = 0
        while off + ENTRY_SIZE <= base + HEADER_TABLE:
            t, size, dest, ofs, snd_type, snd_arg, snd_no, x1c = sw.u32s(off, 8)
            key = "%s%d" % (key_prefix, i)
            if t == END_OF_TABLE:
                break
            if t == SKIP_ENTRY:
                pass
            elif t == NESTED:
                if depth == 0:
                    walk(ofs, key + "/", 1)
                else:
                    REPORT.append({"file": rel, "part": key, "note": "nested table below the game's nest limit"})
            else:
                part_off = base + ofs
                if part_off + size > len(data):
                    raise ValueError("%s part %s outside the file" % (rel, key))
                entry = {"file": rel, "part": key, "type": t, "ofs": part_off, "size": size,
                         "snd": [snd_type, snd_arg, snd_no], "handled": False}
                convert_part(sw, rel, key, part_off, size, entry, drs_body and depth == 0)
                REPORT.append(entry)
            off += ENTRY_SIZE
            i += 1

    walk(0, "", 0)


def convert_file(rel, data):
    sw = Swapper(data, rel)
    handler = (fmt_drs if fnmatch.fnmatchcase(rel, "em/*.drs") else
               fmt_evd if fnmatch.fnmatchcase(rel, "evd/*.evd") else
               fmt_esl if fnmatch.fnmatchcase(rel, "etc/*.esl") else find_handler(FILE_FORMATS, rel))
    if handler:
        entry = {"file": rel, "handled": True, "size": len(data)}
        guarded(sw, handler, 0, len(data), rel, entry)
        REPORT.append(entry)
    elif data[:32] == CONTAINER_MAGIC:
        convert_container(sw, rel)
    elif looks_like_tagged(data, 0, len(data)):
        entry = {"file": rel, "handled": True, "size": len(data), "format": "ARC"}
        guarded(sw, fmt_tagged, 0, len(data), rel, entry)
        REPORT.append(entry)
    elif rel in RAW_CONTRACTS:
        REPORT.append({"file": rel, "handled": True, "complete": True, "size": len(data),
                       "format": "RAW", "safe_raw": RAW_CONTRACTS[rel]})
    elif rel.endswith(".txt"):
        # Text the game parses byte by byte (debug/config.txt): explicit safe-raw.
        REPORT.append({"file": rel, "handled": True, "complete": True, "size": len(data),
                       "format": "TXT", "safe_raw": "text"})
    else:
        REPORT.append({"file": rel, "handled": False, "size": len(data)})


def check_required(report, deps_path):
    """Every entry of every required file must be handled and complete (or
    safe-raw). Returns the list of violations as strings."""
    required = []
    with open(deps_path) as f:
        lines = f.readlines()
    for line in lines:
        # a comment starts the line or follows whitespace ("#n" names a sub-file)
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        line = line.split(" #", 1)[0].split(chr(9) + "#", 1)[0].strip().lower()
        if line:
            required.append(line)
    by_file = {}
    for e in report:
        by_file.setdefault(e["file"], []).append(e)
    problems = []
    for line in required:
        # "file" = every part and sub-file of it; "file:part" = that container
        # part; "file:part#n" or "file#n" = that tagged sub-file only.
        rel = line.split(":", 1)[0].split("#", 1)[0]
        entries = by_file.get(rel)
        if not entries:
            problems.append("%s: not in the tree" % rel)
            continue
        if "#" in line:
            entries = [e for e in entries if e.get("sub") == line]
        elif ":" in line:
            entries = [e for e in entries if "%s:%s" % (rel, e.get("part")) == line]
        if not entries:
            problems.append("%s: no such part" % line)
            continue
        for e in entries:
            where = e.get("sub") or ("%s:%s" % (rel, e["part"]) if "part" in e else rel)
            if e.get("error"):
                problems.append("%s: error: %s" % (where, e["error"]))
            elif not e.get("handled"):
                problems.append("%s: no handler (tag %s)" % (where, e.get("tag", e.get("format", "?"))))
            elif e.get("complete") is False:
                problems.append("%s: incomplete, raw parts: %s" % (where, ", ".join(e.get("raw_parts", []))))
    return problems


def prepare_room_archive(rel, data):
    """Decode the source room's single type-0 payload, then use normal handlers.

    The returned .arc is a build artifact, not runtime-ready unless every entry
    passes check_required. Original compressed files remain independently copied.
    """
    from decode_yz2 import decode
    if data[:32] != CONTAINER_MAGIC:
        raise ValueError(rel + ': room is not a DVD container')
    payloads = []
    terminated = False
    for pos in range(ENTRY_SIZE, HEADER_TABLE, ENTRY_SIZE):
        kind, size, dest, offset = struct.unpack_from('>4I', data, pos)
        if kind == END_OF_TABLE:
            terminated = True
            break
        if kind == 0:
            if offset < HEADER_TABLE or offset + size > len(data):
                raise ValueError(rel + ': room payload outside container')
            payloads.append((offset, size))
        elif kind not in (NESTED, SKIP_ENTRY):
            raise ValueError(rel + ': unexpected top-level room entry')
    if not terminated or len(payloads) != 1:
        raise ValueError(rel + ': expected one type-0 room payload')
    offset, size = payloads[0]
    decoded = bytearray(decode(data[offset:offset + size]))
    if not looks_like_tagged(decoded, 0, len(decoded)):
        raise ValueError(rel + ': decoded room is not a tagged archive')
    native_rel = rel[:-4] + '.arc'
    convert_file(native_rel, decoded)
    return native_rel, decoded



# Enemy/player DRS uses this second source signature; its structural validation
# is already performed by fmt_drs/tools.drs before any payload replacement.
DRS_MAGIC = bytes.fromhex('836e834a835a82cc8341837a815b815b815b815b815b815b815b814981498149')


def native_payload_slot(converted_container):
    """Validate the existing one-main-payload DVD transport contract."""
    data = converted_container
    if len(data) < HEADER_TABLE or data[:32] not in (CONTAINER_MAGIC, DRS_MAGIC):
        raise ValueError('native room requires a converted DVD container')
    payload_headers = []
    ended = False
    for pos in range(ENTRY_SIZE, HEADER_TABLE, ENTRY_SIZE):
        kind, size, dest, offset = struct.unpack_from('<4I', data, pos)
        if kind == END_OF_TABLE:
            ended = True
            break
        if kind == 0:
            if dest or offset < HEADER_TABLE or offset + size > len(data):
                raise ValueError('native room has an invalid type-0 destination/range')
            payload_headers.append(pos)
        elif kind not in (NESTED, SKIP_ENTRY):
            raise ValueError('native room has an unexpected top-level entry')
    if not ended or payload_headers != [ENTRY_SIZE]:
        raise ValueError('native room requires one room payload in the first slot')
    return payload_headers[0]


def replace_native_payload(converted_container, payload):
    """Replace a previously qualified payload, preserving nested sound bytes.

    Qualification belongs to the caller; this shared transport helper only
    checks the DVD boundary. It is not an archive conversion success gate.
    """
    slot=native_payload_slot(converted_container)
    data=bytearray(converted_container)
    offset=(len(data)+31)&~31
    data+=bytes(offset-len(data))+payload
    data+=bytes((-len(data))&31)
    struct.pack_into('<4I',data,slot,0,len(payload),0,offset)
    return data


def prepare_native_room(rel, converted_container, decoded, entries):
    """Qualified native DVD container: replace only top-level type 0.

    Keep nested sound headers/offsets and payloads exactly as converted. Appending
    the room avoids relocating those tables; old compressed bytes occupy disc
    space only and are never read into RAM. No hardcoded GameCube destination is
    permitted. Qualification includes every decoded subfile and sound entry.
    """
    native_rel = rel[:-4] + '.dar'
    arc_rel = rel[:-4] + '.arc'
    native_payload_slot(converted_container)
    covered = [e for e in entries if e['file'] == arc_rel or
               (e['file'] == rel and not (e.get('type') == 0 and
                                         '/' not in str(e.get('part', ''))))]
    if not any(e['file'] == arc_rel and 'sub' not in e for e in covered):
        raise ValueError('native room has no decoded archive coverage')
    # Explicit success, rather than absence of an error, is required here.
    bad = [e.get('sub', e.get('part', e['file'])) for e in covered
           if not e.get('handled') or e.get('complete') is not True or e.get('error')]
    if bad:
        raise ValueError('unqualified native room dependencies: ' + ', '.join(map(str, bad)))
    return native_rel, replace_native_payload(converted_container, decoded)


# Native descriptor uses the existing OSModuleHeader layout, with no PPC sections.
# Version marks an explicit static binding; only id and bssSize survive.
STATIC_REL_VERSION = 0xDC000001


def static_module_ids():
    """Use the existing binding table; refuse a stale Makefile/registry pair."""
    root = Path(__file__).resolve().parents[3]
    registry = (root / 'port/dreamcast/game/platform/modules.cpp').read_text()
    bindings = re.findall(r'^    MODULE\((\d+), (\w+)\),$', registry, re.M)
    makefile = (root / 'port/dreamcast/game/Makefile').read_text()
    selected = re.search(r'^MODULES = (.*)$', makefile, re.M)
    if not bindings or selected is None or set(selected[1].split()) != {n for _, n in bindings}:
        raise ValueError('static module registry and Makefile disagree')
    result = {int(i): n for i, n in bindings}
    if len(result) != len(bindings):
        raise ValueError('duplicate static module id')
    for ident, name in result.items():
        config = json.loads((root / 'config/G4BE08/modules' / name / 'rel.json').read_text())
        if config['module_id'] != ident:
            raise ValueError('static module id differs from source config: ' + name)
    return result


def compact_static_rel(rel, data, entries, bindings):
    """Drop only unused code after whole-file qualification, never asset entries.

    DRS remains a source DVD container. Its body/REL boundary is unchanged;
    the nested sound container is moved as an intact byte string. Rebase only
    top-level DVD offsets, and keep all asset offsets and source slot numbers.
    Runtime OSLink must bind the marked descriptor to real compiled SH-4 code.
    """
    embedded = rel.startswith('em/') and rel.endswith('.drs')
    standalone = rel.startswith('rel/') and rel.endswith('.rel')
    if not (embedded or standalone):
        return data
    own = [e for e in entries if e['file'] == rel]
    if not own or any(not e.get('handled') or e.get('complete') is not True or e.get('error') for e in own):
        return data  # failed qualification remains failed; never turn it into success
    if embedded:
        kind, body_size, dest, body_off = struct.unpack_from('<4I', data, 32)
        if kind != 0 or dest or body_off != HEADER_TABLE or body_off + body_size > len(data):
            raise ValueError('compact DRS requires the validated source body layout')
        rel_offset = struct.unpack_from('<I', data, body_off + 4)[0]
        if not rel_offset:
            return data
        start, end = body_off + rel_offset, body_off + body_size
    else:
        start, end = 0, len(data)
    if end - start < 64:
        raise ValueError('short static module header')
    ident = struct.unpack_from('<I', data, start)[0]
    if ident not in bindings:
        return data  # unknown modules retain the explicit native-binding requirement
    version, bss = struct.unpack_from('<2I', data, start + 0x1c)
    if version != 3:
        raise ValueError('expected an unlinked source REL version 3')
    header = bytearray(64)
    struct.pack_into('<I', header, 0, ident)
    struct.pack_into('<2I', header, 0x1c, STATIC_REL_VERSION, bss)
    out = bytearray(data[:start]) + header + data[end:]
    saved = end - start - len(header)
    if embedded:
        struct.pack_into('<I', out, 36, body_size - saved)
        for at in range(64, HEADER_TABLE, ENTRY_SIZE):
            kind, size, dest, offset = struct.unpack_from('<4I', out, at)
            if kind == END_OF_TABLE:
                break
            if kind not in (NESTED, SKIP_ENTRY) or offset < end or offset + size > len(data):
                raise ValueError('unexpected compact DRS trailing record')
            struct.pack_into('<I', out, at + 12, offset - saved)
    for e in own:
        if e.get('ofs', -1) >= end:
            e['ofs'] -= saved
        if e.get('tag') == 'REL' or (standalone and 'part' not in e and 'sub' not in e):
            e['source_size'] = e['size']; e['size'] = 64
            e.pop('raw_parts', None)
            e['native_binding_required'] = True
            e['static_module'] = bindings[ident]
        elif embedded and e.get('part') == '0':
            e['source_size'] = e['size']; e['size'] -= saved
        if 'part' not in e and 'sub' not in e:
            e['source_size'] = len(data); e['size'] = len(out)
            e['native_compacted'] = True
            e['unused_ppc_bytes_removed'] = saved
    return out


def prepare_event_reference(rel, source):
    """Bounded EVD preparation, using this converter's actual coverage result.

    Return the qualified LE payload and its immutable-file transport certificate.
    Callers must use this returned payload (or compare it exactly with a current
    mirror), not attach the certificate to an unrelated cached conversion.
    Proprietary payloads/certificates stay in private generated directories.
    """
    import re
    import zlib
    if not re.fullmatch(r'evd/[a-z0-9_]+\.evd', rel) or len(rel) >= 32:
        raise ValueError('noncanonical event identity')
    if not source or len(source) > 4 * 1024 * 1024 or len(source) % 32:
        raise ValueError('event size outside bounded transport')
    mark = len(REPORT)
    data = bytearray(source)
    try:
        convert_file(rel, data)
        records = REPORT[mark:]
        if not records or any(not e.get('complete') or e.get('error') for e in records):
            raise ValueError('event conversion is incomplete')
        chunk = 65536
        crcs = b''.join(struct.pack('<I', zlib.crc32(data[i:i+chunk]))
                        for i in range(0, len(data), chunk))
        cert = b'R4EVDREF' + struct.pack('<6I', 1, len(data), chunk, len(crcs)//4,
                                       zlib.crc32(rel.encode('ascii')), zlib.crc32(crcs)) + crcs
        return bytes(data), cert
    finally:
        del REPORT[mark:]


def main():
    argv = sys.argv[1:]
    require = None
    if "--require" in argv:
        i = argv.index("--require")
        require = argv[i + 1]
        del argv[i:i + 2]
    args = [a for a in argv if not a.startswith("--")]
    force = "--force" in argv
    compact_modules = "--compact-static-rel" in argv
    bindings = static_module_ids() if compact_modules else {}
    native_rooms = "--native-rooms" in argv
    decode_rooms = "--decode-rooms" in argv or native_rooms
    if len(args) != 2:
        sys.exit(__doc__)
    src, dst = args
    tool_mtime = os.path.getmtime(os.path.abspath(__file__))
    report_path = os.path.join(dst, "le_mirror_report.json")
    previous = {}
    if os.path.exists(report_path):
        for e in json.load(open(report_path)):
            previous.setdefault(e["file"], []).append(e)
    converted = skipped = 0
    for root, dirs, files in sorted(os.walk(src)):
        for name in sorted(files):
            sp = os.path.join(root, name)
            rel = os.path.relpath(sp, src).replace(os.sep, "/").lower()
            dp = os.path.join(dst, rel)
            os.makedirs(os.path.dirname(dp), exist_ok=True)
            if decode_rooms and fnmatch.fnmatchcase(rel, "st*/r*.das"):
                native_rel, decoded = prepare_room_archive(rel, open(sp, "rb").read())
                native_path = os.path.join(dst, native_rel)
                with open(native_path, "wb") as f:
                    f.write(decoded)
            was_compacted = any(e.get("native_compacted") for e in previous.get(rel, []))
            if not force and not compact_modules and not was_compacted and not (native_rooms and fnmatch.fnmatchcase(rel, "st*/r*.das")) and os.path.exists(dp) and rel in previous:
                dm = os.path.getmtime(dp)
                if dm >= os.path.getmtime(sp) and dm >= tool_mtime:
                    REPORT.extend(previous[rel])
                    skipped += 1
                    continue
            data = bytearray(open(sp, "rb").read())
            convert_file(rel, data)
            if compact_modules:
                data = compact_static_rel(rel, data, REPORT, bindings)
            with open(dp, "wb") as f:
                f.write(data)
            if native_rooms and fnmatch.fnmatchcase(rel, "st*/r*.das"):
                native_path = os.path.join(dst, rel[:-4] + '.dar')
                try:
                    native_rel, packaged = prepare_native_room(rel, data, decoded, REPORT)
                except ValueError as exc:
                    # Do not leave an older qualified package beside a newly
                    # rejected conversion. This is an exact generated path.
                    if os.path.exists(native_path):
                        os.unlink(native_path)
                    REPORT.append({'file': rel[:-4]+'.dar', 'handled': False,
                                   'complete': False, 'error': str(exc)})
                else:
                    with open(native_path + '.tmp', 'wb') as f:
                        f.write(packaged)
                    os.replace(native_path + '.tmp', native_path)
                    REPORT.append({'file': native_rel, 'handled': True,
                                   'complete': True, 'size': len(packaged)})
            converted += 1
    with open(report_path, "w") as f:
        json.dump(REPORT, f, indent=1)
    subs = [e for e in REPORT if "sub" in e]
    raw_tags = {}
    for e in subs:
        if not e.get("handled"):
            raw_tags[e["tag"]] = raw_tags.get(e["tag"], 0) + 1
    print("le_mirror: %d converted, %d up to date; %d whole files handled, %d raw files; "
          "%d tagged sub-files (%d handled); raw by tag: %s"
          % (converted, skipped, sum(1 for e in REPORT if e.get("handled") and "part" not in e and "sub" not in e),
             sum(1 for e in REPORT if "part" not in e and "sub" not in e and not e.get("handled")),
             len(subs), sum(1 for e in subs if e.get("handled")),
             " ".join("%s=%d" % kv for kv in sorted(raw_tags.items()))))
    errors = [e for e in REPORT if e.get("error")]
    if errors:
        print("le_mirror: %d handler errors (rolled back to raw), first: %s: %s"
              % (len(errors), errors[0].get("sub") or errors[0]["file"], errors[0]["error"]))
    if require:
        problems = check_required(REPORT, require)
        if problems:
            print("le_mirror: boot fixture dependencies not satisfied (%s):" % require)
            for m in problems:
                print("  " + m)
            sys.exit(2)
        print("le_mirror: boot fixture dependencies satisfied (%s)" % require)


if __name__ == "__main__":
    main()
