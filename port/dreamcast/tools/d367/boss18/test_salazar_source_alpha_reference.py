#!/usr/bin/env python3
"""Independent exact-geometry and source-alpha controls, no private assets."""
from fractions import Fraction as F
import itertools
import unittest
import numpy as np
import salazar_source_alpha_reference as ref


class AuthoredAlphaReferenceTests(unittest.TestCase):
    def setUp(self):
        self.white = np.full((4, 4), 255, np.uint8)
        self.partial = self.white.copy()
        self.partial[1, 1] = 254

    def test_opaque_footprint(self):
        self.assertIsNone(ref.footprint([(128, 128)] * 3, self.white, (1, 1)))

    def test_partial_and_exact_rational_value(self):
        self.assertTrue(ref.seven([(256, 256)] * 3, self.partial, (1, 1)))
        self.assertEqual(ref.alpha_at(self.partial, F(1, 2), F(1, 2), (1, 1)), F(1019, 4))

    def test_zero_weight_neighbour_is_excluded(self):
        self.assertFalse(ref.seven([(0, 256)] * 3, self.partial, (1, 1)))
        self.assertIsNone(ref.footprint([(0, 256)] * 3, self.partial, (1, 1)))
        self.assertEqual(ref.support_axis(0, 1, 4, 1), [(0, F(1))])

    def test_support_boundary_only_is_excluded(self):
        self.assertIsNone(ref.footprint([(0, 0), (0, 256), (0, 512)], self.partial, (1, 1)))

    def test_interior_partial_between_all_seven_samples(self):
        pts = [(0, 0), (4096, 0), (0, 4096)]
        self.assertFalse(ref.seven(pts, self.partial, (0, 0)))
        self.assertIsNotNone(ref.footprint(pts, self.partial, (0, 0), witness=True))

    def test_arbitrarily_small_positive_weight_is_retained(self):
        den = 10 ** 18
        pts = [(1, 1)] * 3
        self.assertEqual(ref.alpha_at(self.partial, F(1, den), F(1, den), (1, 1)), F(255) - F(1, den * den))
        self.assertTrue(ref.seven(pts, self.partial, (1, 1), den))
        self.assertIsNotNone(ref.footprint(pts, self.partial, (1, 1), den, witness=True))

    def test_repeat_and_clamp_preserve_distinct_semantics(self):
        pts = [(-768, 256)] * 3
        self.assertIsNotNone(ref.footprint(pts, self.partial, (1, 1)))
        self.assertIsNone(ref.footprint(pts, self.partial, (0, 0)))

    def test_every_cyclic_order_has_same_classification(self):
        pts = [(0, 0), (4096, 0), (0, 4096)]
        for n in range(3):
            q = pts[n:] + pts[:n]
            self.assertFalse(ref.seven(q, self.partial, (0, 0)))
            self.assertIsNotNone(ref.footprint(q, self.partial, (0, 0)))

    def test_sat_against_independent_fraction_polygon_clip(self):
        points = [(x, y) for x in (-2, -1, 0, 1, 2) for y in (-2, -1, 0, 1, 2)]
        checks = 0
        for triangle in itertools.combinations_with_replacement(points, 3):
            pts = list(triangle)
            for x, y in ((0, 0), (-1, 1)):
                self.assertEqual(ref.touches_open_rect(pts, x, y, 1), ref.clipped_witness(pts, x, y, 1) is not None, (pts, x, y))
                checks += 1
        self.assertEqual(checks, 5850)

    def test_inexact_or_unsupported_inputs_refuse(self):
        for pts, img, wrap, den in [
            ([(0, 0)] * 3, self.white, (0, 0), 0),
            ([(0.0, 0)] * 3, self.white, (0, 0), 256),
            ([(0, 0)] * 3, self.white, (2, 0), 256),
            ([(0, 0)] * 3, np.zeros((4, 4, 4), np.uint8), (0, 0), 256),
        ]:
            with self.assertRaises(ValueError):
                ref.footprint(pts, img, wrap, den)


if __name__ == '__main__':
    unittest.main(verbosity=2)
