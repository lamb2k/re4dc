"""Refuse attachment source/owner contract violations without touching runtime."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import copy
import unittest
import ps2_cast as pc

class AttachmentOwnerTests(unittest.TestCase):
    def setUp(self):
        self.data = (b'attachment-ps2', b'attachment-gc', b'owner-ps2', b'owner-gc')
        self.contract = dict(kind='source-pinned-body-owner-attachment', **{
            k: pc.sha(v) for k,v in zip(('ps2_sha256','gc_sha256','owner_ps2_sha256','owner_gc_sha256'),self.data)})
        self.owner = [dict(id=0,parent=-1,pos=[0.,0.,0.]),dict(id=1,parent=0,pos=[0.,1.,0.])]
        self.gc = [dict(id=q['id'],attach=q['id'],parent=q['parent'],translation=list(q['pos'])) for q in self.owner]
        # Unused attachment metadata includes a second rest record for ID0.
        self.child = copy.deepcopy(self.owner)+[dict(id=0,parent=-1,pos=[50.,0.,0.])]
    def run_contract(self, **changes):
        a=dict(pbin=self.data[0],gbin=self.data[1],owner_pbin=self.data[2],owner_gbin=self.data[3],
               source_bones=self.child,owner_ps2=self.owner,section_gc=self.gc,owner_gc=self.gc,
               weighted={1},contract=self.contract,bone_tol=.001)
        a.update(changes)
        return pc.source_attachment_owner_skeleton(**a)
    def test_complete_metadata_preserved_and_owner_used(self):
        before=copy.deepcopy(self.child)
        selected,proof=self.run_contract()
        self.assertEqual(selected,self.owner)
        self.assertEqual(proof['original_PS2_rest_records'],before)
        self.assertEqual(self.child,before)
        self.assertEqual(proof['original_PS2_rest_record_count'],3)
    def test_each_source_identity_is_required(self):
        for key in ('pbin','gbin','owner_pbin','owner_gbin'):
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,'identity'):
                self.run_contract(**{key:b'changed'})
    def test_weights_cannot_escape_body_owner(self):
        with self.assertRaisesRegex(ValueError,'weights'):
            self.run_contract(weighted={2})
    def test_gc_attachment_must_share_actual_owner(self):
        bad=copy.deepcopy(self.gc);bad[1]['translation'][1]+=.002
        with self.assertRaisesRegex(ValueError,'rest'):
            self.run_contract(section_gc=bad)
    def test_owner_hierarchy_cannot_be_retargeted(self):
        bad=copy.deepcopy(self.owner);bad[1]['parent']=-1
        with self.assertRaisesRegex(ValueError,'hierarchy'):
            self.run_contract(owner_ps2=bad)
    def test_unknown_original_ids_or_nonfinite_metadata_refused(self):
        for field,value in (('id',2),('pos',[float('nan'),0.,0.])):
            bad=copy.deepcopy(self.child);bad[-1][field]=value
            with self.subTest(field=field),self.assertRaisesRegex(ValueError,'original rest'):
                self.run_contract(source_bones=bad)

if __name__=='__main__':unittest.main()
