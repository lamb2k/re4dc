"""PUBLIC composition, budget and authorization controls. No actual bind/media."""
import contextlib
import dataclasses
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
import adapter as a
import source_quad as q
import test_source_quad as public

class AdapterControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(dir='/dev/shm');root=Path(__file__).resolve().parents[5]
        raw=subprocess.check_output(['git','-C',str(root),'show','4305e0eca9b0f5261a67ab3433e09ab63c9537db:port/dreamcast/tools/d367/triangle_partition24/partition.py'])
        if hashlib.sha256(raw).hexdigest()!='f227a5bf26ae4d65ca97481f92d3e3220beee3cbbf6979cd8299ba1b827f0278':raise ValueError('Frozen public composition helper drift')
        path=Path(cls.temp.name)/'partition.py';path.write_bytes(raw);spec=importlib.util.spec_from_file_location('quad_adapter_public_partition',path);cls.old=importlib.util.module_from_spec(spec);sys.modules[spec.name]=cls.old;spec.loader.exec_module(cls.old)
        cls.f=public.Controls()
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def oldcase(self,n=1,sources=None):
        old=self.old;parents=tuple(old.Parent(p.occurrence,p.indices,p.affine_sha256,p.vertices) for p in (self.f.parent(ordinal=i) for i in range(n)))
        inv=old.Inventory(parents,'d'*64,old.inventory_digest(parents,'d'*64));panel=self.f.panel();op=old.PhysicalPanel(panel.identifier,panel.record,panel.source_binding_sha256,panel.faces)
        if sources is None:sources=(types.SimpleNamespace(key=(1,0),reason=None,fixed=old.FixedFace(op,0)),)
        return types.SimpleNamespace(identifier=(0,'PUBLIC'),inventory=inv,eye_box=(self.f.eyes().low,self.f.eyes().high),sources=tuple(sources),expected_fingerprint='e'*64)
    def case(self,n=1,sources=None):return a.convert_case(self.oldcase(n,sources))
    def budget(self,caps=a.CAPS,clock=lambda:0):return a.Budget(caps,clock,100)
    def test_prebound_inventory_digest_is_byte_identical_not_recomputed_subset(self):
        old=self.oldcase(2);case=a.convert_case(old)
        self.assertEqual(case.inventory.expected_inventory_sha256,old.inventory.expected_inventory_sha256)
        self.assertEqual(q.inventory_digest(case.inventory.parents,case.inventory.source_binding_sha256),old.inventory.expected_inventory_sha256)
        self.assertEqual([dataclasses.asdict(p) for p in case.inventory.parents],[dataclasses.asdict(p) for p in old.inventory.parents])
        self.assertEqual((case.eyes.low,case.eyes.high),old.eye_box);self.assertEqual(case.eyes.source_binding_sha256,old.expected_fingerprint)
        changed=types.SimpleNamespace(**vars(old));changed.inventory=dataclasses.replace(old.inventory,parents=old.inventory.parents[:1])
        with self.assertRaisesRegex(ValueError,'serialization/binding'):a.convert_case(changed)
    def test_every_old_source_key_face_and_refusal_preserved_first_seen_full_dedup(self):
        old=self.oldcase();one=old.sources[0];two=types.SimpleNamespace(key=(1,1),reason=None,fixed=self.old.FixedFace(one.fixed.panel,1));no=types.SimpleNamespace(key=(9,0),reason='PUBLIC_UNREPRESENTABLE',fixed=None)
        old.sources=(one,two,no);case=a.convert_case(old)
        self.assertEqual(len(case.panels),1);self.assertEqual([m.key for m in case.source_mappings],[s.key for s in old.sources]);self.assertEqual([m.panel_index for m in case.source_mappings],[0,0,None]);self.assertEqual([m.face for m in case.source_mappings],[0,1,None]);self.assertEqual(case.source_mappings[2].reason,no.reason)
        self.assertEqual(dataclasses.asdict(case.panels[0]),dataclasses.asdict(one.fixed.panel))
        with patch.object(a,'make_assignment',side_effect=AssertionError('conversion cannot form a coverage certificate')):a.convert_case(old)
    def test_aliases_duplicate_keys_and_unrepresentable_geometry_refuse(self):
        old=self.oldcase();first=old.sources[0];p=first.fixed.panel
        for other in (dataclasses.replace(p,source_binding_sha256='f'*64),dataclasses.replace(p,identifier=2)):
            s=types.SimpleNamespace(key=(2,0),reason=None,fixed=self.old.FixedFace(other,0))
            with self.assertRaisesRegex(ValueError,'alias'):a.convert_case(self.oldcase(sources=(first,s)))
        with self.assertRaisesRegex(ValueError,'ordered source keys'):a.convert_case(self.oldcase(sources=(first,first)))
        with self.assertRaisesRegex(ValueError,'Unrepresentable'):a.convert_case(self.oldcase(sources=(types.SimpleNamespace(key=(1,0),reason='FAIL',fixed=first.fixed),)))
    def test_one_first_normal_sign_whole_domain_no_axis_or_per_parent_search(self):
        panel=self.f.panel();assignment=a.make_assignment(panel,self.f.eyes())
        normal=q._normal(panel.faces[0],q.Limits());self.assertEqual(assignment.functional,tuple(-v for v in normal));self.assertEqual(assignment.orientation,1)
        # Mirroring all source/eye/target positions preserves exact actual winding;
        # the other sign of the first face's transformed normal is selected.
        def mirror(point):return (-point[0],point[1],point[2])
        mirrored=dataclasses.replace(panel,faces=tuple(tuple(mirror(p) for p in t) for t in panel.faces))
        chosen=a.make_assignment(mirrored,self.f.eyes());self.assertEqual(chosen.functional,q._normal(mirrored.faces[0],q.Limits()));self.assertEqual(chosen.orientation,-1)
        result=q.cover_triangle(self.f.eyes(),dataclasses.replace(self.f.parent(),vertices=tuple(mirror(p) for p in self.f.parent().vertices)),chosen)
        self.assertIs(type(result),q.TriangleOpportunity)
        crossing=self.f.eyes((-1,-1,0),(1,1,2));self.assertEqual(a.make_assignment(panel,crossing).reason,'NO_FIXED_FIRST_NORMAL_DEPTH')
    def test_all_originals_one_complete_final_call_and_honest_counters(self):
        case=self.case(2);budget=self.budget();calls=a.Calls()
        with patch.object(q,'cover_assigned',wraps=q.cover_assigned) as final:rows=a.execute((case,),budget,calls)
        row=rows[0];self.assertEqual(row['status'],'NOMINAL_EXACT_REAL_OPPORTUNITY_ONLY');self.assertEqual(row['complete_originals'],2);self.assertEqual(len(row['assignments']),2);self.assertEqual(final.call_count,1);self.assertEqual(len(final.call_args.args[0].parents),2);self.assertEqual(len(final.call_args.args[2]),2)
        self.assertEqual(budget.used,(2,256,2,256));self.assertIsNone(budget.active);self.assertEqual(calls.candidate_primitives,2);self.assertEqual(calls.final_batches,1);self.assertEqual(calls.certificate_formations,1)
    def test_four_atomic_caps_before_certificate_or_candidate_and_refund_only_close(self):
        case=self.case(2);values=a.reservation(case)
        for i in range(4):
            caps=tuple(v-(j==i) for j,v in enumerate(values));budget=self.budget(caps);calls=a.Calls()
            with patch.object(a,'make_assignment',side_effect=AssertionError('not reserved')):rows=a.execute((case,case),budget,calls)
            self.assertTrue(all(r['status']=='UNTESTED_UNKNOWN_BUDGET' and not r['started'] for r in rows));self.assertEqual(budget.used,(0,0,0,0));self.assertEqual(calls.candidate_primitives,0)
        budget=self.budget(values);self.assertTrue(budget.reserve(values));budget.candidate()
        with self.assertRaises(a.CounterFault):budget.reserve((0,0,0,0))
        budget.close();self.assertEqual(budget.used,(1,128,0,0));self.assertFalse(budget.reserve(values));self.assertTrue(budget.reserve((1,128,1,128)));budget.close()
    def test_malformed_counters_reservations_cannot_bypass_caps(self):
        for caps in ((-1,1,1,1),(1.0,1,1,1),(True,1,1,1),(100001,12800000,2667,341376)):
            with self.assertRaises(ValueError):self.budget(caps)
        b=self.budget()
        for values in ((-1,1,1,1),(1,1,1),(1,1,1,1.0),(True,1,1,1)):
            with self.assertRaises(a.CounterFault):b.reserve(values)
        b.reserve((1,128,1,128))
        for values in ((-1,1,1,1),(1,1,1),(1,1,1,1.0),(2,256,0,0)):
            with self.assertRaises(a.CounterFault):b.take(values)
        self.assertEqual(b.used,(0,0,0,0));b.close()
    def test_no_functional_and_no_full_panels_never_finalizes(self):
        old=self.oldcase();case=self.case();case=dataclasses.replace(case,eyes=q.EyeBox((0,0,0),(0,0,2),'e'*64));case=dataclasses.replace(case,expected_fingerprint=a.token(a.case_record(case)))
        calls=a.Calls();budget=self.budget();row=a.execute((case,),budget,calls)[0]
        self.assertEqual(row['status'],'UNKNOWN_NO_FIXED_PANEL');self.assertEqual(calls.candidate_primitives,0);self.assertEqual(calls.certificate_formations,1);self.assertEqual(budget.used,(1,128,0,0));self.assertEqual(calls.final_batches,0)
        old.sources=(types.SimpleNamespace(key=(3,0),reason='PUBLIC_UNREPRESENTABLE',fixed=None),);empty=a.convert_case(old);calls=a.Calls();row=a.execute((empty,),self.budget(),calls)[0]
        self.assertEqual(row['status'],'UNKNOWN_NO_FIXED_PANEL');self.assertEqual(calls.candidate_primitives,0);self.assertEqual(calls.final_batches,0)
    def test_last_original_failure_discards_all_partial_assignments(self):
        old=self.oldcase(2);last=dataclasses.replace(old.inventory.parents[1],vertices=((20,0,3),(21,0,3),(20,1,3)))
        parents=(old.inventory.parents[0],last);old.inventory=dataclasses.replace(old.inventory,parents=parents,expected_inventory_sha256=self.old.inventory_digest(parents,old.inventory.source_binding_sha256));case=a.convert_case(old);calls=a.Calls();row=a.execute((case,),self.budget(),calls)[0]
        self.assertEqual(row['status'],'UNKNOWN_NO_FIXED_PANEL');self.assertEqual(row['first_uncovered_original'],1);self.assertNotIn('assignments',row);self.assertEqual(calls.final_batches,0)
    def test_global17_across_originals_refuses_before_final(self):
        sources=[]
        for i in range(17):
            p=self.f.panel(identifier=i+1);p=self.old.PhysicalPanel(p.identifier,p.record,p.source_binding_sha256,p.faces)
            sources.append(types.SimpleNamespace(key=(i,0),reason=None,fixed=self.old.FixedFace(p,0)))
        case=self.case(17,sources);calls=a.Calls();real=q.cover_triangle
        def force_each(eyes,parent,assignment):
            if assignment.panel.identifier!=parent.occurrence[-1]+1:return q.Unknown('PUBLIC_FORCE_DISTINCT')
            return real(eyes,parent,assignment)
        with patch.object(q,'cover_triangle',side_effect=force_each):row=a.execute((case,),self.budget(),calls)[0]
        self.assertEqual(row['status'],'UNKNOWN_GLOBAL_PANEL_LIMIT');self.assertEqual(calls.final_batches,0);self.assertNotIn('assignments',row)
    def test_incomplete_or_failed_final_is_never_a_partial_positive(self):
        case=self.case(2);real=q.cover_assigned
        def incomplete(*args):
            result=real(*args);return dataclasses.replace(result,triangles=result.triangles[:-1])
        for result in (q.Unknown('PUBLIC_FINAL'),):
            with patch.object(q,'cover_assigned',return_value=result):row=a.execute((case,),self.budget(),a.Calls())[0]
            self.assertEqual(row['status'],'UNKNOWN_FINAL_PUBLIC_FINAL');self.assertNotIn('assignments',row)
        with patch.object(q,'cover_assigned',side_effect=incomplete):row=a.execute((case,),self.budget(),a.Calls())[0]
        self.assertEqual(row['status'],'UNKNOWN_FINAL_INCOMPLETE_RESULT');self.assertNotIn('assignments',row)
    def test_deadline_after_candidate_or_final_halts_remaining_rows(self):
        case=self.case();real_triangle=q.cover_triangle;real_final=q.cover_assigned
        for name,real in (('cover_triangle',real_triangle),('cover_assigned',real_final)):
            clock=[0];budget=self.budget(clock=lambda:clock[0])
            def late(*args):answer=real(*args);clock[0]=100;return answer
            with patch.object(q,name,side_effect=late):rows=a.execute((case,case),budget,a.Calls())
            self.assertEqual(rows[0]['status'],'UNKNOWN_WALL_BUDGET');self.assertFalse(rows[1]['started']);self.assertNotIn('assignments',rows[0]);self.assertIsNone(budget.active)
    def test_allocation_and_counter_failures_remain_unknown_and_halt(self):
        case=self.case()
        for name in ('make_assignment',):
            for error in (MemoryError,OverflowError):
                with patch.object(a,name,side_effect=error):rows=a.execute((case,case),self.budget(),a.Calls())
                self.assertEqual(rows[0]['status'],'UNKNOWN_MEMORY_ALLOCATION');self.assertFalse(rows[1]['started'])
        for name in ('cover_triangle','cover_assigned'):
            with patch.object(q,name,return_value=q.Unknown('MEMORY_ALLOCATION')):rows=a.execute((case,case),self.budget(),a.Calls())
            self.assertIn(rows[0]['status'],('UNKNOWN_MEMORY_ALLOCATION','UNKNOWN_FINAL_MEMORY_ALLOCATION'));self.assertFalse(rows[1]['started']);self.assertNotIn('assignments',rows[0])
        budget=self.budget()
        with patch.object(budget,'candidate',side_effect=a.CounterFault),patch.object(a,'make_assignment',side_effect=AssertionError('counter failure cannot form certificate')):rows=a.execute((case,case),budget,a.Calls())
        self.assertEqual(rows[0]['status'],'UNKNOWN_COUNTER_BUDGET');self.assertFalse(rows[1]['started']);self.assertIsNone(budget.active)
    def test_converted_drift_is_refused_before_candidate(self):
        case=self.case();case=dataclasses.replace(case,panels=case.panels[::-1],identifier=(9,'FOREIGN'))
        with patch.object(a,'make_assignment',side_effect=AssertionError('drift cannot enter predicates')):
            with self.assertRaisesRegex(ValueError,'case drift'):a.execute((case,),self.budget(),a.Calls())
    def test_exact_grant_all_fixed_fields_and_payload_hashes(self):
        with tempfile.TemporaryDirectory(dir='/dev/shm') as temp:
            root=Path(temp);reader=root/'reader';prepared=root/'prepared';out=root/'out';review=root/'review';review.write_text('PUBLIC synthetic source review');sha=a.pin(review)['sha256'];grant=root/'grant';valid=a.grant_binding('a'*40,sha,reader,prepared,out)
            def write(value):grant.write_text(json.dumps(value));return a.pin(grant)['sha256']
            gs=write(valid);a.authorize(grant,gs,review,sha,'a'*40,reader,prepared,out)
            with self.assertRaises(ValueError):a.authorize(None,None,review,sha,'a'*40,reader,prepared,out)
            for key in valid:
                changed=dict(valid);changed[key]='FOREIGN';gs=write(changed)
                with self.subTest(field=key),self.assertRaises(ValueError):a.authorize(grant,gs,review,sha,'a'*40,reader,prepared,out)
            gs=write(valid);grant.write_text(grant.read_text()+' ')
            with self.assertRaisesRegex(ValueError,'Frozen input changed'):a.authorize(grant,gs,review,sha,'a'*40,reader,prepared,out)
            gs=write(valid);review.write_text('changed')
            with self.assertRaisesRegex(ValueError,'Frozen input changed'):a.authorize(grant,gs,review,sha,'a'*40,reader,prepared,out)
    def test_default_and_missing_grant_touch_no_reader_or_private_inputs(self):
        with tempfile.TemporaryDirectory(dir='/dev/shm') as temp:
            root=Path(temp);common=['adapter.py','--repo',str(root/'source'),'--expected-source','a'*40,'--reader-repo',str(root/'reader'),'--prepared-directory',str(root/'private')]
            with patch.object(a,'own_sources',return_value={}),patch.object(a,'bind_cases',side_effect=AssertionError('NO PRIVATE AUTHENTICATION')),patch.object(a,'load_reader',side_effect=AssertionError('NO READER LOAD')),patch.object(q,'cover_triangle',side_effect=AssertionError('NO COVERAGE')),contextlib.redirect_stdout(io.StringIO()):
                out=root/'default'
                with patch.object(sys,'argv',common+['--out',str(out)]):a.main()
                d=json.loads((out/'report.json').read_text());self.assertEqual(d['classification'],'HELD_SOURCE_ONLY_NO_PRIVATE_INPUTS_OR_PREDICATES');self.assertEqual(d['private_reader_invocations'],0);self.assertEqual(d['candidate_primitives'],0);self.assertEqual(d['final_batches'],0);self.assertEqual(d['input_authentication'],'NOT_RUN')
                denied=root/'denied'
                with patch.object(sys,'argv',common+['--out',str(denied),'--execute']),self.assertRaisesRegex(ValueError,'separately pinned root grant'):a.main()
                self.assertFalse(denied.exists())
    def test_public_source_pin_drift_and_reader_alias_restoration(self):
        with tempfile.TemporaryDirectory(dir='/dev/shm') as temp:
            root=Path(temp);folder=root/'port/dreamcast/tools/d367/source_quad24';folder.mkdir(parents=True);raw={name:('PUBLIC '+name).encode() for name in a.OWNED}
            for name,data in raw.items():(folder/name).write_bytes(data)
            gp={name:hashlib.sha256(raw[name]).hexdigest() for name in a.GENERIC_PINS}
            def git(args):return raw[args[-1].split('/')[-1]]
            with patch.object(a,'__file__',str(folder/'adapter.py')),patch.object(a,'GENERIC_PINS',gp),patch.object(subprocess,'check_output',side_effect=git):
                self.assertEqual(len(a.own_sources(root,'a'*40)),6);(folder/'ADAPTER.md').write_text('changed')
                with self.assertRaisesRegex(ValueError,'source changed'):a.own_sources(root,'a'*40)
            reader=root/'reader';rf=reader/'port/dreamcast/tools/d367/triangle_partition24';rf.mkdir(parents=True)
            code={'prepare_private.py':b'flag="PUBLIC"\n','verify_private.py':b'import prepare_private as prep\n','runner.py':b'import prepare_private as prep\nimport verify_private as verify\n'}
            for name,data in code.items():(rf/name).write_bytes(data)
            pins={name:hashlib.sha256(data).hexdigest() for name,data in code.items()}
            saved={name:sys.modules.get(name) for name in ('prepare_private','verify_private')}
            with patch.object(a,'READER_PINS',pins),patch.object(subprocess,'check_output',side_effect=lambda args:code[args[-1].split('/')[-1]]):
                module,binding=a.load_reader(reader);self.assertEqual(module.prep.flag,'PUBLIC');self.assertIs(module.verify.prep,module.prep)
                self.assertEqual({name:sys.modules.get(name) for name in saved},saved)
                (rf/'runner.py').write_text('changed')
                with self.assertRaisesRegex(ValueError,'reader source changed'):a.load_reader(reader)
    def test_frozen_case_universe_mismatch_refuses_before_conversion(self):
        mock=types.SimpleNamespace(bind=lambda *args:({},(self.oldcase(),),self.old,{}),prep=types.SimpleNamespace(token=a.token))
        with patch.object(a,'load_reader',return_value=(mock,{})),patch.object(a,'convert_case',side_effect=AssertionError('universe changed')):
            with self.assertRaisesRegex(ValueError,'authenticated75'):a.bind_cases(Path('/PUBLIC'),Path('/PUBLIC'),Path('/PUBLIC'))

if __name__=='__main__':unittest.main()
