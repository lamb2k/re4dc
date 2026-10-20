"""Asset-free semantic guards; actual-disc Ashley regression runs in the CLI."""
import importlib.util
from pathlib import Path
import unittest
spec=importlib.util.spec_from_file_location('audit',Path(__file__).with_name('animation_cache_audit.py'))
audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)

def fixture(version,states,keys=None):
    keys=keys or list(range(len(states)))
    return dict(mtc=None if version is None else dict(version=version),
                clips={str(i):dict(arc=i,state=s,offset=i,key=str(k)) for i,(s,k) in enumerate(zip(states,keys))})

class CapacitySemantics(unittest.TestCase):
    def test_known_three_cold_shape(self):
        a=fixture(3,['cached-cold']*3)
        self.assertTrue(audit.evaluate_set(a,[0,1,2])['strict_two_slab_overflow'])
    def test_hot_inline_repair(self):
        a=fixture(3,['inline-resident']*3)
        self.assertFalse(audit.evaluate_set(a,[0,1,2])['strict_two_slab_overflow'])
    def test_aliases_are_not_three_distinct_clips(self):
        a=fixture(3,['cached-cold']*3,[0,1,1])
        self.assertEqual(audit.evaluate_set(a,[0,1,2])['distinct_cold'],2)
        self.assertFalse(audit.evaluate_set(a,[0,1,2])['strict_two_slab_overflow'])
    def test_v2_is_not_a_no_spill_proof(self):
        a=fixture(2,['cached-cold']*3)
        r=audit.evaluate_set(a,[0,1,2])
        self.assertFalse(r['strict_two_slab_overflow'])
        self.assertTrue(r['exceeds_two_reserved_if_preload_or_spill_lost'])
    def test_missing_fcv_is_not_a_pass(self):
        r=audit.evaluate_set(fixture(None,['inline-resident']),[0,5])
        self.assertEqual(r['conclusion'],'unresolved mapping')
    def test_function_parser_keeps_macro_lines_and_ignores_comments(self):
        t='// void fake() { ARC(5); }\nvoid real() { ARC(8); }\n#define RELOAD(x) '+chr(92)+'\n x = WEP_ARC_PTR(9);\n'
        found=list(audit.functions(t))
        self.assertEqual([x[0]for x in found],['real','macro:RELOAD'])
        self.assertIn('WEP_ARC_PTR(9)',found[1][3])

if __name__=='__main__':unittest.main()