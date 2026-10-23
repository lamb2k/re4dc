#!/usr/bin/env python3
"""Estimator controls; optional private-input static-reference checks.

Run without arguments for five small controls. To add both real camera checks:
  python test_placement_estimate.py --inputs INPUTS.json \
      --cross-camera CROSS.log --farm-camera FARM.log

Input paths and game/camera data are supplied by the caller, never embedded.
These are offline estimator checks, not rendering or memory acceptance.
"""
import argparse
import collections
from pathlib import Path
import unittest

import numpy as np
import placement_estimate as pe


class GroupControls(unittest.TestCase):
    def setUp(self):
        self.pieces = {}
        for key, count in [((1, 1), 200), ((1, 2), 100), ((2, 3), 80)]:
            self.pieces[key] = dict(nv=count, lo=np.zeros(3), hi=np.ones(3),
                                    center=np.ones(3) * 0.5)

    def part(self, members, material=('compatible',)):
        return dict(members=members, center=np.ones(3), material=material)

    def mixed_parts(self):
        return {(1, 0): self.part([(1, 1)]),
                (1, 1): self.part([(1, 2)]),
                (2, 0): self.part([(2, 3)])}

    def test_empty_candidates_keep_original_path(self):
        self.assertEqual(pe.group_parts({}, {}, 2000), [])

    def test_one_placement_is_not_a_placement_merge(self):
        parts = self.mixed_parts()
        del parts[(2, 0)]
        self.assertEqual(pe.group_parts(parts, self.pieces, 2000), [])

    def test_material_mismatch_keeps_original_parts(self):
        parts = {(1, 0): self.part([(1, 1)]),
                 (2, 0): self.part([(2, 3)], ('different',))}
        self.assertEqual(pe.group_parts(parts, self.pieces, 2000), [])

    def test_cross_placement_group_keeps_each_source_once(self):
        parts = self.mixed_parts()
        groups = pe.group_parts(parts, self.pieces, 2000)
        self.assertEqual(len(groups), 1)
        self.assertEqual(collections.Counter(groups[0]['source_parts']),
                         collections.Counter(parts.keys()))
        members = [key for group in groups for batch in group['batches']
                   for key in batch['members']]
        self.assertEqual(collections.Counter(members),
                         collections.Counter(self.pieces.keys()))

    def test_large_context_splits_into_bounded_children(self):
        groups = pe.group_parts(self.mixed_parts(), self.pieces, 2000)
        batches = [batch for group in groups for batch in group['batches']]
        self.assertGreater(len(batches), 1)
        self.assertTrue(all(0 < batch['nv'] <= 256 for batch in batches))
        self.assertEqual(sum(batch['nv'] for batch in batches), 380)


class RealZeroGroupControls(unittest.TestCase):
    options = None

    def check_room(self, room, camera):
        if self.options.inputs is None:
            self.skipTest('Supply --inputs, --cross-camera and --farm-camera.')
        import json
        source = json.loads(self.options.inputs.read_text())
        data, _ = pe.load(source[room])
        cams = pe.cameras(camera)
        self.assertEqual([frame for frame, _ in cams], list(range(500, 795, 7)))
        mean, rows = pe.price(data, {}, [], cams)
        self.assertEqual(len(rows), 43)
        for row in rows:
            with self.subTest(room=room, frame=row['frame']):
                for unit in ('vertices', 'triangles', 'part_contexts', 'placements'):
                    self.assertEqual(row['before_' + unit], row['after_' + unit])
                self.assertEqual(row['before_selected_meshlets'],
                                 row['after_selected_meshlets'])
        for metric in ('part_context_drop_percent', 'meshlet_selection_drop_percent',
                       'vertex_growth_percent'):
            self.assertEqual(mean[metric], 0.0)

    def test_r101_cross_zero_groups_preserve_all_counts(self):
        self.check_room('r101', self.options.cross_camera)

    def test_r103_farm_zero_groups_preserve_all_counts(self):
        self.check_room('r103', self.options.farm_camera)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path)
    parser.add_argument('--cross-camera', type=Path)
    parser.add_argument('--farm-camera', type=Path)
    args = parser.parse_args()
    supplied = (args.inputs, args.cross_camera, args.farm_camera)
    if any(path is not None for path in supplied) and not all(path is not None for path in supplied):
        parser.error('Real-data controls require all three input and camera options.')
    RealZeroGroupControls.options = args
    suite = unittest.TestSuite()
    for cls in (GroupControls, RealZeroGroupControls):
        suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(cls))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)


if __name__ == '__main__':
    main()

