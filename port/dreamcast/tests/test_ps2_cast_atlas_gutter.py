"""Source sampler preservation for optional PS2 character atlas gutters."""
import ast
import math
from pathlib import Path
import unittest
import numpy as np

SOURCE = Path(__file__).resolve().parents[1] / 'tools' / 'ps2_cast.py'
module = ast.parse(SOURCE.read_text(encoding='utf-8'))
namespace = {'math': math, 'np': np}
exec(compile(ast.Module(body=[n for n in module.body if isinstance(n, ast.FunctionDef) and n.name in ('gutter_texture', 'pack_atlas')], type_ignores=[]), str(SOURCE), 'exec'), namespace)
gutter_texture = namespace['gutter_texture']
pack_atlas = namespace['pack_atlas']


def sample(image, u, v, repeat):
    h, w, _ = image.shape
    x, y = u * w - .5, v * h - .5
    ix, iy = math.floor(x), math.floor(y)
    fx, fy = x - ix, y - iy
    def at(x, y):
        x = x % w if repeat[0] else min(w - 1, max(0, x))
        y = y % h if repeat[1] else min(h - 1, max(0, y))
        return image[y, x].astype(float)
    return ((1-fy)*((1-fx)*at(ix, iy)+fx*at(ix+1, iy)) +
            fy*((1-fx)*at(ix, iy+1)+fx*at(ix+1, iy+1)))


class AtlasGutterTests(unittest.TestCase):
    def test_bilinear_source_phase_and_interpolation_survive_repeat_and_clamp(self):
        src = np.arange(3*5*4, dtype=np.uint8).reshape(3, 5, 4)
        for wrap in ((1, 1), (0, 0), (1, 0), (0, 1)):
            data, (left, top, right, bottom) = gutter_texture(src.tobytes(), 5, 3, ((-512, -256), (768, 512)), wrap)
            ext = np.frombuffer(data, np.uint8).reshape(3+top+bottom, 5+left+right, 4)
            np.testing.assert_array_equal(ext[top:top+3, left:left+5], src)
            for u in np.linspace(-2, 3, 29):
                for v in np.linspace(-1, 2, 19):
                    got = sample(ext, (left+u*5)/ext.shape[1], (top+v*3)/ext.shape[0], (0, 0))
                    np.testing.assert_allclose(got, sample(src, u, v, wrap), atol=1e-10, rtol=0)

    def test_padded_images_keep_power_of_two_atlas_and_legacy_layout(self):
        cells, shape = pack_atlas([(0, 64, 64), (1, 64, 64)])
        self.assertEqual(shape, (128, 64))
        self.assertEqual(cells, {0: (0, 0, 64, 64), 1: (64, 0, 64, 64)})
        for items in ([(0, 18, 18)], [(0, 258, 258), (1, 258, 258)], [(0, 516, 258), (1, 66, 70)]):
            _, shape = pack_atlas(items)
            self.assertTrue(all(d > 0 and not d & (d-1) and d <= 2048 for d in shape))

    def test_filter_margin_retains_exact_raw_edge_uvs(self):
        data, pad = gutter_texture(bytes(64*32*4), 64, 32, ((0, -14), (257, 256)), (1, 1))
        self.assertEqual(pad, (1, 3, 2, 1))
        self.assertEqual(len(data), 67*36*4)

    def test_refuse_unsupported_sampler_invalid_bounds_and_unbounded_storage(self):
        for bounds, wrap in [(((0, 0), (256, 256)), (2, 1)), (((10, 0), (0, 256)), (1, 1)),
                             (((0, 0), (float('nan'), 256)), (1, 1)), (((-1000000, 0), (256, 256)), (1, 1))]:
            with self.assertRaises(ValueError):
                gutter_texture(bytes(4), 1, 1, bounds, wrap)


if __name__ == '__main__':
    unittest.main()
