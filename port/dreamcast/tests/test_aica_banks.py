"""tools/aica_banks.py: codec parity with platform/audio_aica.cpp and in-place bank rewriting."""
import math
import os
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools'))
import aica_banks as ab  # noqa: E402


def dsp_encode_silence_frames(n_frames):
    # DSP-ADPCM frames with scale 0 / predictor 0 and zero nibbles decode to 0.
    return bytes(8 * n_frames)


def make_archive(path, samples_len, rate):
    """A minimal DvdHeader archive: one ROOM (t=6) block, MRAM (ISS + WT) and ARAM parts."""
    n = len(samples_len)
    wt = bytearray(24)
    smp_ofs, adp_ofs = 24, 24 + 16 * n
    offs, table = 0, b''
    for ln in samples_len:
        table += struct.pack('<HHIIHH', 0, rate, offs * 2, ln, 0, 0)   # nibble address of the first frame header
        offs += (ln + 13) // 14 * 8
    wt[0:24] = struct.pack('<6I', 0, 0, 0, 0, smp_ofs, adp_ofs)
    wt += table + bytes(0x2E)
    iss = struct.pack('<4I', 1, 16, 0, 0)
    mram = struct.pack('<I', 4) + iss + bytes(wt)
    aram = dsp_encode_silence_frames(offs // 8)
    hdr = bytearray(b'\xca\xb6\xbe\x20' * 8)
    body_ofs = 0x20 + 32 * 3
    hdr += struct.pack('<8I', 1, len(mram), 0, body_ofs, 6, 256, 0, 0)
    hdr += struct.pack('<8I', 2, len(aram), 0, body_ofs + len(mram), 6, 256, 0, 0)
    hdr += struct.pack('<8I', 0xFFFFFFFF, 0, 0, 0, 0, 0, 0, 0)
    with open(path, 'wb') as f:
        f.write(bytes(hdr) + mram + aram)
    return body_ofs + len(mram), len(aram)


class Codec(unittest.TestCase):
    def test_sample_shift_matches_runtime_rules(self):
        self.assertEqual(ab.sample_shift(32000, 1000, 32000), 0)
        self.assertEqual(ab.sample_shift(32000, 1000, 16000), 1)
        self.assertEqual(ab.sample_shift(32000, 1000, 8000), 2)
        self.assertEqual(ab.sample_shift(11025, 200000, 32000), 2)   # AICA 16-bit LEA limit
        self.assertEqual(ab.sample_bytes(15, 0), 8)
        self.assertEqual(ab.sample_bytes(16, 1), 4)

    def test_yamaha_round_trip_snr(self):
        x = [int(12000 * math.sin(i * 0.05)) for i in range(4000)]
        enc = ab.yamaha_encode(x)
        self.assertEqual(len(enc), ab.sample_bytes(len(x), 0))
        y = ab.yamaha_decode(enc, len(x))
        sig, err = ab.energies(x, y)
        self.assertGreater(10 * math.log10(sig / err), 20.0)

    def test_decimate_truncates_like_c(self):
        self.assertEqual(ab.decimate([4, 4, -3], 1), [4, -3])
        self.assertEqual(ab.decimate([-1, -2, -1, -1, -1, -1, 0], 2), [-2, 0])   # >> floors, the tail / truncates


class AntiAlias(unittest.TestCase):
    """decimate_aa (prebuilt banks): same sample count as the runtime box, real stopband, seamless loops."""

    def test_length_invariance(self):
        for sh in (0, 1, 2, 3):
            for ln in (0, 1, 2, 3, 7, 8, 9, 100, 101, 1023, 4097):
                x = [(i * 7919) % 2001 - 1000 for i in range(ln)]
                self.assertEqual(len(ab.decimate_aa(x, sh)), len(ab.decimate(x, sh)), (sh, ln))
                self.assertEqual(len(ab.decimate_aa(x, sh, (ln // 3, ln))), len(ab.decimate(x, sh)), (sh, ln))
                self.assertEqual(ab.sample_bytes(ln, sh), ((len(ab.decimate_aa(x, sh)) + 7) // 8) * 4)

    def test_passband_and_stopband(self):
        def rms(v):
            v = v[200:-200]
            return math.sqrt(sum(a * a for a in v) / len(v))
        for sh in (1, 2, 3):
            n = 1 << sh
            low = [int(10000 * math.sin(2 * math.pi * 0.2 / n * i)) for i in range(6000 * n)]
            high = [int(10000 * math.sin(2 * math.pi * 0.7 / n * i)) for i in range(6000 * n)]   # folds to 0.3
            self.assertAlmostEqual(rms(ab.decimate_aa(low, sh)) / rms(low), 1.0, delta=0.01)
            aa = rms(ab.decimate_aa(high, sh)) / rms(high)
            box = rms(ab.decimate(high, sh)) / rms(high)
            self.assertLess(20 * math.log10(aa + 1e-9), -60.0, sh)
            self.assertGreater(box, 10 * aa)

    def test_clamps_to_s16(self):
        x = [32767, -32768] * 500 + [32767] * 1000 + [-32768] * 1000
        y = ab.decimate_aa(x, 1)
        self.assertTrue(all(-32768 <= v <= 32767 for v in y))

    def test_loop_seam_is_continuous(self):
        sh, n = 1, 2
        period = 400                                   # 4 cycles of a tone: the loop body is exactly periodic
        body = [int(12000 * math.sin(2 * math.pi * 4 * i / period)) for i in range(period)]
        intro = [(i * 7919) % 20001 - 10000 for i in range(600)]   # loud noise before the loop
        tail = [0] * 64                                  # data after the loop end (never played)
        x = intro + body + tail
        ls, le = len(intro), len(intro) + period
        y = ab.decimate_aa(x, sh, (ls, le))
        a, b = ls >> sh, le >> sh                        # what audio_aica.cpp plays: [lsa, len) looping
        played = y[a:b] * 3
        ref = ab.decimate_aa(body * 40, sh)[(period * 20) >> sh:((period * 20) >> sh) + (b - a)] * 3
        self.assertLessEqual(max(abs(p - r) for p, r in zip(played, ref)), 1)   # = the infinite periodic signal
        # without the circular wrap the samples before the seam see the tail of zeros / the intro: a click
        lin = ab.decimate_aa(x, sh)
        self.assertGreater(max(abs(p - r) for p, r in zip(lin[a:b], ref)), 100)

    def test_sample_loops_from_regions(self):
        # wavetable with 2 samples and 3 regions (region 1 loops sample 1, region 2 repeats it)
        n = 2
        rgn_ofs = 24
        regions = struct.pack('<BBhiIIII', 60, 0, 0, 0, 0, 0, 0, 0)
        regions += struct.pack('<BBhiIIII', 60, 0, 0, 0, 100, 300, 0, 1)
        regions += struct.pack('<BBhiIIII', 60, 0, 0, 0, 5, 7, 0, 1)
        art_ofs = rgn_ofs + len(regions)
        smp_ofs = art_ofs
        adp_ofs = smp_ofs + 16 * n
        wt = struct.pack('<6I', 0, 0, rgn_ofs, art_ofs, smp_ofs, adp_ofs) + regions
        wt += struct.pack('<HHIIHH', 0, 32000, 0, 500, 0, 0) * n + bytes(0x2E)
        mram = struct.pack('<I', 4) + struct.pack('<4I', 1, 16, 0, 0) + wt
        self.assertEqual(ab.sample_loops(mram, 6, 0, len(mram), n), {1: (100, 400)})


class Build(unittest.TestCase):
    def test_rewrite_in_place(self):
        with tempfile.TemporaryDirectory() as d:
            mirror, out = os.path.join(d, 'm'), os.path.join(d, 'o')
            os.makedirs(os.path.join(mirror, 'st1'))
            ao, asz = make_archive(os.path.join(mirror, 'st1', 'r100.dar'), [1400, 280], 32000)
            old = ab.ROOMS, ab.RESIDENT
            ab.ROOMS, ab.RESIDENT = {'r100': ['st1/r100.dar']}, []
            try:
                budget = ab.AICA_POOL - ab.MOVIE_RESERVE - ab.STREAM_RING
                res, per_room, uniq, slots, arena = ab.plan(mirror, ['r100'], budget)
                ab.build(mirror, out, res, per_room, uniq, slots, None, False)
            finally:
                ab.ROOMS, ab.RESIDENT = old
            src = open(os.path.join(mirror, 'st1', 'r100.dar'), 'rb').read()
            dst = open(os.path.join(out, 'st1', 'r100.dar'), 'rb').read()
            self.assertEqual(len(src), len(dst))
            self.assertEqual(src[:ao], dst[:ao])               # headers and MRAM part untouched
            h = ab.HDR.unpack_from(dst, ao)
            self.assertEqual(h[0], ab.MAGIC)
            self.assertEqual(h[2], 16000)                     # ROOM preferred cap
            self.assertEqual(h[3], ab.sample_bytes(1400, 1) + ab.sample_bytes(280, 1))
            self.assertEqual(h[7], 8)                         # room arena slot
            self.assertEqual(h[9 + 8], (h[3] + 31) & ~31)     # layout slot_bytes[8] = room arena


class Reserve(unittest.TestCase):
    def test_disc_refuses_to_eat_the_movie_reserve(self):
        with tempfile.TemporaryDirectory() as d:
            mirror = os.path.join(d, 'm')
            os.makedirs(os.path.join(mirror, 'st1'))
            make_archive(os.path.join(mirror, 'st1', 'r100.dar'), [60000, 60000], 8000)
            old = ab.ROOMS, ab.RESIDENT, ab.AICA_POOL
            ab.ROOMS, ab.RESIDENT = {'r100': ['st1/r100.dar']}, []
            ab.AICA_POOL = ab.MOVIE_RESERVE + ab.STREAM_RING + 1000   # too small even at the lowest cap
            try:
                with self.assertRaises(SystemExit):
                    ab.disc(mirror, os.path.join(d, 'out'), os.path.join(d, 'cache'), ['r100'], [], None)
            finally:
                ab.ROOMS, ab.RESIDENT, ab.AICA_POOL = old
            self.assertFalse(os.path.exists(os.path.join(d, 'out')))


class Streams(unittest.TestCase):
    def test_interleave_2k_blocks(self):
        a, b = bytes([1]) * 3000, bytes([2]) * 100
        out = ab.interleave([a, b])
        self.assertEqual(len(out), 2 * 2 * ab.STR_BLOCK)      # 2 blocks x 2 channels, zero padded
        self.assertEqual(out[:2048], a[:2048])
        self.assertEqual(out[2048:2148], b)
        self.assertEqual(out[4096:4096 + 952], a[2048:])

    def test_encoder_state_carries_over(self):
        x = [int(8000 * math.sin(i * 0.07)) for i in range(2000)]
        whole, p, s = ab.yamaha_encode_state(x)
        head, p1, s1 = ab.yamaha_encode_state(x[:1000])
        tail, p2, s2 = ab.yamaha_encode_state(x[1000:], p1, s1)
        self.assertEqual(head + tail, whole)                   # a region continues its predecessor's decoder state
        self.assertEqual((p2, s2), (p, s))


if __name__ == '__main__':
    unittest.main()
