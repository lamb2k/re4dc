"""Lossless host input compatibility; target runtime checks remain authoritative."""
from pathlib import Path
import struct
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from ps2_cast_host_strips import ordered_gx


def triangle_list(triangles):
    flat = [c for t in triangles for c in t]
    return struct.pack('>BH', 0x90, len(flat)) + b''.join(struct.pack('>3H', *c) for c in flat)


def strip_stream(stream):
    result, at = [], 0
    while at < len(stream) and stream[at]:
        op, n = struct.unpack_from('>BH', stream, at)
        if op != 0x98:
            raise AssertionError('not a GX strip')
        at += 3
        result.append([struct.unpack_from('>3H', stream, at+6*k) for k in range(n)])
        at += 6*n
    if any(stream[at:]):
        raise AssertionError('nonzero padding')
    return result


class HostStripsTests(unittest.TestCase):
    def test_source_adjacent_strip_keeps_full_corner_attributes_and_64_limit(self):
        corners = [(i, i+100, i+200) for i in range(100)]
        triangles = [([corners[i+1], corners[i], corners[i+2]] if i & 1 else corners[i:i+3]) for i in range(98)]
        output, proof = ordered_gx(triangle_list(triangles))
        strips = strip_stream(output)
        self.assertEqual(strips, [corners[:64], corners[62:]])
        self.assertEqual(proof['triangles'], 98)
        self.assertEqual(proof['max_strip_corners'], 64)
        self.assertEqual(len(output) % 32, 0)

    def test_uv_normal_seams_duplicates_and_source_order_remain_distinct(self):
        a, b, c, d = [(i, 0, 0) for i in range(4)]
        seam_b, seam_c = (1, 1, 0), (2, 0, 1)
        triangles = [[a, b, c], [seam_c, seam_b, d], [a, b, c]]
        output, proof = ordered_gx(triangle_list(triangles))
        self.assertEqual(strip_stream(output), triangles)
        self.assertEqual(proof['triangles'], 3)
        self.assertTrue(proof['exact_oriented_corner_sequence'])

    def test_original_array_bounds_are_checked_before_fixture_creation(self):
        data = triangle_list([[(0, 0, 0), (1, 1, 1), (2, 2, 2)]])
        ordered_gx(data, (3, 3, 3))
        for counts in ((2, 3, 3), (3, 2, 3), (3, 3, 2), (0, 3, 3), (3, 3)):
            with self.assertRaises(ValueError):
                ordered_gx(data, counts)

    def test_malformed_original_input_is_refused(self):
        valid = triangle_list([[(0, 0, 0), (1, 1, 1), (2, 2, 2)]])
        for data in (b'', b'\x98'+valid[1:], valid[:-1], valid+b'\x01', b'\x90\x00\x04'+bytes(24)):
            with self.assertRaises(ValueError):
                ordered_gx(data)


if __name__ == '__main__':
    unittest.main()
