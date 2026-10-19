#!/usr/bin/env python3
"""Model-draw coverage must distinguish IRQ ancestry from nested IRQ work."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from summarize_model_draw import summarize


class DrawIRQRootTest(unittest.TestCase):
    def fixture(self, root_owner, child_owner):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        profile = Path(tmp.name) / 'profile'
        witness = Path(tmp.name) / 'witness'
        (profile / 'profile').mkdir(parents=True)
        witness.mkdir()
        runtime = profile / 'runtime.elf'
        runtime.write_bytes(b'exact test runtime')
        symbols = profile / 'runtime-symbols.json'
        symbols.write_text(json.dumps({'symbols': [
            {'symbol': 1, 'name': 'commonModelTrans'},
            {'symbol': 2, 'name': 'source transaction'},
            {'symbol': 3, 'name': 'IRQ'}]}))
        proof = dict(runtime_elf_sha256=hashlib.sha256(runtime.read_bytes()).hexdigest(),
                     symbols_sha256=hashlib.sha256(symbols.read_bytes()).hexdigest(),
                     models=[{'model': '8c100000', 'name': 'test-model'}],
                     accessor_pc=0x8c001000, id_offset=0x100)
        (witness / 'build-proof.json').write_text(json.dumps(proof))
        (witness / 'validation.json').write_text(json.dumps({'status': 'PASS', 'samples': 1}))
        (witness / 'model-witnesses.tsv').write_text(
            'sample\tnode\tcommon_root\ttx_root\tmodel\tpc\taddress\tsize\n'
            '0\t1\t0\t1\t8c100000\t8c001000\t8c100100\t1\n')
        contexts = ('sample\tnode\tparent\tsymbol\tkind\towner\tcomplete\tinvalid\tself16\tinclusive16\n'
                    f'0\t0\t4294967295\t1\t1\t{root_owner}\t1\t0\t16\t80\n'
                    f'0\t1\t0\t2\t1\t{child_owner}\t1\t0\t32\t32\n'
                    '0\t2\t0\t3\t1\t5\t1\t0\t32\t32\n')
        for directory in (profile / 'profile', witness):
            (directory / 'nominal.contexts.tsv').write_text(contexts)
            (directory / 'nominal.function_frames.tsv').write_text('same observed attribution\n')
        return summarize(profile, witness, [350])

    def test_irq_owned_draw_is_unqualified_not_zero_cost(self):
        result = self.fixture(5, 5)
        row = result['results']['8c100000']
        self.assertEqual(row['complete_noninvalid_invocations'], 1)
        self.assertEqual(row['excluded_irq_root_samples'], [0])
        self.assertEqual(result['jointly_complete_ticks'], [])
        self.assertIsNone(row['jointly_complete_ms_per_sample'])

    def test_normal_draw_excludes_only_nested_irq_charge(self):
        result = self.fixture(1, 1)
        row = result['results']['8c100000']
        self.assertEqual(result['jointly_complete_ticks'], [350])
        self.assertEqual(row['excluded_irq_root_samples'], [])
        self.assertEqual(row['jointly_complete_ms_per_sample'], 48 / (16 * 200000))
        self.assertEqual(row['rows'][0]['excluded_IRQ_ms'], 32 / (16 * 200000))

    def test_irq_root_with_nonirq_child_still_unqualified(self):
        result = self.fixture(5, 1)
        self.assertEqual(result['results']['8c100000']['qualified_samples'], {})
        self.assertEqual(result['jointly_complete_ticks'], [])


if __name__ == '__main__':
    unittest.main()