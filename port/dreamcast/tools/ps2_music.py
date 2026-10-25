#!/usr/bin/env python3
"""PS2 music for the AICA BGM banks (lane purge-audio24, 2026-10-24): ps2_audio.py music.

A PS2 song (BIO4DAT miNNN_a.snd, the same number as the GC bgm/bio4midi.dat entry NNN; bgm/bgmtbl.dat is the same
table on both versions) is a DvdHeader archive of four parts:
  dest 0xFFF5  a standard MIDI file (format 0, division 480, MusyX SDK text events, CC 0x66 / 0x67 loop marks)
  dest 0xFFF2  the HD bank (Prog / Smpl / Vagi), dest 0xFFF3 the BD body (SPU PS-ADPCM), dest 0xFFF1 "dbsT" (unused)
The GC entry is an archive of an MRAM part (ISS header num / dls / sit / seq, the SYN wavetable, one SIT, the
sequence: u32 track count, u32 offsets, then MIDI events with only the 0x2F / 0x51 meta events) and an ARAM part
(the prebuilt AIC1 bank, tools/aica_banks.py).

This module rebuilds an entry IN PLACE from the PS2 song: the MRAM part gets a SYN wavetable made from the HD bank
(program -> 128-key region table, regions with the Smpl base note / volume / VAG loop, articulations from the SPU ADSR,
samples = the VAGs), the GC SIT (cue settings kept) and the PS2 sequence (meta / sysex events dropped); the ARAM part
gets an AIC1 bank of the VAGs. Both parts keep their GC sizes (zero padded), so the archive, bio4midi.hed and the disc
layout do not move, and the AIC1 header keeps the frozen layout, slot and GC part size the runtime checks.
"""
import math
import struct

import aica_banks as ab
import ps2_audio as pa

SPU_HZ = 44100


# ---------------------------------------------------------------- PS2 HD bank, full
def hd_bank(hd):
    """dict(progs={p: dict(vol, pan, regions=[(lo, hi, vol, pan, smpl)])}, smpl={i: dict(adsr1, adsr2, note, fine, vol,
    pan, vag)}, vags=[(offset, bytes, flags, rate)]). Region count from the next program's offset."""
    prog, plast = pa._chunk(hd, b'Prog')
    smpl, slast = pa._chunk(hd, b'Smpl')
    sm = {}
    for k in range(slast + 1):
        row = smpl[16 + 12 * k:28 + 12 * k]
        if len(row) == 12 and row != bytes([0xFF]) * 12:
            a1, a2 = struct.unpack_from('<HH', row, 0)
            sm[k] = dict(adsr1=a1, adsr2=a2, fine=row[4], note=row[5], vol=row[6], pan=row[7],
                         vag=struct.unpack_from('<H', row, 10)[0])
    offs = [struct.unpack_from('<I', prog, 16 + 4 * p)[0] for p in range(plast + 1)]
    valid = sorted(o for o in offs if o != 0xFFFFFFFF)
    progs = {}
    for p, po in enumerate(offs):
        if po == 0xFFFFFFFF or po + 8 > len(prog):
            continue
        nxt = min([o for o in valid if o > po] + [len(prog)])
        regs = []
        for r in range((nxt - po - 8) // 14):
            ro = po + 8 + 14 * r
            row = prog[ro:ro + 14]
            if row[:4] == bytes([0xFF]) * 4:
                break
            regs.append((row[2], row[3], row[8], row[9], struct.unpack_from('<H', row, 12)[0]))
        progs[p] = dict(vol=prog[po + 2], pan=prog[po + 3], regions=regs)
    return dict(progs=progs, smpl=sm, vags=pa.vagi(hd))


# ---------------------------------------------------------------- SPU ADSR -> DLS articulation
def _spu_run(level, rate, decrease, exp, target, limit=SPU_HZ * 30):
    """Samples (at 44.1 kHz) the SPU envelope takes from `level` to `target` with this rate (0..127)."""
    if rate >= 0x7F:
        return None
    shift = rate >> 2
    base = (-8 + (rate & 3)) if decrease else (7 - (rate & 3))
    cyc = 1 << max(0, shift - 11)
    step0 = base << max(0, 11 - shift)
    n = 0
    while n < limit:
        c, st = cyc, step0
        if exp and not decrease and level > 0x6000:
            c *= 4
        if exp and decrease:
            st = (st * level) >> 15
        level += st
        n += c
        if (decrease and level <= target) or (not decrease and level >= target):
            return n
    return None


def _tc(seconds):
    if seconds is None:
        return 0x7FFFFFFF
    if seconds <= 0.0005:
        return -0x7FFFFFFF - 1  # 0x80000000: no time
    return int(round(1200.0 * math.log2(seconds) * 65536))


def articulation(adsr1, adsr2):
    """WTART bytes (0x50) from the SPU ADSR words: attack time, decay time to -96 dB, sustain level (dB x 655360),
    release time to -96 dB. Sustain-phase slopes are not modelled (the DC synth has no second decay)."""
    ar, aexp = (adsr1 >> 8) & 0x7F, adsr1 >> 15
    dr, sl = (adsr1 >> 4) & 0xF, adsr1 & 0xF
    rr, rexp = adsr2 & 0x1F, (adsr2 >> 5) & 1
    t_att = _spu_run(0, ar, False, aexp, 0x7FFF)
    sus = (sl + 1) << 11
    sus_db = 20 * math.log10(min(0x7FFF, sus) / 0x7FFF)
    t_dec = None
    if sl < 15:
        n = _spu_run(0x7FFF, dr << 2, True, 1, sus)
        if n is not None and sus_db < 0:
            t_dec = n / SPU_HZ * 96.0 / -sus_db
    n = _spu_run(0x7FFF, rr << 2, True, rexp, 33 if rexp else 0)
    t_rel = None if n is None else n / SPU_HZ * (96.0 / 60.0 if rexp else 1.0)
    vals = [0] * 20
    vals[6] = _tc(None if t_att is None else t_att / SPU_HZ)
    vals[7] = _tc(t_dec) if t_dec is not None else -0x7FFFFFFF - 1
    vals[8] = int(round(sus_db * 655360))
    vals[9] = _tc(t_rel) if t_rel is not None else _tc(0.03)
    return struct.pack('<20i', *vals)


# ---------------------------------------------------------------- MIDI
def _vlq(b, p):
    v = 0
    while True:
        c = b[p]
        p += 1
        v = (v << 7) | (c & 0x7F)
        if not c & 0x80:
            return v, p


def _wvlq(v):
    out = [v & 0x7F]
    v >>= 7
    while v:
        out.append(0x80 | (v & 0x7F))
        v >>= 7
    return bytes(reversed(out))


# What the GC sequencer accepts (src/game/snd_seq2.cpp): note off / on, control change (only these numbers), program
# change, pitch bend and the meta events 0x2F / 0x51; anything else is "SND SEQ data error" and an OSPanic (halt).
GC_CC = (0x01, 0x06, 0x26, 0x07, 0x0A, 0x0B, 0x40, 0x5B, 0x5C, 0x66, 0x67, 0x68, 0x69)
GC_STATUS = (0x80, 0x90, 0xB0, 0xC0, 0xE0)


def smf_to_gc_seq(smf):
    """The GC sequence (u32 tracks = 1, u32 offset 8, events) of a format-0 SMF: channel events with explicit status,
    meta events other than 0x51 / 0x2F and sysex dropped (their delta times carried over)."""
    assert smf[:4] == b'MThd'
    fmt, ntr, div = struct.unpack_from('>HHH', smf, 8)
    assert fmt == 0 and ntr == 1 and div == 480, (fmt, ntr, div)
    q = 14
    assert smf[q:q + 4] == b'MTrk'
    ln = struct.unpack_from('>I', smf, q + 4)[0]
    p, end = q + 8, q + 8 + ln
    out = bytearray()
    carry = 0
    run = None
    chans = {}
    stats = dict(events=0, dropped=0)
    ended = False
    while p < end:
        d, p = _vlq(smf, p)
        carry += d
        st = smf[p]
        if st == 0xFF:
            ty = smf[p + 1]
            n, p2 = _vlq(smf, p + 2)
            body = smf[p2:p2 + n]
            p = p2 + n
            if ty in (0x51, 0x2F):
                out += _wvlq(carry) + bytes([0xFF, ty]) + _wvlq(n) + body
                carry = 0
                if ty == 0x2F:
                    ended = True
                    break
            else:
                stats['dropped'] += 1
            continue
        if st in (0xF0, 0xF7):
            n, p2 = _vlq(smf, p + 1)
            p = p2 + n
            stats['dropped'] += 1
            continue
        if st & 0x80:
            run = st
            p += 1
        k = 1 if (run & 0xF0) in (0xC0, 0xD0) else 2
        data = smf[p:p + k]
        p += k
        kind = run & 0xF0
        if kind not in GC_STATUS or (kind == 0xB0 and data[0] not in GC_CC):
            stats['dropped'] += 1
            stats.setdefault('dropped_kinds', set()).add('%02x%s' % (kind, '/%02x' % data[0] if kind == 0xB0 else ''))
            continue
        if kind == 0xC0:
            chans.setdefault(run & 15, data[0])
        out += _wvlq(carry) + bytes([run]) + data
        carry = 0
        stats['events'] += 1
    if not ended:
        out += _wvlq(carry) + b'\xff\x2f\x00'
    stats['first_prog'] = chans
    stats['dropped_kinds'] = sorted(stats.get('dropped_kinds', ()))
    seq = struct.pack('<2I', 1, 8) + bytes(out)
    check_gc_seq(seq)
    return seq, stats


def check_gc_seq(seq):
    """Raise ValueError unless every event of a GC sequence is one the GC sequencer accepts."""
    p, end = 8, len(seq)
    while p < end:
        d, p = _vlq(seq, p)
        st = seq[p]
        if st == 0xFF:
            ty = seq[p + 1]
            n, p2 = _vlq(seq, p + 2)
            if ty not in (0x2F, 0x51):
                raise ValueError('meta %02x' % ty)
            p = p2 + n
            if ty == 0x2F:
                return
            continue
        if not st & 0x80 or (st & 0xF0) not in GC_STATUS:
            raise ValueError('status %02x' % st)
        k = 1 if (st & 0xF0) == 0xC0 else 2
        if (st & 0xF0) == 0xB0 and seq[p + 1] not in GC_CC:
            raise ValueError('cc %02x' % seq[p + 1])
        p += 1 + k
    raise ValueError('no end of track')


# ---------------------------------------------------------------- one entry
def convert_entry(d, base, snd, cap_max=32000):
    """Rebuild the bio4midi entry at `base` of `d` (bytearray, in place) from PS2 song bytes `snd`. Returns a report
    dict; raises ValueError when the PS2 song does not fit the entry's GC part sizes or the frozen BGM0 slot."""
    ents = pa.snd_parts(bytes(d), base)
    mram = [e for e in ents if e[0] == 1]
    aram = [e for e in ents if e[0] == 2]
    if len(mram) != 1 or len(aram) != 1:
        raise ValueError('entry is not one MRAM + one ARAM part')
    mo, ms = base + mram[0][3], mram[0][1]
    ao, asz = base + aram[0][3], aram[0][1]
    h = ab.HDR.unpack_from(bytes(d), ao)
    if h[0] != ab.MAGIC:
        raise ValueError('GC entry has no prebuilt AIC1 bank (runtime-converted): not ported')
    m = bytes(d[mo:mo + ms])
    num, dls, sit, seq = struct.unpack_from('<4I', m, 0)
    sit_bytes = m[sit:seq]
    parts = {(e[2] & 0xFFFF): snd[e[3]:e[3] + e[1]] for e in pa.snd_parts(snd)}
    hd, bd, smf = parts[0xFFF2], parts[0xFFF3], parts[0xFFF5]
    bank = hd_bank(hd)
    gseq, sstats = smf_to_gc_seq(smf)
    # samples = the VAGs
    vags = []
    for (o, s_, fl, rate) in bank['vags']:
        pcm, loop = pa.vag_decode(bd, o, s_)
        vags.append((pcm, rate, loop))
    # regions / articulations
    nprog = max(bank['progs']) + 1 if bank['progs'] else 1
    regions, arts, artkey = [], [], {}
    inst = bytearray(b'\xff\xff' * 128 * nprog)
    for p, pr in sorted(bank['progs'].items()):
        for (lo, hi, rvol, rpan, si) in pr['regions']:
            s = bank['smpl'].get(si)
            if s is None or s['vag'] >= len(vags) or not vags[s['vag']][0]:
                continue
            ak = (s['adsr1'], s['adsr2'])
            if ak not in artkey:
                artkey[ak] = len(arts)
                arts.append(articulation(*ak))
            pcm, rate, loop = vags[s['vag']]
            v = (pr['vol'] / 127.0) * (rvol / 127.0) * (s['vol'] / 127.0)
            attn = int(round(20 * math.log10(max(v, 1e-4)) * 10 * 65536))
            fine = 0 if s['fine'] in (0, 0xFF) else (s['fine'] - 256 if s['fine'] > 127 else s['fine'])
            ls, ll = (loop, len(pcm) - loop) if loop is not None else (0, 0)
            ri = len(regions)
            regions.append(struct.pack('<BBhiIIII', s['note'], 0, fine, attn, ls, ll, artkey[ak], s['vag']))
            for k in range(lo, min(hi, 127) + 1):
                if struct.unpack_from('<H', inst, 256 * p + 2 * k)[0] == 0xFFFF:
                    struct.pack_into('<H', inst, 256 * p + 2 * k, ri)
    samples = b''.join(struct.pack('<HHIIH2x', 0, rate, 0, len(pcm), 0) for (pcm, rate, loop) in vags)
    adpcm = bytes(0x2E)
    # percussion (MIDI channel 10): the program the song selects there, else program 0
    perc = sstats['first_prog'].get(9, 0)
    hdr_sz = 24
    o_inst = hdr_sz
    o_rgn = o_inst + len(inst)
    o_art = o_rgn + 24 * len(regions)
    o_smp = o_art + len(b''.join(arts))
    o_adp = o_smp + len(samples)
    wt = struct.pack('<6I', o_inst + 256 * (perc if perc < nprog else 0), o_inst, o_rgn, o_art, o_smp, o_adp) + \
        bytes(inst) + b''.join(regions) + b''.join(arts) + samples + adpcm
    new_sit = (16 + len(wt) + 31) & ~31
    new_seq = new_sit + len(sit_bytes)
    newm = bytearray(struct.pack('<4I', 1, 16, new_sit, new_seq) + wt)
    newm += bytes(new_sit - len(newm)) + sit_bytes + gseq
    if len(newm) > ms:
        raise ValueError('PS2 MRAM part %d bytes > GC part %d' % (len(newm), ms))
    # AIC1 image at the highest cap that fits the frozen BGM0 slot and the GC ARAM part
    slot = h[9 + h[7]] if h[7] < 9 else 0
    table = [(0, rate, 0, len(pcm), 0) for (pcm, rate, loop) in vags]
    cap = None
    for c in [cap_max] + [x for x in ab.CAPS if x < cap_max]:
        if ab.bank_bytes(table, c) <= min(slot, asz - ab.HDR_SIZE):
            cap = c
            break
    if cap is None:
        raise ValueError('PS2 song does not fit the BGM slot even at 8 kHz')
    img = []
    for (pcm, rate, loop) in vags:
        sh = ab.sample_shift(rate, len(pcm), cap)
        x = ab.decimate_aa(pcm, sh, (loop, len(pcm)) if loop is not None else None)
        need = ab.sample_bytes(len(pcm), sh)
        e = ab.yamaha_encode(x)
        img.append(e[:need] + bytes(need - min(need, len(e))))
    img = b''.join(img)
    fields = list(h)
    fields[2] = cap
    fields[3] = len(img)
    fields[4] = len(vags)
    fields[5] = ab.fnv1a(samples)
    newa = ab.HDR.pack(*fields) + img
    d[mo:mo + ms] = bytes(newm) + bytes(ms - len(newm))
    d[ao:ao + asz] = newa + bytes(asz - len(newa))
    return dict(progs=len(bank['progs']), regions=len(regions), arts=len(arts), samples=len(vags), cap=cap,
                image=len(img), slot=slot, mram=len(newm), mram_gc=ms, seq_events=sstats['events'],
                dropped=sstats['dropped'], dropped_kinds=sstats['dropped_kinds'], perc_prog=perc,
                seconds=round(sum(len(v[0]) / v[1] for v in vags), 2))
