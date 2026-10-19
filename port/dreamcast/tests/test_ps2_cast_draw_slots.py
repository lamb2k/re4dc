"""Existing registry draw slots preserve complete source skeletons and skin records."""
from pathlib import Path
import copy
import sys
import json
import struct
import tempfile
import unittest
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import ps2_cast as pc


def source_mesh(joints=201):
    bones = []
    for i in range(joints):
        matrix = np.eye(4).tolist()
        matrix[1][3] = i * 10.0
        bones.append(dict(id=i, parent=i - 1, rest=matrix, capture=copy.deepcopy(matrix)))
    source = dict(bones=bones, source_archive='source', infos=[dict(id=0)])
    weights = [[[0, .25], [joints - 1, .75]], [[37, 1.0]], [[0, 1.0]]]
    mesh = dict(bones=copy.deepcopy(bones), positions_mm=[[1., 2., 3.], [-1., 0., 4.], [3., 2., 1.]],
                weights=weights, triangles=[dict(source_info=0, corners=[dict(vertex=i, normal=[0., 1., 0.],
                uv=[i / 4., 0.]) for i in range(3)])], policy='Original source geometry.')
    return mesh, source


class SourceDrawSlotsTests(unittest.TestCase):
    def test_full201_source_and_every_corner_preserved_without_mutation(self):
        mesh, source = source_mesh()
        before = copy.deepcopy((mesh, source))
        low, src, proof = pc.lossless_draw_slots(mesh, source, 96)
        self.assertEqual((mesh, source), before)
        self.assertEqual(src['bones'], source['bones'])
        self.assertEqual(len(src['bones']), 201)
        self.assertEqual(src['draw_slots'], [0, 37, 200])
        self.assertEqual(low['triangles'], mesh['triangles'])
        self.assertEqual(low['positions_mm'], mesh['positions_mm'])
        self.assertEqual([[[src['draw_slots'][b], w] for b, w in ws] for ws in low['weights']], mesh['weights'])
        self.assertEqual([b['source_joint'] for b in low['bones']], src['draw_slots'])
        self.assertTrue(proof['source_skeleton_preserved'])

    def test_arbitrary_affine_source_skin_is_exact_after_mapping(self):
        mesh, source = source_mesh()
        low, src, _ = pc.lossless_draw_slots(mesh, source, 96)
        rng = np.random.default_rng(221)
        for _ in range(8):
            mats = rng.normal(size=(201, 4, 4))
            mats[:, 3] = [0., 0., 0., 1.]
            full = pc.skin(mesh['positions_mm'], mesh['weights'], mats)
            got = pc.skin(low['positions_mm'], low['weights'], mats[src['draw_slots']])
            np.testing.assert_array_equal(full, got)

    def test_zero_weight_records_remain_exact(self):
        mesh, source = source_mesh()
        mesh['weights'][0].append([99, 0.0])
        low, src, _ = pc.lossless_draw_slots(mesh, source, 96)
        self.assertIn(99, src['draw_slots'])
        self.assertEqual([[[src['draw_slots'][b], w] for b, w in ws] for ws in low['weights']], mesh['weights'])

    def test_changed_or_incomplete_source_hierarchy_refused(self):
        for mutation in ('mesh', 'parent', 'id', 'nonfinite_unused'):
            mesh, source = source_mesh()
            if mutation == 'mesh':
                mesh['bones'].pop()
            elif mutation == 'parent':
                source['bones'][200]['parent'] = 200
            elif mutation == 'id':
                source['bones'][199]['id'] = 200
            else:
                source['bones'][199]['rest'][0][0] = float('nan')
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                pc.lossless_draw_slots(mesh, source, 96)

    def test_outside_joint_negative_and_nonfinite_weights_refused(self):
        for weight in ([201, 1.0], [-1, 1.0], [True, 1.0], [0, -0.5], [0, float('nan')]):
            mesh, source = source_mesh()
            mesh['weights'][0] = [weight]
            with self.subTest(weight=weight), self.assertRaisesRegex(ValueError, 'weights'):
                pc.lossless_draw_slots(mesh, source, 96)

    def test_existing_capacity_and_source_joint_encoding_cannot_expand(self):
        mesh, source = source_mesh()
        with self.assertRaisesRegex(ValueError, 'existing registry capacity'):
            pc.lossless_draw_slots(mesh, source, 201)
        mesh['positions_mm'] = [[0., 0., 0.]] * 129
        mesh['weights'] = [[[i, 1.0]] for i in range(129)]
        with self.assertRaisesRegex(ValueError, 'unchanged registry capacity'):
            pc.lossless_draw_slots(mesh, source, 128)
        mesh, source = source_mesh(256)
        with self.assertRaisesRegex(ValueError, '1..255'):
            pc.lossless_draw_slots(mesh, source, 96)

    def test_host_fixture_selects_source_poses_and_keeps_original_root_compensation(self):
        # The source root is unweighted. Joint1 moves11mm, root5mm: the
        # root-compensated draw-slot translation must be6mm, not0or11.
        _, source = source_mesh(39)
        source['bones'][0]['capture'][1][3] += 5.0
        source['bones'][1]['capture'][1][3] += 11.0
        source['draw_slots'] = [1]
        with tempfile.TemporaryDirectory() as temporary:
            n = Path(temporary)
            report = dict(chunks=[dict(info=0, positions=1, normals=1, palettes=1,
                          triangles=1, palette_weights=[[[0, 1.0]]])])
            (n / 'native-report.json').write_text(json.dumps(report))
            for extension, data in (('pos', bytes(6)), ('nrm', bytes(6)), ('uv', bytes(4)), ('gx', bytes(21))):
                (n / ('info0.' + extension)).write_bytes(data)
            pc.host_fixture(n, source)
            raw = (n / 'host-fixture.bin').read_bytes()
            matrices = struct.unpack_from('<12f', raw, 4 + 40 + 6 + 6 + 4 + 21)
            self.assertEqual(matrices[10], 6.0)
            # Established Ashley-style already-selected input is not selected twice.
            selected = dict(source, bones=[dict(source['bones'][1], id=0, parent=-1, source_joint=1)])
            pc.host_fixture(n, selected)
            raw = (n / 'host-fixture.bin').read_bytes()
            legacy = struct.unpack_from('<12f', raw, 4 + 40 + 6 + 6 + 4 + 21)
            self.assertEqual(legacy[10], 0.0)
            bad = dict(source, draw_slots=[39])
            with self.assertRaisesRegex(ValueError, 'outside complete source'):
                pc.host_fixture(n, bad)

    def test_already_mapped_or_unneeded_mapping_refused(self):
        mesh, source = source_mesh()
        low, src, _ = pc.lossless_draw_slots(mesh, source, 96)
        with self.assertRaisesRegex(ValueError, 'original source skeleton'):
            pc.lossless_draw_slots(low, src, 96)
        mesh, source = source_mesh(39)
        mesh['positions_mm'] = [[0., 0., 0.]] * 39
        mesh['weights'] = [[[i, 1.0]] for i in range(39)]
        with self.assertRaisesRegex(ValueError, 'strict subset'):
            pc.lossless_draw_slots(mesh, source, 48)


if __name__ == '__main__':
    unittest.main()
