"""New FX policy layers retain later texture work and reject alias conflicts."""
import copy,pathlib,sys,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools/d367/mipmap21'))
import layer_effect_candidate as layer
import texpack
import test_mipmap_select_effects as fixture


class EffectLayer(unittest.TestCase):
    def setUp(self):
        f=fixture.SelectEffects();f.setUp();self.f=f
        original=layer.compose._read(f.original);current=layer.compose._read(f.base)
        b=bytearray(current[(5,6)]);b[44]^=1;current[(5,6)]=bytes(b)
        self.current=texpack.build(current)[0]
        self.receipt=dict(original_pack_sha256=layer.sha(f.original),candidate_pack_sha256=layer.sha(self.current),
            members=[dict(key='%08x-%08x'%k,before_sha256=layer.sha(original[k]),after_sha256=layer.sha(current[k]),changed=original[k]!=current[k]) for k in sorted(original)],required_build_knobs=[])
    def call(self,**kw):
        f=self.f
        return layer.layer(f.original,f.base,f.review,f.receipt,f.policy,self.current,self.receipt,**kw)
    def test_off_exact_and_new_effect_does_not_erase_current_non_effect_changes(self):
        output,r,b,a=self.call();self.assertEqual(output,self.current);self.assertEqual(b,a)
        output,r,b,a=self.call(enabled=True)
        self.assertEqual(r['changed_from_base'],1);self.assertEqual(r['already_selected_effect_keys'],0)
        self.assertEqual(a[(3,4)],b[(3,4)]);self.assertEqual(a[(5,6)],b[(5,6)])
    def test_already_selected_review_bytes_are_idempotent(self):
        output,r,b,a=self.call(enabled=True);self.current=output;self.receipt=r
        output2,r2,b2,a2=self.call(enabled=True)
        self.assertEqual(output,output2);self.assertEqual(r2['changed_from_base'],0);self.assertEqual(r2['already_selected_effect_keys'],1)
    def test_a_later_change_to_the_selected_key_requires_explicit_regeneration(self):
        before=layer.compose._read(self.current);b=bytearray(before[(1,2)]);b[44]^=1;before[(1,2)]=bytes(b)
        self.current=texpack.build(before)[0];self.receipt['candidate_pack_sha256']=layer.sha(self.current)
        for row in self.receipt['members']:
            if row['key']=='00000001-00000002':row['after_sha256']=layer.sha(before[(1,2)]);row['changed']=True
        with self.assertRaises(ValueError):self.call(enabled=True)
    def test_a_stale_current_member_receipt_is_refused(self):
        self.receipt['members'][0]['after_sha256']='wrong'
        with self.assertRaises(ValueError):self.call(enabled=True)


if __name__=='__main__':unittest.main()
