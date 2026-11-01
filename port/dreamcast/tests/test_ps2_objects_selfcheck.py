"""Converter self-check (lane props-ps2-26, 2026-10-26, scope (d)): ps2_objects refuses an output larger than the GC
model it replaces, refuses an object whose reduction step did not run, and its mesh_lod step brings a dense PS2 mesh
below the GC triangle count without moving a seam vertex."""
import pathlib
import sys
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent / 'tools'), str(HERE.parents[2] / 'tools')]
import ps2_objects as po  # noqa: E402


def grid(n, tex=0):
    """n x n quad grid on y=0, 1000 units wide, planar UVs: 2*n*n triangles in the converter's PS2 form."""
    out = []
    f = lambda i, j: (i * 1000.0 / n, 0.0, j * 1000.0 / n)
    uv = lambda i, j: (i / n, j / n)
    w = ((0, 1.0),)
    nrm = (0.0, 1.0, 0.0)
    for i in range(n):
        for j in range(n):
            a, b, c, d = (i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)
            for t in ((a, b, c), (a, c, d)):
                out.append((tex, [(f(*k), nrm, uv(*k), w) for k in t]))
    return out


class SelfCheck(unittest.TestCase):
    def test_larger_triangles_refused(self):
        with self.assertRaises(po.SizeCheckError):
            po.self_check(dict(gc_tris=100, out_tris=120, lod={}))

    def test_equal_triangles_pass(self):
        po.self_check(dict(gc_tris=100, out_tris=100, lod={}), before_bytes=1000, after_bytes=1000)

    def test_larger_bytes_refused(self):
        with self.assertRaises(po.SizeCheckError):
            po.self_check(dict(gc_tris=100, out_tris=50, lod={}), before_bytes=1000, after_bytes=1032)

    def test_skipped_reduction_refused(self):
        with self.assertRaises(po.SizeCheckError):
            po.self_check(dict(gc_tris=100, out_tris=50))

    def test_smaller_passes(self):
        po.self_check(dict(gc_tris=100, out_tris=50, lod={}), before_bytes=1000, after_bytes=800)

    def test_keep_larger_needs_reason(self):
        class A:
            keep_larger, keep_larger_reason = True, ''
        self.assertIsNone(po.size_gate(type('B', (), dict(keep_larger=True, keep_larger_reason='x')),
                                       dict(gc_tris=1, out_tris=5, lod={}), 1, 2))
        self.assertTrue(po.size_gate(type('C', (), dict(keep_larger=False, keep_larger_reason=None)),
                                     dict(gc_tris=1, out_tris=5, lod={}), 1, 2).startswith('self-check'))

    def test_lod_reduces_below_gc(self):
        mesh = grid(12)                     # 288 triangles, flat: the quadric reducer collapses it freely
        out, rep = po.lod_reduce(mesh, 100)
        self.assertLessEqual(len(out), 100)
        self.assertEqual(rep['step'], 'mesh_lod')
        self.assertEqual(rep['tris_out'], len(out))

    def test_lod_keeps_material_seam(self):
        a, b = grid(6, tex=0), [(1, [((p[0] + 1000.0, p[1], p[2]), n, uv, w) for p, n, uv, w in cs]) for t, cs in grid(6)]
        out, rep = po.lod_reduce(a + b, 40)
        seam_in = {c[0] for t, cs in a + b for c in cs if c[0][0] == 1000.0}
        seam_out = {c[0] for t, cs in out for c in cs if c[0][0] == 1000.0}
        self.assertEqual(seam_in, seam_out)  # locked: every shared border vertex survives
        self.assertEqual({t for t, cs in out}, {0, 1})


if __name__ == '__main__':
    unittest.main()
