#!/usr/bin/env python3
"""PS2 sound data for the AICA banks and disc streams (lane purge-audio24, 2026-10-24).

The game's sound code and its GC tables stay (ISS cue tables, sequences, the wavetable's instruments, regions, loops,
rates and lengths: they decide which sound plays, when and how). What changes is the PCM behind each wavetable sample:
it comes from the PS2 version instead of the GC DSP-ADPCM image.

PS2 formats (BIO4DAT.AFS):
  rNNN.snd / emNN.snd / plNN.snd / wepNN.snd / core.snd / title.snd / miNNN_[ab].snd are DvdHeader archives, like the
  GC banks: 32-byte header, then 32-byte part entries (type, size, dest, offset, sndType, arg, sndNo, 0), 0xFFFFFFFF.
  For each sound block: a type-1 part with Capcom's SE table (dest 0xFFF4), a type-1 part with a Sony-style HD bank
  (dest 0xFFF2: chunks "Head", "Prog", "Smpl", "Vagi"; Vagi = count-1 then 16-byte rows (BD offset, BD bytes, flags,
  rate)) and a type-2 part with the BD body (dest 0xFFF3: SPU PS-ADPCM, 16-byte frames of 28 samples, flag bit 0 =
  end, bit 2 = loop start). Rates are 8000 / 11025 / 16000 / 32000 Hz.
  stNNN.adx etc. are CRI ADX streams (4-bit ADPCM, 18-byte frames of 32 samples per channel).

GC side: the disc tree's prebuilt AIC1 banks (aica_banks.py: AicaBankHeader + per-sample AICA ADPCM images in sample
index order, each decimated to the bank's cap). The sample map pairs every GC wavetable sample with a PS2 VAG by
envelope correlation and duration (the two versions hold the same sound set in a different order). The PS2 PCM is
resampled to the GC sample's AICA rate and length and re-encoded IN PLACE: same header, same sizes, same offsets, so
the frozen AICA layout and every file size stay identical. A GC sample with no PS2 match keeps its GC bytes and is
reported (GC-in-use count).

usage:
  ps2_audio.py banks --tree DISCTREE --ps2 DIR --out OVERLAY [--files spec,...] [--json MAP] [--level gc|ps2] [--jobs N]
      [--dsp]  (snd28: banks the runtime converts at load keep their GC DSP-ADPCM container; the PS2 PCM is
                re-encoded into it in place with the sample's own coefficients: same sizes, same AICA path)
  ps2_audio.py streams --tree DISCTREE --ps2 DIR --out OVERLAY [--json MAP]
  ps2_audio.py music --tree DISCTREE --ps2 DIR --out OVERLAY [--json MAP]  (PS2 songs into bio4midi.dat, ps2_music.py)
  ps2_audio.py afs --iso PS2ISO --out DIR [patterns]        (BIO4DAT.AFS entries, default *.snd *.adx)
  tools/d367/ps2snd24-regen.sh rebuilds the whole data set from a final disc in one command

Game data never enters the repository: the tree, the PS2 directory and the overlay are private.
"""
import argparse
import json
import math
import os
import struct
import sys
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import aica_banks as ab  # noqa: E402

# ---------------------------------------------------------------- PS2 .snd
PSX_F = ((0, 0), (60, 0), (115, -52), (98, -55), (122, -60))


def snd_parts(d, base=0):
    out = []
    p = base + 0x20
    while p + 32 <= len(d):
        e = struct.unpack_from('<8I', d, p)
        p += 32
        if e[0] == 0xFFFFFFFF:
            break
        out.append(e)
    return out


def vagi(hd):
    i = hd.find(b'Vagi')
    if i < 0:
        return []
    last = struct.unpack_from('<i', hd, i + 8)[0]
    return [struct.unpack_from('<4I', hd, i + 16 + 16 * k) for k in range(last + 1)]


def vag_decode(bd, off, size):
    """PS-ADPCM -> (s16 list, loop start sample or None)."""
    out, h1, h2, loop = [], 0, 0, None
    p, end = off, min(off + size, len(bd))
    app = out.append
    while p + 16 <= end:
        sf, fl = bd[p], bd[p + 1]
        sh, f = sf & 0xF, (sf >> 4) & 7
        c1, c2 = PSX_F[f if f <= 4 else 0]
        if fl & 4 and loop is None:
            loop = len(out)
        for k in range(28):
            b = bd[p + 2 + (k >> 1)]
            n = (b >> 4) if (k & 1) else (b & 0xF)
            if n >= 8:
                n -= 16
            v = ((n << 12) >> sh) + ((h1 * c1 + h2 * c2 + 32) >> 6)
            v = 32767 if v > 32767 else (-32768 if v < -32768 else v)
            h2, h1 = h1, v
            app(v)
        p += 16
        if fl & 1:
            break
    return out, loop


def _chunk(hd, name):
    i = hd.find(name)
    if i < 0:
        return None, -1
    size, last = struct.unpack_from('<Ii', hd, i + 4)
    return hd[i:i + size], last


def hd_key_vag(hd):
    """{(program, key): vagi index} of a PS2 HD bank. Prog: u32 offsets (chunk-relative) per program; a program is
    an 8-byte header (region count - 1 first) and 14-byte regions (lo key +2, hi key +3, Smpl index u16 +12).
    Smpl: 12-byte rows (Vagi index u16 +10; all 0xFF = no set)."""
    prog, plast = _chunk(hd, b'Prog')
    smpl, slast = _chunk(hd, b'Smpl')
    if prog is None or smpl is None:
        return {}
    sv = {}
    for k in range(slast + 1):
        row = smpl[16 + 12 * k:16 + 12 * k + 12]
        if len(row) == 12 and row != bytes([0xFF]) * 12:
            sv[k] = struct.unpack_from('<H', row, 10)[0]
    out = {}
    for p in range(plast + 1):
        po = struct.unpack_from('<I', prog, 16 + 4 * p)[0]
        if po == 0xFFFFFFFF or po + 8 > len(prog):
            continue
        nreg = prog[po] + 1
        for r in range(nreg):
            ro = po + 8 + 14 * r
            if ro + 14 > len(prog):
                break
            lo, hi = prog[ro + 2], prog[ro + 3]
            si = struct.unpack_from('<H', prog, ro + 12)[0]
            if si in sv:
                for key in range(lo, hi + 1):
                    out.setdefault((p, key), sv[si])
    return out


def ps2_blocks(path):
    """{GC block index: dict(se=SE table bytes, keymap, vags=[(name, pcm, rate, loop)])} of a PS2 .snd. Parts are
    grouped by (sndType, sndNo) like the GC blocks: SE table (dest 0xFFF4), HD (0xFFF2), BD (0xFFF3)."""
    d = open(path, 'rb').read()
    grp = {}
    for (typ, size, dest, ofs, st, arg, no, x) in snd_parts(d):
        g = grp.setdefault(ab.block_index(st, no), {})
        blob = d[ofs:ofs + size]
        if typ == 1 and blob[:4] == b'Head':
            g['hd'] = blob
        elif typ == 1 and (dest & 0xFFFF) == 0xFFF4:
            g['se'] = blob
        elif typ == 2:
            g['bd'] = blob
    out = {}
    for t, g in grp.items():
        if 'hd' not in g or 'bd' not in g:
            continue
        vs = []
        for j, (o, s_, fl, rate) in enumerate(vagi(g['hd'])):
            pcm, loop = vag_decode(g['bd'], o, s_)
            vs.append(('%s:%d:%d' % (os.path.basename(path), t, j), pcm, rate or 1, loop))
        out[t] = dict(se=g.get('se', b''), keymap=hd_key_vag(g['hd']), vags=vs)
    return out


def ps2_vags(path):
    return [v for b in ps2_blocks(path).values() for v in b['vags'] if v[1]]


def gc_cue_samples(d, t, mo, ms):
    """[(cue, sample index or None, SIT flag)] of a GC ISS block: SIT prog = instrument << 8 | key -> the DLS key
    region's sample (snd_iss3.cpp iss_ax_set_wt_ptr)."""
    m = d[mo:mo + ms]
    base = 0 if t in (3, 4) else struct.unpack_from('<I', m, 0)[0]
    num, dls, sit, seq = struct.unpack_from('<4I', m, base)
    wt = base + dls
    x0, inst, rgn, art, smp, adp = struct.unpack_from('<6I', m, wt)
    # WTINST is 128 u16 key regions, but a bank stores only the keys it uses (the region table follows at once)
    out = []
    for k in range(num):
        so = base + sit + 24 * k
        if so + 24 > len(m):
            break
        prog = struct.unpack_from('<H', m, so)[0]
        flag = struct.unpack_from('<H', m, so + 0x16)[0]
        si = None
        ko = wt + inst + 256 * (prog >> 8) + 2 * (prog & 0xFF)
        if not flag & 0x8000 and not flag & 0x4 and (prog & 0xFF) < 128 and ko + 2 <= wt + rgn:
            ri = struct.unpack_from('<H', m, ko)[0]
            if ri != 0xFFFF and wt + rgn + 24 * ri + 24 <= len(m):
                si = struct.unpack_from('<I', m, wt + rgn + 24 * ri + 20)[0]
        out.append((k, si, flag))
    return out


def gc_key_samples(d, t, mo, ms):
    """{(instrument, key): GC sample} over every stored WTINST key region of a block."""
    m = d[mo:mo + ms]
    base = 0 if t in (3, 4) else struct.unpack_from('<I', m, 0)[0]
    num, dls, sit, seq = struct.unpack_from('<4I', m, base)
    wt = base + dls
    x0, inst, rgn, art, smp, adp = struct.unpack_from('<6I', m, wt)
    nrgn = (art - rgn) // 24 if art > rgn else 0
    out = {}
    for p in range(max(1, (rgn - inst + 255) // 256)):
        for k in range(128):
            ko = wt + inst + 256 * p + 2 * k
            if ko + 2 > wt + rgn:
                break
            ri = struct.unpack_from('<H', m, ko)[0]
            if ri != 0xFFFF and ri < nrgn:
                out[(p, k)] = struct.unpack_from('<I', m, wt + rgn + 24 * ri + 20)[0]
    return out


def gc_cue_progs(d, t, mo, ms):
    m = d[mo:mo + ms]
    base = 0 if t in (3, 4) else struct.unpack_from('<I', m, 0)[0]
    num, dls, sit, seq = struct.unpack_from('<4I', m, base)
    return [struct.unpack_from('<H', m, base + sit + 24 * k)[0] for k in range(num)
            if base + sit + 24 * k + 24 <= len(m)]


def ps2_cue_vags(blk):
    """[cue -> vagi index or None] of a PS2 block's SE table (28-byte rows, prog u16 first = program << 8 | key)."""
    se, km = blk['se'], blk['keymap']
    out = []
    for k in range(len(se) // 28):
        prog = struct.unpack_from('<H', se, 28 * k)[0]
        out.append(km.get((prog >> 8, prog & 0xFF)))
    return out


# ---------------------------------------------------------------- ADX
def adx_decode(path, limit=None):
    """CRI ADX (types 3, linear prediction) -> ([channel s16 lists], rate, loop start sample or None)."""
    d = open(path, 'rb').read()
    assert d[0] == 0x80, path
    ofs = struct.unpack_from('>H', d, 2)[0] + 4
    enc, bs, bits, ch = d[4], d[5], d[6], d[7]
    rate, total = struct.unpack_from('>II', d, 8)
    cutoff = struct.unpack_from('>H', d, 12 + 4)[0]
    ver = d[0x12]
    loop = None
    if ver == 3 and struct.unpack_from('>I', d, 0x18)[0]:
        loop = struct.unpack_from('>I', d, 0x1C)[0]
    elif ver == 4 and struct.unpack_from('>I', d, 0x24)[0]:
        loop = struct.unpack_from('>I', d, 0x28)[0]
    a = math.sqrt(2.0) - math.cos(2 * math.pi * cutoff / rate)
    b = math.sqrt(2.0) - 1.0
    c = (a - math.sqrt((a + b) * (a - b))) / b
    c1 = int(math.floor(c * 8192))
    c2 = int(math.floor(c * c * -4096))
    spf = (bs - 2) * 8 // bits
    chans = [[] for _ in range(ch)]
    hist = [[0, 0] for _ in range(ch)]
    p = ofs
    n = 0
    want = total if limit is None else min(total, limit)
    while n < want and p + bs * ch <= len(d):
        for c_ in range(ch):
            fr = d[p:p + bs]
            p += bs
            scale = struct.unpack_from('>H', fr, 0)[0] & 0x1FFF
            h1, h2 = hist[c_]
            out = chans[c_]
            for k in range(spf):
                byte = fr[2 + (k >> 1)]
                nib = (byte >> 4) if not (k & 1) else (byte & 0xF)
                if nib >= 8:
                    nib -= 16
                v = nib * (scale + 1) + ((c1 * h1 + c2 * h2) >> 12)
                v = 32767 if v > 32767 else (-32768 if v < -32768 else v)
                h2, h1 = h1, v
                out.append(v)
            hist[c_] = [h1, h2]
        n += spf
    return [c_[:want] for c_ in chans], rate, loop


# ---------------------------------------------------------------- resampling
PHASES = 128
HALF = 10


def _kernel(fc):
    """Kaiser-windowed sinc low-pass (cutoff fc of the source Nyquist) at PHASES fractional phases; returns (half
    width in source samples, rows of 2*half taps for source offsets -half+1 .. half)."""
    half = int(math.ceil(HALF / fc))
    beta = 8.0
    i0b = ab._bessel_i0(beta)
    tab = []
    for ph in range(PHASES):
        frac = ph / PHASES
        row = []
        for k in range(-half + 1, half + 1):
            x = k - frac
            s = fc if x == 0 else math.sin(math.pi * fc * x) / (math.pi * x)
            r = x / half
            w = ab._bessel_i0(beta * math.sqrt(1 - r * r)) / i0b if abs(r) < 1 else 0.0
            row.append(s * w)
        sm = sum(row) or 1.0
        tab.append([v / sm for v in row])
    return half, tab


_KCACHE = {}


def resample(src, r_in, r_out, n_out, loop=None, stretch=1.0):
    """src (r_in Hz) -> n_out samples at r_out Hz; output time t reads source time t * stretch. loop = source loop
    start (reads past the end wrap there), else silence past the end."""
    step = r_in / r_out * stretch
    fc = round(min(1.0, 1.0 / step) * 0.95, 3)
    if fc not in _KCACHE:
        _KCACHE[fc] = _kernel(fc)
    half, tab = _KCACHE[fc]
    n = len(src)
    wrap = loop is not None and 0 <= loop < n
    out = []
    app = out.append
    for i in range(n_out):
        t = i * step
        k0 = int(t)
        row = tab[int((t - k0) * PHASES) % PHASES]
        acc = 0.0
        base = k0 - half + 1
        if base >= 0 and base + 2 * half <= n:
            for j, c in enumerate(row):
                acc += c * src[base + j]
        else:
            for j, c in enumerate(row):
                idx = base + j
                if idx < 0:
                    continue
                if idx >= n:
                    if not wrap:
                        continue
                    idx = loop + (idx - n) % (n - loop)
                acc += c * src[idx]
        v = int(round(acc))
        app(32767 if v > 32767 else (-32768 if v < -32768 else v))
    return out


# ---------------------------------------------------------------- matching
WIN = 0.010      # envelope window (s)
NPTS = 48


def features(pcm, rate):
    w = max(1, int(rate * WIN))
    env, zc = [], []
    for i in range(0, max(1, len(pcm) - w + 1), w):
        seg = pcm[i:i + w]
        env.append(math.sqrt(sum(abs(v) for v in seg) / len(seg)))
        zc.append(sum(1 for a, b in zip(seg, seg[1:]) if (a < 0) != (b < 0)) * rate / len(seg))
    return dict(dur=len(pcm) / rate, env=env, zc=zc, rms=math.sqrt(sum(v * v for v in pcm) / max(1, len(pcm))))


def _norm(seq, npts=NPTS):
    if not seq:
        return [0.0] * npts
    return [seq[min(len(seq) - 1, int(i * len(seq) / npts))] for i in range(npts)]


def _corr(a, b):
    n = len(a)
    ma, mb = sum(a) / n, sum(b) / n
    va = sum((x - ma) ** 2 for x in a)
    vb = sum((y - mb) ** 2 for y in b)
    if va <= 0 or vb <= 0:
        return 0.0
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / math.sqrt(va * vb)


def score(g, p, dtol=0.25):
    dr = min(g['dur'], p['dur']) / max(g['dur'], p['dur'], 1e-6)
    if dr < 1 - dtol:
        return 0.0
    ce = _corr(_norm(g['env']), _norm(p['env']))
    # brightness: zero-crossing rate profile over the loud part (both capped at the GC Nyquist of the AICA rate)
    cz = _corr(_norm(g['zc']), _norm(p['zc']))
    return max(0.0, (0.7 * ce + 0.3 * cz)) * dr * dr


def assign(gfeat, pfeat, floor=0.55, reuse=0.80, dtol=0.25):
    """{gc index: (ps2 index, score)}: one-to-one greedy on score, then reuse of a PS2 sample for the leftovers when
    the score is high (the GC keeps duplicate takes the PS2 shares)."""
    pairs = []
    for gi, g in enumerate(gfeat):
        for pi, p in enumerate(pfeat):
            s = score(g, p, dtol)
            if s >= floor:
                pairs.append((s, gi, pi))
    pairs.sort(reverse=True)
    got, used = {}, set()
    for s, gi, pi in pairs:
        if gi not in got and pi not in used:
            got[gi] = (pi, s)
            used.add(pi)
    for s, gi, pi in pairs:
        if gi not in got and s >= reuse:
            got[gi] = (pi, s)
    return got


# ---------------------------------------------------------------- GC side
def gc_blocks(d, base=0, dsp=False):
    """[(t, mo, ms, ao, header tuple, [(rate, length, sh, img_ofs, img_bytes, loop)])] of the AIC1 banks.
    dsp (lane snd28, 10-28): also the banks that are NOT prebuilt (type-2 part still the GC DSP-ADPCM image, converted
    by audio_aica.cpp blk_begin at load); their header is a dict {'dsp': True, 'coefs': [coef table per sample]}, sh 0,
    img_ofs the sample's first DSP frame and img_bytes its whole frames (8 bytes per 14 samples)."""
    out = []
    for (t, mo, ms, ao, asz) in ab.sound_blocks(d, base) or []:
        if struct.unpack_from('<I', d, ao)[0] != ab.MAGIC:
            if dsp:
                table, samples, coefs = ab.wavetable(d, t, mo, ms)
                loops = ab.sample_loops(d, t, mo, ms, len(samples))
                smp, cs = [], []
                for si, (fmt, rate, offset, length, ai) in enumerate(samples):
                    p = ao + offset // 2
                    # the part size is not padded to a whole frame: the last sample's final frame may be cut short
                    nb = max(0, min((length + 13) // 14 * 8, ao + asz - p))
                    smp.append((rate, length, 0, p, nb, loops.get(si)))
                    cs.append(coefs[ai])
                if smp and all(nb >= 8 * ((length - 1) // 14) + 1 for (_r, length, _s, _p, nb, _lp) in smp):
                    out.append((t, mo, ms, ao, {'dsp': True, 'coefs': cs}, smp))
            continue
        h = ab.HDR.unpack_from(d, ao)
        cap = h[2]
        table, samples, coefs = ab.wavetable(d, t, mo, ms)
        loops = ab.sample_loops(d, t, mo, ms, len(samples))
        p = ao + ab.HDR_SIZE
        smp = []
        for si, (fmt, rate, offset, length, ai) in enumerate(samples):
            sh = ab.sample_shift(rate, length, cap)
            nb = ab.sample_bytes(length, sh)
            smp.append((rate, length, sh, p, nb, loops.get(si)))
            p += nb
        out.append((t, mo, ms, ao, h, smp))
    return out


def dsp_encode(x, coef):
    """s16 list -> GC DSP-ADPCM frames (8 bytes per 14 samples, header byte = predictor << 4 | scale exponent), decoded
    by aica_banks.dsp_decode / audio_aica.cpp exactly: the history starts at the coef table's yn1 / yn2 like theirs.
    Per frame: each of the 8 predictor pairs at the scale its open-loop residual needs (and one above), closed-loop
    quantisation, least squared error wins."""
    a, (gain, ps, yn1, yn2, lps, ly1, ly2) = coef
    h1 = yn1 - 65536 if yn1 >= 32768 else yn1
    h2 = yn2 - 65536 if yn2 >= 32768 else yn2
    out = bytearray()
    n = len(x)
    for f0 in range(0, n, 14):
        fr = list(x[f0:f0 + 14])
        fr += [0] * (14 - len(fr))
        best = None
        for idx in range(8):
            c1, c2 = a[2 * idx], a[2 * idx + 1]
            # open-loop residual on the source itself -> starting scale
            p1, p2, mx = h1, h2, 0
            for v in fr:
                r = v - ((1024 + c1 * p1 + c2 * p2) >> 11)
                if r < 0:
                    r = -r
                if r > mx:
                    mx = r
                p2, p1 = p1, v
            s = 0
            while s < 12 and mx > 7 * (1 << s):
                s += 1
            for sc in (s, s + 1):
                if sc > 12 or (best is not None and sc > best[0] + 1 and idx):
                    continue
                scale = 1 << sc
                q1, q2, err, nibs = h1, h2, 0, []
                for v in fr:
                    pred = (1024 + c1 * q1 + c2 * q2) >> 11
                    nb = v - pred
                    nb = (nb + (scale >> 1)) // scale if nb >= 0 else -((-nb + (scale >> 1)) // scale)
                    nb = -8 if nb < -8 else 7 if nb > 7 else nb
                    y = nb * scale + pred
                    y = -32768 if y < -32768 else 32767 if y > 32767 else y
                    err += (v - y) * (v - y)
                    if best is not None and err >= best[1]:
                        break
                    nibs.append(nb)
                    q2, q1 = q1, y
                else:
                    if best is None or err < best[1]:
                        best = (sc, err, idx, nibs, q1, q2)
        sc, err, idx, nibs, h1, h2 = best
        out.append((idx << 4) | sc)
        for k in range(0, 14, 2):
            out.append(((nibs[k] & 0xF) << 4) | (nibs[k + 1] & 0xF))
    return bytes(out)


def ps2_sources(spec, ps2dir):
    name = spec.split('#')[0]
    b = os.path.splitext(os.path.basename(name))[0].lower()
    if name == 'etc/core.das':
        c = ['core.snd']
    elif name == 'bgm/bio4midi.dat':
        # music: the PS2 splits the songs differently (miNNN_a / _b); every song's instruments are candidates
        c = sorted(f for f in os.listdir(ps2dir) if f.startswith('mi') and f.endswith('.snd'))
    elif name == 'bgm/doorse.dat':
        # gcleft26 10-27 (sound plan A): the PS2 has no door-sound file; its door sounds sit in the resident and room
        # banks. Matched by sound like a stub bank (Leon's, the core and every chapter-1 room bank)
        c = ['pl00.snd', 'core.snd'] + sorted(x for x in os.listdir(ps2dir) if x.startswith('r1') and x.endswith('.snd'))
        STUB_SPECS.add(spec)
    else:
        c = [b + '.snd']
        # wep19-26 (10-26): a PS2 bank that is only a stub (every part type 0xFFFFFFFE, sndType 8 arg 0x3d: no bank of
        # its own; wep16 / wep19 / wep27 / wep30 / wep41 / wep42) plays its sounds from the resident or room banks
        # (PS2 wep19's grenade sound is in the room banks' block 6, e.g. r105.snd VAG 23, 1.806 s like the GC sample):
        # match the GC samples by sound against Leon's, the core and every chapter-1 room bank (r1*.snd)
        f = os.path.join(ps2dir, c[0])
        if os.path.exists(f) and is_stub(open(f, 'rb').read()):
            c = ['pl00.snd', 'core.snd'] + sorted(x for x in os.listdir(ps2dir) if x.startswith('r1') and x.endswith('.snd'))
            STUB_SPECS.add(spec)
        # snd28 (10-28): a partner / costume bank (plNN) whose PS2 bank is a stub (pl02, pl04) or absent (pl07, pl12):
        # matched by sound like a stub, against the resident, chapter-1 room AND every other PS2 player bank
        if b.startswith('pl') and (not os.path.exists(f) or spec in STUB_SPECS):
            c = ['pl00.snd', 'core.snd'] + sorted(x for x in os.listdir(ps2dir) if x.endswith('.snd') and (
                x.startswith('r1') or (x.startswith('pl') and x != 'pl00.snd')))
            STUB_SPECS.add(spec)
    return [os.path.join(ps2dir, x) for x in c if os.path.exists(os.path.join(ps2dir, x))]


STUB_SPECS = set()   # specs whose PS2 bank is a stub: matched by sound against every block of the resident banks


def is_stub(d):
    parts = snd_parts(d)
    return bool(parts) and all(e[0] == 0xFFFFFFFE for e in parts)


def map_block(d, t, mo, ms, smp, pbs, gfeat, cross=False):
    """{GC sample: (block no, vagi, score, how)}: by cue first (the same cue numbers on both versions: GC SIT k and
    PS2 SE row k resolve to a GC sample and a PS2 VAG; majority vote over the cues of a sample), then by sound
    (envelope + duration) for samples no cue reaches, among the PS2 VAGs no cue claimed."""
    gcues = gc_cue_samples(d, t, mo, ms) if t not in (3, 4) and not cross else []   # cross: other banks' cue numbers mean other sounds
    votes = {}
    for bi, pb in enumerate(pbs):
        pcues = ps2_cue_vags(pb)
        for (k, gs, flag) in gcues:
            if gs is None or k >= len(pcues) or pcues[k] is None or gs >= len(smp):
                continue
            if pcues[k] >= len(pb['vags']) or not pb['vags'][pcues[k]][1]:
                continue
            votes.setdefault(gs, {}).setdefault((bi, pcues[k]), 0)
            votes[gs][(bi, pcues[k])] += 1
    got = {}
    for gs, v in votes.items():
        (bi, pv), n = max(v.items(), key=lambda kv: kv[1])
        got[gs] = (bi, pv, round(n / sum(v.values()), 3), 'cue')
    claimed = {(g[0], g[1]) for g in got.values()}
    rest = [(bi, j) for bi, pb in enumerate(pbs) for j, v in enumerate(pb['vags']) if v[1] and (bi, j) not in claimed]
    left = [i for i in range(len(smp)) if i not in got]
    if rest and left:
        pfeat = [features(pbs[bi]['vags'][j][1], pbs[bi]['vags'][j][2]) for (bi, j) in rest]
        music = t in (3, 4)
        sub = assign([gfeat[i] for i in left], pfeat, floor=0.5 if music else 0.75, reuse=0.5 if music else 2.0,
                     dtol=0.03 if music else 0.25)
        for li, (pi, sc) in sub.items():
            got[left[li]] = (rest[pi][0], rest[pi][1], round(sc, 3), 'sound')
    return got


def set_loops(d, mo, ms, t, si, start, length):
    """Write a loop (GC sample units) into every wavetable region of sample `si` that loops (in place, MRAM part)."""
    m = bytes(d[mo:mo + ms])
    base = 0 if t in (3, 4) else struct.unpack_from('<I', m, 0)[0]
    num, dls, sit, seq = struct.unpack_from('<4I', m, base)
    wt = base + dls
    offs = struct.unpack_from('<6I', m, wt)
    rgn = offs[2]
    later = [o for o in offs[1:] if o > rgn]
    for i in range((min(later) - rgn) // 24 if later else 0):
        p = wt + rgn + 24 * i
        unity, kg, fine, attn, lstart, llen, art, sidx = struct.unpack_from('<BBhiIIII', m, p)
        if sidx == si and llen:
            struct.pack_into('<II', d, mo + p + 8, start, max(16, length))


def convert_spec(args):
    spec, tree, ps2dir, out, level = args[:5]
    dsp = len(args) > 5 and args[5]
    path, bases = ab.archive_bases(tree, spec)
    d = bytearray(open(path, 'rb').read())
    srcs = ps2_sources(spec, ps2dir)
    pblocks = {}
    for src in srcs:
        for t, pb in ps2_blocks(src).items():
            pblocks.setdefault(t, []).append(pb)
    rep = dict(spec=spec, ps2=[os.path.basename(x) for x in srcs], blocks=[])
    touched = []
    for base in bases:
        for (t, mo, ms, ao, h, smp) in gc_blocks(bytes(d), base, dsp):
            isdsp = isinstance(h, dict)
            cap = 0 if isdsp else h[2]
            gfeat = []
            for si, (rate, length, sh, p, nb, loop) in enumerate(smp):
                n = (length + (1 << sh) - 1) >> sh
                if isdsp:
                    gfeat.append(features(ab.dsp_decode(bytes(d[p:p + nb]) + bytes(8), 0, length, h['coefs'][si], None), rate))
                else:
                    gfeat.append(features(ab.yamaha_decode(bytes(d[p:p + nb]), n), rate >> sh))
            cross = spec in STUB_SPECS
            pbs = pblocks.get(t, []) if t not in (3, 4) and not cross else [pb for v in pblocks.values() for pb in v]
            got = map_block(bytes(d), t, mo, ms, smp, pbs, gfeat, cross) if pbs else {}
            rows = []
            for si, (rate, length, sh, p, nb, loop) in enumerate(smp):
                row = dict(i=si, rate=rate, len=length, dur=round(length / rate, 3))
                if si not in got:
                    row['ps2'] = None
                    rows.append(row)
                    continue
                bi, pv, sc, how = got[si]
                name, pcm, prate, ploop = pbs[bi]['vags'][pv]
                if isdsp and max(map(abs, pcm), default=0) < 2:
                    # snd28: the cue resolves to a PS2 placeholder (a silent ~0.02 s VAG in the costume banks); writing
                    # it would mute a sound the game plays today, so the GC sample stays (listed as kept GC)
                    row.update(ps2=None, note='PS2 cue VAG %s is silent (placeholder)' % name)
                    rows.append(row)
                    continue
                r_out = rate >> sh
                n_out = (length + (1 << sh) - 1) >> sh
                p_out = int(len(pcm) * r_out / prate)
                stretch, lp, how_loop = 1.0, None, None
                if loop:
                    ratio = (len(pcm) / prate) / (length / rate)
                    if ploop is not None and p_out <= n_out:
                        # the PS2 take and its own loop: the GC regions of this sample get the PS2 loop points
                        ls = int(round(ploop * rate / prate))
                        le = min(length, int(round(len(pcm) * rate / prate)))
                        set_loops(d, mo, ms, t, si, ls, le - ls)
                        lp, how_loop = ploop, 'ps2 loop'
                    elif 0.97 <= ratio <= 1.03:
                        # same length: fit the take to the GC length exactly, keep the GC loop
                        stretch = ratio
                        lp = int(loop[0] / rate * prate * stretch)
                        how_loop = 'gc loop, stretch %.3f' % ratio
                    elif ploop is None and p_out <= n_out:
                        # a PS2 one-shot take where the GC loops: loop the whole PS2 take
                        le = min(length, int(round(len(pcm) * rate / prate)))
                        set_loops(d, mo, ms, t, si, 0, le)
                        lp, how_loop = 0, 'ps2 take looped whole'
                    else:
                        lp = ploop if ploop is not None else int(loop[0] / rate * prate)
                        how_loop = 'gc loop, PS2 take longer: trimmed'
                    lp = max(0, min(len(pcm) - 1, lp))
                x = resample(pcm, prate, r_out, n_out, lp, stretch)
                if not loop and p_out < n_out:
                    x[p_out:] = [0] * (n_out - p_out)
                xr = math.sqrt(sum(v * v for v in x[:max(1, min(p_out, n_out))]) / max(1, min(p_out, n_out)))
                row['rms_ps2_over_gc'] = round(xr / max(1.0, gfeat[si]['rms']), 3)
                if level == 'gc' and xr > 1:
                    g = min(4.0, max(0.25, gfeat[si]['rms'] / xr))
                    x = [max(-32768, min(32767, int(round(v * g)))) for v in x]
                    row['gain'] = round(g, 3)
                if how_loop:
                    row['loop'] = how_loop
                enc = dsp_encode(x, h['coefs'][si]) if isdsp else ab.yamaha_encode(x)
                enc = enc[:nb] + bytes(nb - min(nb, len(enc)))
                d[p:p + nb] = enc
                row['sim'] = round(score(gfeat[si], features(pcm, prate)), 3)
                row.update(ps2=name, how=how, score=sc, ps2_dur=round(len(pcm) / prate, 3), ps2_rate=prate)
                rows.append(row)
            if smp:
                touched.append((ao, smp[-1][3] + smp[-1][4]))
            rep['blocks'].append(dict(t=t, name=ab.BLOCK_NAMES.get(t, 'EM%d' % (t - 8)), cap=cap,
                                      samples=len(smp), mapped=sum(1 for r in rows if r['ps2']),
                                      kept_gc=sum(1 for r in rows if not r['ps2']), rows=rows))
    rep['touched'] = touched
    rep['bytes'] = bytes(d) if '#' in spec else None
    if '#' not in spec:
        dst = os.path.join(out, spec)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, 'wb') as f:
            f.write(d)
    return rep


CH1 = ['etc/core.das', 'em/pl00.drs', 'em/pl08.drs', 'em/wep02.drs', 'ss/cmn/title.snd', 'bgm/bio4midi.dat#*']


def ch1_specs(tree):
    specs = list(CH1) + ['em/' + w.split('/')[-1] for w in ab.WEAPONS]
    for r in sorted(ab.ROOMS):
        if r.startswith('r1') or r in ('r200',):
            specs += ab.ROOMS[r]
    seen, out = set(), []
    for s in specs:
        if s not in seen and os.path.exists(os.path.join(tree, s.split('#')[0])):
            seen.add(s)
            out.append(s)
    return out


def cmd_banks(a):
    specs = []
    for sp in (a.files.split(',') if a.files else ch1_specs(a.tree)):
        if sp.endswith('#*'):
            specs += ['%s#%d' % (sp[:-2], i) for i in range(len(ab.archive_bases(a.tree, sp)[1]))]
        else:
            specs.append(sp)
    # one job per file (container specs of one file run in one job, serially)
    with ProcessPoolExecutor(a.jobs) as ex:
        reps = list(ex.map(convert_spec, [(s, a.tree, a.ps2, a.out, a.level, a.dsp) for s in specs]))
    merged = {}
    for r in reps:
        data = r.pop('bytes')
        if data is None:
            continue
        name = r['spec'].split('#')[0]
        if name not in merged:
            merged[name] = bytearray(open(os.path.join(a.tree, name), 'rb').read())
        for (x, y) in r['touched']:
            merged[name][x:y] = data[x:y]
    for name, data in merged.items():
        dst = os.path.join(a.out, name)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, 'wb') as f:
            f.write(data)
    tot = dict(samples=0, mapped=0, kept_gc=0)
    for r in reps:
        for b in r['blocks']:
            for k in tot:
                tot[k] += b[k]
            print('  %-22s %-5s cap %5d  samples %3d  PS2 %3d  GC kept %3d   <- %s' % (
                r['spec'], b['name'], b['cap'], b['samples'], b['mapped'], b['kept_gc'], ','.join(r['ps2'])[:60]))
    print('total', tot)
    if a.json:
        with open(a.json, 'w') as f:
            json.dump(dict(total=tot, files=reps), f, indent=1)


# ---------------------------------------------------------------- streams
def adx_header(path):
    with open(path, 'rb') as f:
        h = f.read(0x40)
    if len(h) < 0x38 or h[0] != 0x80:
        return None
    rate, total = struct.unpack_from('>II', h, 8)
    out = dict(ch=h[7], rate=rate, total=total, dur=total / rate if rate else 0, loop=None)
    if h[0x12] == 4:
        fl, ls, lsb, le, leb = struct.unpack_from('>5I', h, 0x24)
        if fl == 1 and ls < le <= total:
            out['loop'] = (ls, le)
    return out


def _mono8k(chans, rate, start_s, secs):
    a, b = int(start_s * rate), int((start_s + secs) * rate)
    mix = [sum(c[i] for c in chans) // len(chans) for i in range(a, min(b, len(chans[0])))]
    return resample(mix, rate, 4000, int(len(mix) * 4000 / rate))


def _xcorr(a, b, maxlag=400):
    n = min(len(a), len(b)) - maxlag
    if n < 200:
        return 0.0
    best = 0.0
    for lag in range(-maxlag, maxlag + 1, 2):
        s_ = ea = eb = 0
        for i in range(maxlag, n):
            x, y = a[i], b[i + lag]
            s_ += x * y
            ea += x * x
            eb += y * y
        if ea and eb:
            best = max(best, s_ / math.sqrt(ea * eb))
    return best


def stream_match(args):
    """(entry index, ADX path or None, xcorr, how) for one aica_str.dat entry: candidates are the ADX whose length
    matches the GC stream (1.5 %) or, for a looping stream, whose loop starts where the GC loop starts (the PS2 may
    loop a longer body); the one whose first seconds correlate best wins. Acceptance: xcorr >= min_xcorr, or a
    near-exact length / loop start (0.1 % / 10 ms) with xcorr >= 0.25 (speech at 4 kHz correlates weakly)."""
    i, ent, g, ps2dir, adx, min_x = args
    sbb, rate, flags, nch, end, looplen, a_ofs, b_ofs = ent
    dur = end / rate
    gls = (end - looplen) / rate if flags & 1 else None
    best = (None, 0.0, None)
    for p, h in adx.items():
        if not h:
            continue
        exact = abs(h['dur'] - dur) <= max(0.001 * dur, 0.02)
        near = abs(h['dur'] - dur) <= 0.015 * dur + 0.05
        lsm = gls is not None and h['loop'] and abs(h['loop'][0] / h['rate'] - gls) <= 0.03
        lexact = lsm and abs(h['loop'][0] / h['rate'] - gls) <= 0.01
        if not (near or lsm):
            continue
        ch, ar, _ = adx_decode(p, limit=int(h['rate'] * 7))
        x = _xcorr(g, _mono8k(ch, ar, 1.0, 5.0))
        ok = x >= min_x or ((exact or lexact) and x >= 0.25)
        how = 'length' if near else 'loop start'
        if ok and x > best[1]:
            best = (p, x, how)
    return i, best[0], round(best[1], 3), best[2]


def _gc_head(d, ent):
    """The GC stream's 1..6 s as 4 kHz mono, decoded from its AICA data (2 KB blocks per channel, interleaved)."""
    sbb, rate, flags, nch, end, looplen, a_ofs, b_ofs = ent
    need = int(rate * 6)
    chans = []
    for c in range(nch):
        data = bytearray()
        blk = 0
        while len(data) * 2 < need:
            o = a_ofs + (blk * nch + c) * ab.STR_BLOCK
            data += d[o:o + ab.STR_BLOCK]
            blk += 1
        chans.append(ab.yamaha_decode(bytes(data), need))
    return _mono8k(chans, rate, 1.0, 5.0)


def cmd_streams(a):
    """Rewrite bgm/aica_str.dat with the PS2 ADX of each entry: same entries, keys, rates, lengths and loop points
    (the GC timeline, so wall-timed endings do not move); PCM from the matched ADX resampled to the entry's rate.
    An entry with no ADX match keeps its GC data."""
    src = os.path.join(a.tree, 'bgm', 'aica_str.dat')
    d = open(src, 'rb').read()
    magic, n = struct.unpack_from('<2I', d, 0)
    assert magic == ab.STR_MAGIC
    ents = [ab.STR_ENT.unpack_from(d, 16 + ab.STR_ENT.size * i) for i in range(n)]
    adx = {os.path.join(a.ps2, f): adx_header(os.path.join(a.ps2, f)) for f in sorted(os.listdir(a.ps2))
           if f.endswith('.adx')}
    jobs = [(i, e, _gc_head(d, e), a.ps2, adx, a.min_xcorr) for i, e in enumerate(ents)]
    with ProcessPoolExecutor(a.jobs) as ex:
        matches = {i: (p, x, how) for i, p, x, how in ex.map(stream_match, jobs)}
    hsz = ents[0][6]
    blobs, newents, rep = [], [], []
    pos = hsz
    for i, e in enumerate(ents):
        sbb, rate, flags, nch, end, looplen, a_ofs, b_ofs = e
        loops = flags & 1
        p, x, how = matches[i]
        row = dict(stream='%d:%d' % ((flags >> 8) & 0xFF, flags >> 16), rate=rate, seconds=round(end / rate, 2),
                   loop=bool(loops), ps2=os.path.basename(p) if p else None, xcorr=x, how=how)
        nxt = sorted([o for ee in ents for o in (ee[6], ee[7]) if o > a_ofs] + [len(d)])[0]
        if loops:
            nxt = sorted([o for ee in ents for o in (ee[6], ee[7]) if o > b_ofs] + [len(d)])[0]
        if not row['ps2']:
            body = d[a_ofs:nxt]
            newents.append(ab.STR_ENT.pack(sbb, rate, flags, nch, end, looplen, pos,
                                           pos + (b_ofs - a_ofs) if loops else 0))
            blobs.append(body)
            pos += len(body)
            rep.append(row)
            print('  stream %-6s %6.1f s  GC kept (best %s %.2f)' % (row['stream'], end / rate,
                                                                   os.path.basename(p) if p else '-', x))
            continue
        chans, arate, _ = adx_decode(p)
        chans = (chans * nch)[:nch] if len(chans) < nch else chans[:nch]
        lp = adx[p]['loop']
        if a.ps2_length and loops and lp and lp[1] / arate > end / rate * 1.02:
            # --ps2-length: the PS2 loops a longer body from the same loop start: play the PS2 length (entry end / loop
            # length). Off by default: it grows aica_str.dat (0:2 / st001: +5.1 MB) and the release disc is full
            end = int(lp[1] * rate / arate) & ~7
            looplen = (end - int(lp[0] * rate / arate)) & ~7
            row['ps2_length'] = round(end / rate, 2)
        ls = end - looplen if loops else 0
        pcm = [resample(c, arate, rate, end) for c in chans]
        A, B = [], []
        for xx in pcm:
            aa, p_, s_ = ab.yamaha_encode_state(xx[:end])
            A.append(aa)
            if loops:
                bp, bs = p_, s_
                bb = b''
                for _ in range(6):
                    bb, p2, s2 = ab.yamaha_encode_state(xx[ls:end], bp, bs)
                    if (p2, s2) == (bp, bs):
                        break
                    bp, bs = p2, s2
                B.append(bb)
        a_data = ab.interleave(A)
        b_data = ab.interleave(B) if loops else b''
        newents.append(ab.STR_ENT.pack(sbb, rate, flags, nch, end, looplen, pos, pos + len(a_data) if loops else 0))
        blobs += [a_data, b_data]
        pos += len(a_data) + len(b_data)
        row.update(ps2_seconds=round(adx[p]['dur'], 2), ps2_rate=arate)
        rep.append(row)
        print('  stream %-6s %6.1f s  <- %s (%.1f s @ %d Hz, xcorr %.2f)' % (row['stream'], end / rate, row['ps2'],
                                                                         adx[p]['dur'], arate, x))
    hdr = d[:16] + b''.join(newents)
    dst = os.path.join(a.out, 'bgm', 'aica_str.dat')
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, 'wb') as f:
        f.write(hdr + bytes(hsz - len(hdr)))
        for b_ in blobs:
            f.write(b_)
    print('streams: %d of %d from PS2 ADX; file %d -> %d bytes' % (sum(1 for r in rep if r['ps2']), len(rep), len(d),
                                                                   pos))
    if a.json:
        with open(a.json, 'w') as f:
            json.dump(rep, f, indent=1)


def _blen(looplen, nch):
    return ab.STR_BLOCK * ((looplen // 2 + ab.STR_BLOCK - 1) // ab.STR_BLOCK) * nch


def cmd_music(a):
    """bgm/bio4midi.dat with the PS2 songs (ps2_music.py): every prebuilt entry NNN with a PS2 miNNN_a.snd is rebuilt in
    place (same part sizes); others keep their GC data. Writes OUT/bgm/bio4midi.dat (same size)."""
    import ps2_music
    path, bases = ab.archive_bases(a.tree, 'bgm/bio4midi.dat#*')
    d = bytearray(open(path, 'rb').read())
    rep = []
    for i, base in enumerate(bases):
        src = os.path.join(a.ps2, 'mi%03d_a.snd' % i)
        row = dict(entry=i)
        if not os.path.exists(src):
            row['ps2'] = None
            row['why'] = 'no PS2 song'
        else:
            try:
                row.update(ps2_music.convert_entry(d, base, open(src, 'rb').read()))
                row['ps2'] = os.path.basename(src)
            except (ValueError, KeyError) as e:
                row['ps2'] = None
                row['why'] = str(e)
        rep.append(row)
        print('  bio4midi #%-2d %s' % (i, row))
    dst = os.path.join(a.out, 'bgm', 'bio4midi.dat')
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, 'wb') as f:
        f.write(d)
    print('music: %d of %d entries from PS2' % (sum(1 for r in rep if r['ps2']), len(rep)))
    if a.json:
        with open(a.json, 'w') as f:
            json.dump(rep, f, indent=1)


def cmd_afs(a):
    """Extract BIO4DAT.AFS entries matching the patterns from the PS2 ISO (isoinfo finds the AFS extent)."""
    import fnmatch
    import re
    import subprocess
    lst = subprocess.run(['isoinfo', '-l', '-i', a.iso], capture_output=True, text=True).stdout
    m = re.search(r'\s(\d+)\s+\[\s*(\d+)\s+\d+\]\s+BIO4DAT\.AFS', lst, re.I)
    base = int(m.group(2)) * 2048
    with open(a.iso, 'rb') as f:
        f.seek(base)
        hdr = f.read(8)
        assert hdr[:3] == b'AFS'
        n = struct.unpack('<I', hdr[4:8])[0]
        tab = struct.unpack('<%dI' % (2 * n + 2), f.read(8 * n + 8))
        ents = [(tab[2 * i], tab[2 * i + 1]) for i in range(n)]
        noff = tab[2 * n]
        if noff == 0:
            f.seek(base + ents[0][0] - 8)
            noff = struct.unpack('<I', f.read(4))[0]
        f.seek(base + noff)
        names = f.read(48 * n)
        os.makedirs(a.out, exist_ok=True)
        k = 0
        for i, (o, sz) in enumerate(ents):
            nm = names[48 * i:48 * i + 32].split(bytes(1))[0].decode('latin1')
            if any(fnmatch.fnmatch(nm.lower(), p) for p in a.patterns):
                f.seek(base + o)
                with open(os.path.join(a.out, nm), 'wb') as g:
                    g.write(f.read(sz))
                k += 1
    print('afs: %d of %d entries' % (k, n))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    b = sub.add_parser('banks')
    b.add_argument('--tree', required=True)
    b.add_argument('--ps2', required=True)
    b.add_argument('--out', required=True)
    b.add_argument('--files')
    b.add_argument('--json')
    b.add_argument('--level', default='ps2', choices=('gc', 'ps2'))
    b.add_argument('--jobs', type=int, default=4)
    b.add_argument('--dsp', action='store_true', help='also banks that are not prebuilt: PS2 PCM re-encoded as GC DSP-ADPCM in place (snd28)')
    s = sub.add_parser('streams')
    s.add_argument('--tree', required=True)
    s.add_argument('--ps2', required=True)
    s.add_argument('--out', required=True)
    s.add_argument('--json')
    s.add_argument('--jobs', type=int, default=4)
    s.add_argument('--min-xcorr', type=float, default=0.5)
    s.add_argument('--ps2-length', action='store_true')
    mu = sub.add_parser('music')
    mu.add_argument('--tree', required=True)
    mu.add_argument('--ps2', required=True)
    mu.add_argument('--out', required=True)
    mu.add_argument('--json')
    x = sub.add_parser('afs')
    x.add_argument('--iso', required=True)
    x.add_argument('--out', required=True)
    x.add_argument('patterns', nargs='*', default=['*.snd', '*.adx'])
    a = ap.parse_args()
    {'banks': cmd_banks, 'streams': cmd_streams, 'afs': cmd_afs, 'music': cmd_music}[a.cmd](a)


if __name__ == '__main__':
    main()
