import sys, unittest
from pathlib import Path
T = Path(__file__).resolve().parents[1] / 'tools/d367/issue52_visuals'
sys.path.insert(0, str(T))
import repair_chandelier_atlas as atlas


class ChandelierAtlas(unittest.TestCase):
    def test_periodic_collar_preserves_bilinear_seams(self):
        pixels = [(x * 40, y * 40, (x + y) * 20, (x + y) * 17) for y in range(4) for x in range(4)]
        image = [(0, 0, 0, 0)] * (atlas.SIZE * atlas.SIZE)
        rect = (16, 16, 4, 4)
        atlas.paste_repeat(image, set(), pixels, rect)
        for u in [-.125, 0, .125, .9, 1, 1.125]:
            for v in [-.125, 0, .5, 1, 1.125]:
                expected = atlas.bilinear(pixels, 4, 4, (u, v))
                actual = atlas.bilinear(image, atlas.SIZE, atlas.SIZE, atlas.atlas_uv(rect, (u, v)))
                for a, b in zip(expected, actual):
                    self.assertAlmostEqual(a, b, places=10)

    def test_rejects_overlapping_collar(self):
        image = [(0, 0, 0, 0)] * (atlas.SIZE * atlas.SIZE)
        occupied = set()
        atlas.paste_repeat(image, occupied, [(0, 0, 0, 255)] * 16, (16, 16, 4, 4))
        with self.assertRaisesRegex(ValueError, 'overlapping'):
            atlas.paste_repeat(image, occupied, [(0, 0, 0, 255)] * 16, (19, 16, 4, 4))

    def test_mask_keeps_sixteen_levels_and_rejects_colour(self):
        self.assertEqual(atlas.mask_levels([(v, v, v, 255) for v in range(0, 256, 16)]), list(range(0, 256, 17)))
        with self.assertRaisesRegex(ValueError, 'intensity'):
            atlas.mask_levels([(16, 17, 16, 255)])

    def test_material_pair_identity_matches_selected_existing_fixture(self):
        self.assertEqual(atlas.pair_key('680fc44c-1c7b1805', 'cd2fdf7b-98123ca6'), 'd1fdb548-e80a6158')

    def test_disabled_before_any_input_is_opened(self):
        argv = sys.argv
        try:
            sys.argv = ['tool', '--dar', 'missing', '--sources', 'missing', '--out', 'missing']
            with self.assertRaisesRegex(ValueError, 'disabled'):
                atlas.main()
        finally:
            sys.argv = argv


if __name__ == '__main__':
    unittest.main()