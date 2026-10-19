"""Source owner retarget opt-in: preserve every original partial/duplicate rest record."""
from pathlib import Path
import copy
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
import ps2_cast as pc

class RetargetOwnerAttachmentTests(unittest.TestCase):
    def setUp(self):
        self.data=(b'attachment PS2',b'attachment GC',b'owner PS2',b'owner GC')
        keys=('ps2_sha256','gc_sha256','owner_ps2_sha256','owner_gc_sha256')
        self.contract=dict(kind='source-pinned-retarget-owner-attachment',**dict(zip(keys,map(pc.sha,self.data))),
            owner_bind_contract=dict(kind='same-id-parent-gc-inverse-bind',ps2_sha256=pc.sha(self.data[2]),gc_sha256=pc.sha(self.data[3])))
        self.owner=[dict(id=0,parent=-1,pos=[0.,100.,0.]),dict(id=1,parent=0,pos=[10.,0.,0.]),dict(id=2,parent=1,pos=[20.,0.,0.])]
        self.gc=[]
        for i,(pos,world) in enumerate((([0.,105.,0.],[0.,105.,0.]),([12.,0.,0.],[12.,105.,0.]),([18.,0.,0.],[30.,105.,0.]))):
            rest=[[1.,0.,0.,world[0]],[0.,1.,0.,world[1]],[0.,0.,1.,world[2]],[0.,0.,0.,1.]]
            self.gc.append(dict(id=i,attach=i,parent=i-1,translation=pos,rest=rest))
        self.child=[dict(id=1,parent=-1,pos=[10.,100.,0.]),dict(id=1,parent=-1,pos=[10.,100.,0.]),dict(id=2,parent=1,pos=[20.,0.,0.])]
        self.section=[dict(self.gc[2],id=0)]
    def invoke(self,**changes):
        args=dict(pbin=self.data[0],gbin=self.data[1],owner_pbin=self.data[2],owner_gbin=self.data[3],source_bones=self.child,
            owner_ps2=self.owner,section_gc=self.section,owner_gc=self.gc,weighted={2},contract=self.contract,bone_tol=.001)
        args.update(changes);return pc.source_attachment_owner_skeleton(**args)
    def test_partial_duplicate_metadata_kept_and_only_original_owner_selected(self):
        before=copy.deepcopy((self.owner,self.gc,self.child,self.section))
        selected,proof=self.invoke()
        self.assertEqual(selected,self.owner)
        self.assertEqual(proof['original_PS2_rest_records'],self.child)
        self.assertEqual(proof['original_GC_rest_records'],self.section)
        self.assertEqual(proof['original_PS2_rest_record_count'],3)
        self.assertEqual(proof['original_GC_rest_record_count'],1)
        self.assertEqual(proof['weighted_ids'],[2])
        self.assertGreater(proof['owner_bind_offsets']['maximum_virtual_world_offset_mm'],.001)
        self.assertEqual((self.owner,self.gc,self.child,self.section),before)
    def test_all_four_source_BIN_identities_required(self):
        for key in ('pbin','gbin','owner_pbin','owner_gbin'):
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,'identity'):self.invoke(**{key:b'changed'})
    def test_body_offset_opt_in_requires_its_own_pinned_sources(self):
        for key in ('ps2_sha256','gc_sha256'):
            bad=copy.deepcopy(self.contract);bad['owner_bind_contract'][key]='0'*64
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,'identity'):self.invoke(contract=bad)
    def test_unknown_policy_or_extra_contract_field_refused(self):
        for extra in ({'kind':'unsupported'}, {'unexpected':True}):
            bad=dict(self.contract,**extra)
            with self.subTest(extra=extra),self.assertRaisesRegex(ValueError,'contract'):self.invoke(contract=bad)
    def test_body_hierarchy_must_remain_same_id_parent(self):
        bad=copy.deepcopy(self.owner);bad[2]['parent']=-1
        with self.assertRaisesRegex(ValueError,'same-id/parent'):self.invoke(owner_ps2=bad)
    def test_every_weight_must_exist_in_all_three_original_tables(self):
        for weights,change in (({3},{}),({True},{}),({1},{}),({2},{'source_bones':self.child[:2]})):
            with self.subTest(weights=weights,change=change),self.assertRaisesRegex(ValueError,'weights'):self.invoke(weighted=weights,**change)
    def test_nonfinite_or_unordered_unused_PS2_record_refused(self):
        for value in (dict(id=0,parent=-1,pos=[float('nan'),0.,0.]),dict(id=0,parent=2,pos=[0.,0.,0.]),dict(id=3,parent=-1,pos=[0.,0.,0.])):
            with self.subTest(value=value),self.assertRaisesRegex(ValueError,'original attachment'):self.invoke(source_bones=[value]+self.child)
    def test_conflicting_duplicate_metadata_is_not_collapsed(self):
        bad=copy.deepcopy(self.child);bad[1]['pos'][0]+=1
        with self.assertRaisesRegex(ValueError,'duplicate'):self.invoke(source_bones=bad)
    def test_GC_section_owner_parent_and_finite_matrix_required(self):
        for key,value in (('parent',0),('attach',3),('rest',[[float('nan')]*4]*4)):
            bad=copy.deepcopy(self.section);bad[0][key]=value
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,'GC'):self.invoke(section_gc=bad)
    def test_unweighted_GC_rest_parent_retained_without_changing_body(self):
        extra=dict(self.gc[1],id=1,parent=-1)
        section=self.section+[extra]
        selected,proof=self.invoke(section_gc=section)
        self.assertEqual(selected,self.owner)
        self.assertEqual(proof['original_GC_rest_records'],section)
        self.assertEqual(selected[1]['parent'],0)
        bad=copy.deepcopy(section);bad[1]['parent']=3
        with self.assertRaisesRegex(ValueError,'GC'):self.invoke(section_gc=bad)
    def test_body_boolean_indices_or_nonfinite_unused_translation_refused(self):
        bad=copy.deepcopy(self.gc);bad[1]['id']=True
        with self.assertRaisesRegex(ValueError,'original body owner'):self.invoke(owner_gc=bad)
        bad=copy.deepcopy(self.gc);bad[0]['translation'][0]=float('nan')
        with self.assertRaisesRegex(ValueError,'original body owner'):self.invoke(owner_gc=bad)
    def test_legacy_identity_contract_stays_closed_to_retarget_partial_sections(self):
        bad={k:v for k,v in self.contract.items() if k!='owner_bind_contract'};bad['kind']='source-pinned-body-owner-attachment'
        with self.assertRaises(ValueError):self.invoke(contract=bad)

if __name__=='__main__':unittest.main()