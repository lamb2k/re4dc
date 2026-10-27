import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


ashley = module('ps2_ashley', HERE.parents[1] / 'ps2_ashley.py')
header = module('rig_header', HERE / 'rig_header.py')


class RigTests(unittest.TestCase):
    def test_authored_influences_survive(self):
        weights = [(4, .25), (64, .25), (80, .5)]
        self.assertEqual(ashley.rig_weights(weights), {4: .25, 70: .25, 127: .5})

    def test_garment_domains(self):
        self.assertEqual(set(ashley.RIG_MAP), set(range(64, 81)))
        self.assertTrue(all(64 <= ashley.RIG_MAP[b] <= 84 for b in range(64, 69)))
        self.assertTrue(all(93 <= ashley.RIG_MAP[b] <= 140 for b in range(69, 81)))
        self.assertEqual(len(set(ashley.RIG_MAP.values())), 17)

    def test_invalid_weights_refused(self):
        for weights in ([(81, 1)], [(4, .2)], [], [(1, .25), (2, .25), (3, .25), (4, .25)],
                        [(-1, 1)], [(1, -1), (2, 1)], [(1, float('nan'))], [(1, float('inf'))]):
            with self.assertRaises(ValueError):
                ashley.rig_weights(weights)

    def test_header_refuses_old_and_mixed_rig(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            convs = [root / str(k) for k in range(3)]
            for p in convs:
                p.mkdir()
                (p / 'source.json').write_text(json.dumps(dict(draw_slots=[4, 70])))
            with self.assertRaises(ValueError):
                header.generate(convs, root / 'out')

            for p in convs:
                (p / 'source.json').write_text(json.dumps(dict(draw_slots=[4, 70], ps2_rig=dict(
                    schema='ashley-ps2-rig-1', ps2_bones=81))))
            header.generate(convs, root / 'out')
            self.assertIn('slots_match', (root / 'out/ashley_ps2_rig27.h').read_text())
            (convs[1] / 'source.json').write_text(json.dumps(dict(draw_slots=[4, 70], ps2_rig=dict(
                schema='ashley-ps2-rig-1', ps2_bones=81, changed=True))))
            with self.assertRaises(ValueError):
                header.generate(convs, root / 'out')

    def test_source_normal_length_refused(self):
        run=subprocess.run([sys.executable,str(HERE.parent/'model_registry.py'),'unused-spec','unused-output',
                            '--package-room','117','--slots','--ashley-rig',
                            '--source-normal-length'],capture_output=True,text=True)
        self.assertNotEqual(run.returncode,0)
        self.assertIn('PS2 Ashley rig must keep PS2 normals',run.stderr+run.stdout)


if __name__ == '__main__':
    unittest.main()
