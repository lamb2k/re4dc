"""Receipt-bound selective FX composition holds UI and preserves OFF/base bytes."""
import copy
import json
import pathlib
import sys
import tempfile
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools/d367/mipmap21'))
import compose_candidate as compose
import fx_candidate as fx
import select_effect_candidate as select
import test_mipmap_fx_candidate as source_fixture


class SelectEffects(unittest.TestCase):
    def setUp(self):
        fixture=source_fixture.EffectMipSelection();fixture.setUp()
        self.original,self.base=fixture.original,fixture.base_pack
        self.review,self.receipt,before,after=fx.build_candidate(
            fixture.original,fixture.base_pack,fixture.coverage,fixture.proofs,enabled=True,engine='python')
        self.receipt['members']=[dict(key='%08x-%08x'%k,before_sha256=fx.sha(before[k]),
            after_sha256=fx.sha(after[k]),changed=before[k]!=after[k]) for k in sorted(before)]
        rec=dict(kind=0,sprite_id=0,screen_parts=False,tool_flags=0,shimmer_type=0)
        binding=dict(source_path='fixture',source_sha256='exact-source',records=[rec])
        self.policy=dict(original_source_pack_sha256=fx.sha(self.original),
            selected_base_pack_sha256=fx.sha(self.base),review_candidate_sha256=fx.sha(self.review),
            source_files=dict(fixture=dict(retained=True,parsed=True,sha256='exact-source')),
            common_sprite_ids=[0],rows=[
                dict(key='00000001-00000002',decision='world-common-sprite-source-candidate',reasons=[],
                    direct_ID_UI_consumers=[],source_bindings=[binding]),
                dict(key='00000003-00000004',decision='hold-fixed-ID-UI',reasons=['ID consumer'],
                    direct_ID_UI_consumers=['scope'],source_bindings=[])])

    def test_off_identity_and_on_keeps_ui_at_compact_base(self):
        control,_,_,_=select.select(self.original,self.base,self.review,self.receipt,self.policy)
        self.assertEqual(control,self.base)
        output,report,before,after=select.select(self.original,self.base,self.review,self.receipt,self.policy,enabled=True)
        self.assertEqual(report['changed_from_base'],1)
        self.assertEqual(report['family_counts'],{'compact-PAL4':1})
        self.assertEqual(after[(3,4)],before[(3,4)])
        self.assertEqual(after[(5,6)],before[(5,6)])
        # New selective receipts are relative to original source and compose
        # through the ordinary sealed-candidate reader without losing ancestry.
        with tempfile.TemporaryDirectory() as directory:
            p=pathlib.Path(directory);(p/'tex.pak').write_bytes(output)
            (p/'candidate.json').write_text(json.dumps(report))
            self.assertEqual(compose.bound_candidate(p,self.original),output)

    def test_forged_ui_world_label_or_screen_record_is_refused(self):
        policy=copy.deepcopy(self.policy);policy['rows'][1]['decision']='world-common-sprite-source-candidate'
        with self.assertRaises(ValueError):select.select(self.original,self.base,self.review,self.receipt,policy,enabled=True)
        policy=copy.deepcopy(self.policy);policy['rows'][0]['source_bindings'][0]['records'][0]['screen_parts']=True
        with self.assertRaises(ValueError):select.select(self.original,self.base,self.review,self.receipt,policy,enabled=True)

    def test_extended_emitter_contract_accepts_only_reviewed_generator00(self):
        policy=copy.deepcopy(self.policy);policy['sampling_contract_version']=2
        r=policy['rows'][0]['source_bindings'][0]['records'][0]
        r.update(kind=1,generator_id=0)
        _,report,_,_=select.select(self.original,self.base,self.review,self.receipt,policy,enabled=True)
        self.assertEqual(report['selected_frames'],1)
        r['generator_id']=2
        with self.assertRaises(ValueError):select.select(self.original,self.base,self.review,self.receipt,policy,enabled=True)
        policy['sampling_contract_version']=3
        with self.assertRaises(ValueError):select.select(self.original,self.base,self.review,self.receipt,policy,enabled=True)

    def test_ancestry_source_hash_and_incomplete_policy_are_refused(self):
        for field in ('original_source_pack_sha256','selected_base_pack_sha256','review_candidate_sha256'):
            policy=copy.deepcopy(self.policy);policy[field]='bad'
            with self.assertRaises(ValueError):select.select(self.original,self.base,self.review,self.receipt,policy)
        policy=copy.deepcopy(self.policy);policy['source_files']['fixture']['sha256']='bad'
        with self.assertRaises(ValueError):select.select(self.original,self.base,self.review,self.receipt,policy)
        policy=copy.deepcopy(self.policy);policy['rows'].pop()
        with self.assertRaises(ValueError):select.select(self.original,self.base,self.review,self.receipt,policy)


if __name__=='__main__':unittest.main()
