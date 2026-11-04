"""Original body ownership is explicit, hash-pinned and independently re-derived."""
import copy
from pathlib import Path
import sys
import json
import tempfile
import unittest
from types import SimpleNamespace as NS
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools/d367'))
import model_registry_owner as owner


class OriginalOwnerTests(unittest.TestCase):
    def setUp(self):
        self.pbins=[b'original PS2 owner',b'original PS2 section']
        self.gbins=[b'original GC owner',b'original GC section']
        def part(i,parent,attach,pos):
            return NS(no=i,parent=parent,attach=attach,pos=tuple(pos))
        self.gc=[NS(parts=[part(0,-1,0,[0,100,0]),part(1,0,1,[10,0,0]),part(2,1,2,[20,0,0])]),
                 NS(parts=[part(0,0,1,[10,0,0]),part(1,0,2,[20,0,0])])]
        self.ps=[NS(bones=[dict(id=0,parent=-1,pos=[0,105,0]),dict(id=1,parent=0,pos=[12,0,0]),dict(id=2,parent=1,pos=[18,0,0])]),
                 NS(bones=[dict(id=1,parent=-1,pos=[12,105,0]),dict(id=1,parent=-1,pos=[12,105,0])])]
        for p in self.ps:p.triangles=[(0,[dict(w=[(1,1.)])]*3)]
        bodyhash=dict(kind='same-id-parent-gc-inverse-bind',ps2_sha256=owner.sha(self.pbins[0]),gc_sha256=owner.sha(self.gbins[0]))
        self.source=dict(bones=[],source_bind_offsets={'0':dict(contract=bodyhash)})
        for i,(parent,x) in enumerate(((-1,0),(0,10),(1,30))):
            rest=[[1.,0.,0.,float(x)],[0.,1.,0.,100.],[0.,0.,1.,0.],[0.,0.,0.,1.]]
            self.source['bones'].append(dict(id=i,parent=parent,rest=rest))
        self.bindings=[dict(bin=5+i,parts=len(g.parts),part_bindings=owner._gc_parts(g)) for i,g in enumerate(self.gc)]
        rows=[]
        for g in owner._gc_parts(self.gc[1]):
            rest=[[float(r==c) for c in range(4)] for r in range(4)]
            rows.append(dict(g,rest=rest))
        proof=dict(kind='source-pinned-retarget-owner-attachment',source_BIN_sha256=dict(ps2_sha256=owner.sha(self.pbins[1]),gc_sha256=owner.sha(self.gbins[1]),owner_ps2_sha256=bodyhash['ps2_sha256'],owner_gc_sha256=bodyhash['gc_sha256']),owner_parts=3,weighted_ids=[1],owner_bind_offsets=dict(contract=bodyhash),original_PS2_rest_records=copy.deepcopy(self.ps[1].bones),original_PS2_rest_record_count=2,original_GC_rest_records=rows,original_GC_rest_record_count=2)
        self.source['attachment_owner_skeletons']={'1':proof}
        self.chunks=[dict(source_info=i,weights=[((1,0,0),1,[1.,0.,0.])]) for i in range(2)]
        self.contract=dict(owner_bin=5)
    def invoke(self):
        return owner.prove_tables(self.source,self.bindings,self.chunks,self.contract,self.ps,self.gc,self.pbins,self.gbins)
    def test_partial_duplicates_and_unused_parent_metadata_are_retained(self):
        before=copy.deepcopy((self.source,self.bindings));r=self.invoke()
        self.assertEqual(r['owner_parts'],3);self.assertEqual(r['sections'][0]['weighted_ids'],[1])
        self.assertEqual((self.source,self.bindings),before)
    def test_every_original_source_BIN_identity_is_required(self):
        for which,k in (('p',0),('p',1),('g',0),('g',1)):
            with self.subTest(which=which,k=k):
                data=self.pbins if which=='p' else self.gbins;old=data[k];data[k]=b'changed'
                with self.assertRaises(ValueError):self.invoke()
                data[k]=old
    def test_original_body_owner_cannot_be_replaced(self):
        self.source['bones'][1]['rest'][0][3]+=1
        with self.assertRaisesRegex(ValueError,'unchanged original'):self.invoke()
    def test_first_info_must_be_original_modelInit_body(self):
        self.contract['owner_bin']=6
        with self.assertRaisesRegex(ValueError,'first modelInit'):self.invoke()
    def test_no_attachment_proof_may_be_missing_or_added(self):
        for proofs in ({},{'1':self.source['attachment_owner_skeletons']['1'],'2':{}}):
            old=self.source['attachment_owner_skeletons'];self.source['attachment_owner_skeletons']=proofs
            with self.assertRaisesRegex(ValueError,'exactly once'):self.invoke()
            self.source['attachment_owner_skeletons']=old
    def test_raw_GC_binding_metadata_must_match_original(self):
        self.bindings[1]['part_bindings'][1]['parent']=1
        with self.assertRaisesRegex(ValueError,'original GC BIN'):self.invoke()
    def test_native_weight_cannot_escape_original_section(self):
        self.chunks[1]['weights']=[((2,0,0),1,[1.,0.,0.])]
        with self.assertRaisesRegex(ValueError,'weights escape'):self.invoke()
    def test_weighted_GC_parent_must_still_name_original_owner(self):
        self.gc[1].parts[0].parent=2;g=owner._gc_parts(self.gc[1]);self.bindings[1]['part_bindings']=g
        self.source['attachment_owner_skeletons']['1']['original_GC_rest_records'][0]['parent']=2
        with self.assertRaisesRegex(ValueError,'weighted original GC'):self.invoke()
    def test_conflicting_duplicate_PS2_records_are_refused(self):
        self.ps[1].bones[1]['pos'][0]+=1
        self.source['attachment_owner_skeletons']['1']['original_PS2_rest_records']=copy.deepcopy(self.ps[1].bones)
        with self.assertRaisesRegex(ValueError,'conflicting original duplicate'):self.invoke()
    def test_nonfinite_unused_metadata_is_refused(self):
        self.source['attachment_owner_skeletons']['1']['original_GC_rest_records'][1]['rest'][0][0]=float('nan')
        with self.assertRaisesRegex(ValueError,'nonfinite'):self.invoke()
    def test_actual_weight_ids_not_a_declaration_drive_validation(self):
        self.ps[1].triangles=[(0,[dict(w=[(2,1.)])]*3)]
        with self.assertRaises(ValueError):self.invoke()
    def test_canonical_pin_keeps_duplicate_order_and_rejects_nonfinite(self):
        self.assertNotEqual(owner.canonical([dict(id=1),dict(id=1)]),owner.canonical([dict(id=1)]))
        with self.assertRaises(ValueError):owner.canonical(dict(x=float('nan')))

    def test_loader_manifest_and_source_header_archive_pins_are_mandatory(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);header=root/'header';header.write_bytes(b'header');data=root/'ps2.dat';data.write_bytes(b'PS2DAT')
            source=dict(self.source,source_archive='example',source_archive_sha256='a'*64,ps2_archive_sha256=owner.sha(data.read_bytes()))
            contract=dict(schema='re4dc-source-body-owner-1',source_sha256=owner.canonical(source),bindings_sha256=owner.canonical(self.bindings),header_sha256=owner.sha(header.read_bytes()),ps2_archive=str(data),ps2_archive_sha256=owner.sha(data.read_bytes()),gc_archive_sha256='a'*64,owner_bin=5)
            class Inputs:
                def take(self,path,rel):return path
            path=root/'contract.json'
            def attempt(value,wrong_selection=False):
                path.write_text(json.dumps(value));selection=dict(path=str(path),sha256='0'*64 if wrong_selection else owner.sha(path.read_bytes()))
                return owner.prove(Inputs(),dict(name='example',source_owner_contract=selection),source,self.bindings,None,'a'*64,str(header),self.chunks)
            with self.assertRaisesRegex(ValueError,'manifest hash'):attempt(contract,True)
            with self.assertRaisesRegex(ValueError,'schema/fields'):attempt(dict(contract,unexpected=True))
            for key in ('source_sha256','bindings_sha256','header_sha256','gc_archive_sha256','ps2_archive_sha256'):
                bad=dict(contract);bad[key]='0'*64
                with self.subTest(key=key),self.assertRaisesRegex(ValueError,'identity changed'):attempt(bad)



if __name__=='__main__':unittest.main()
