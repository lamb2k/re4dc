"""Explicit source correspondence controls; these do not certify animation."""
import ast
import copy
import hashlib
import math
from pathlib import Path
import unittest
import numpy as np

P = Path(__file__).resolve().parents[1] / 'tools' / 'ps2_cast.py'
ns = {'np': np, 'math': math, 'sha': lambda b: hashlib.sha256(b).hexdigest()}
module = ast.parse(P.read_text(encoding='utf-8'))
exec(compile(ast.Module(body=[n for n in module.body if isinstance(n, ast.FunctionDef) and n.name == 'source_bind_offsets'], type_ignores=[]), str(P), 'exec'), ns)
source_bind_offsets = ns['source_bind_offsets']


class BindOffsetTests(unittest.TestCase):
    def setUp(self):
        self.p = [dict(id=0, parent=-1, pos=[0, 0, 0]), dict(id=1, parent=0, pos=[2, 0, 0])]
        root = np.eye(4); tip = np.eye(4); tip[0, 3] = 1
        self.g = [dict(id=0, attach=0, parent=-1, rest=root.tolist()), dict(id=1, attach=1, parent=0, rest=tip.tolist())]
        self.contract = dict(kind='same-id-parent-gc-inverse-bind', ps2_sha256=hashlib.sha256(b'PS2').hexdigest(), gc_sha256=hashlib.sha256(b'GC').hexdigest())

    def test_declared_offset_leaves_source_tables_unchanged(self):
        original = copy.deepcopy((self.p, self.g))
        result = source_bind_offsets(b'PS2', b'GC', self.p, self.g, self.contract)
        self.assertEqual((self.p, self.g), original)
        self.assertEqual(result['maximum_virtual_world_offset_mm'], 1)
        np.testing.assert_array_equal(np.asarray(result['offsets'][1]['gc_to_ps2_virtual_rest_offset'])[:3, 3], [1, 0, 0])
        self.assertTrue(result['animation_evidence'].startswith('NONE'))

    def test_changed_source_bytes_or_policy_are_refused(self):
        for source, gc in ((b'OTHER', b'GC'), (b'PS2', b'OTHER')):
            with self.assertRaises(ValueError):
                source_bind_offsets(source, gc, self.p, self.g, self.contract)
        for key, value in (('kind', 'unmapped'), ('extra', 'unreviewed')):
            contract = dict(self.contract); contract[key] = value
            with self.assertRaises(ValueError):
                source_bind_offsets(b'PS2', b'GC', self.p, self.g, contract)

    def test_missing_remapped_or_nonfinite_source_joints_are_refused(self):
        pairs = []
        p = copy.deepcopy(self.p); p[1]['id'] = 2; pairs.append((p, self.g))
        g = copy.deepcopy(self.g); g[1]['parent'] = -1; pairs.append((self.p, g))
        p = copy.deepcopy(self.p); p[1]['pos'][0] = float('nan'); pairs.append((p, self.g))
        pairs.append((self.p[:1], self.g))
        for p, g in pairs:
            with self.assertRaises(ValueError):
                source_bind_offsets(b'PS2', b'GC', p, g, self.contract)


if __name__ == '__main__':
    unittest.main()
