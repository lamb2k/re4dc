import tempfile
from pathlib import Path
import struct
import unittest

from sh4_icache_trace import Replay, Symbols, runs


class TraceReplayTests(unittest.TestCase):
    def test_halfword_crosses_cache_line(self):
        replay = Replay()
        replay.run(0x8c010000, 17)
        self.assertEqual((replay.instructions, replay.fills), (17, 2))

    def test_eight_kib_conflict_and_four_kib_separation(self):
        replay = Replay()
        for pc in (0x8c010000, 0x8c012000, 0x8c010000):
            replay.run(pc, 1)
        self.assertEqual((replay.fills, replay.first, replay.conflict), (3, 2, 1))
        separated = Replay()
        for pc in (0x8c010000, 0x8c011000, 0x8c010000):
            separated.run(pc, 1)
        self.assertEqual(separated.fills, 2)

    def test_capacity_reference_is_separate(self):
        replay = Replay()
        for i in range(257):
            replay.run(0x8c010000 + 32 * i, 1)
        replay.run(0x8c010000, 1)
        self.assertEqual((replay.first, replay.capacity, replay.conflict), (257, 1, 0))

    def test_uncached_fetch_does_not_fill(self):
        replay = Replay()
        replay.run(0xac010000, 17)
        self.assertEqual((replay.fills, replay.uncached_fetches), (0, 2))

    def test_runs_ignore_data_events_and_reject_truncation(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'trace.bin'
            path.write_bytes(struct.pack('<IIII', 0x8c010000, 0x10000011, 0x8c020000, 0x20000000))
            self.assertEqual(list(runs(path)), [(0x8c010000, 17)])
            path.write_bytes(path.read_bytes() + b'\0')
            with self.assertRaises(ValueError):
                list(runs(path))

    def test_invalid_alignment_and_zero_length(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'trace.bin'
            for pc, word in ((0x8c010001, 0x10000001), (0x8c010000, 0x10000000)):
                path.write_bytes(struct.pack('<II', pc, word))
                with self.assertRaises(ValueError):
                    list(runs(path))

    def test_shared_line_symbols_are_not_independent_units(self):
        symbols = Symbols.__new__(Symbols)
        symbols.starts = [0x8c010000, 0x8c010010]
        symbols.rows = [(16, 'first'), (16, 'second')]
        self.assertEqual(symbols.lookup(0x0c010000 >> 5), 'first / second [shared line]')
        self.assertEqual(symbols.lookup(0x0c012000 >> 5), '<unresolved/fixed>')


if __name__ == '__main__':
    unittest.main()
