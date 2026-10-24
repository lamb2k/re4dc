"""PUBLIC fixtures only: no private binder, input report or scene predicate."""
from dataclasses import replace
from fractions import Fraction as F
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
import original_chunks_adapter as z
a,c,q=z.a,z.c,z.q

class Controls(unittest.TestCase):
    def case(self,hidden=(True,),rank=0,size=2000,panel_id=1):
        qa=a.q;ps=[]
        for i,hide in enumerate(hidden):
            verts=((F(-1,2),F(1,2),3),(F(1,2),F(-1,2),3),(F(1,2),F(1,2),3))
            if not hide:verts=tuple((x+20,y,w) for x,y,w in verts)
            ps.append(qa.Parent((100+rank,2,3,4,0,5,i),(0,1,2),'c'*64,verts))
        inv=qa.Inventory(tuple(ps),'d'*64,qa.inventory_digest(tuple(ps),'d'*64))
        r=F(1,100) if size==2000 else F(1,200) if size==500 else F(1,300)
        eyes=qa.EyeBox((-r,)*3,(r,)*3,'a'*64)
        pts=((-1,-1,1),(1,-1,1),(1,1,1),(-1,1,F(3,2)))
        p=qa.PhysicalPanel(panel_id,(panel_id,2,3,4,5,0,1,2,0,2,3),'b'*64,((pts[0],pts[1],pts[2]),(pts[0],pts[2],pts[3])))
        mappings=(a.SourceMap((7,0),0,0,None),a.SourceMap((7,1),1,0,None),a.SourceMap((9,0),None,None,'PUBLIC_UNREPRESENTABLE'))
        old=a.Case((rank,100+rank,2,3,4,0,5,'hut',647,size),inv,eyes,(p,),mappings,'e'*64,'')
        return replace(old,expected_fingerprint=a.token(a.case_record(old)))
    def retoken(self,case):return replace(case,expected_fingerprint=a.token(a.case_record(case)))
    def run_case(self,cases,budget=None,clock=lambda:0):
        return z.run(tuple(cases),c.Budget() if budget is None else budget,100,clock)
    def test_distinct_qclass_identity_exact_full_serialization_bridge(self):
        old=self.case((False,True));new=z.bridge(old)
        self.assertIsNot(a.q.Parent,q.Parent);self.assertIs(type(old.inventory),a.q.Inventory);self.assertIs(type(new.inventory),q.Inventory)
        self.assertEqual(a.case_record(old),a.case_record(new));self.assertEqual(old.expected_fingerprint,new.expected_fingerprint)
        self.assertEqual(new.source_mappings,old.source_mappings);self.assertEqual([x.face for x in new.source_mappings],[0,1,None])
        self.assertEqual(q.inventory_digest(new.inventory.parents,new.inventory.source_binding_sha256),old.inventory.expected_inventory_sha256)
    def test_case_or_inventory_tamper_refuses_before_primitives(self):
        old=self.case((True,True));inv=replace(old.inventory,parents=old.inventory.parents[:1])
        for bad in (replace(old,inventory=inv),self.retoken(replace(old,inventory=inv))):
            with patch.object(q,'cover_triangle',side_effect=AssertionError('early predicate')):
                with self.assertRaises(ValueError):z.bridge(bad)
    def test_every_original_after_unproved_is_visited_and_finally_rechecked(self):
        old=self.case((False,True,False,True));r=self.run_case((old,));row=r['results'][0]
        self.assertEqual(row['covered_originals'],(1,3));self.assertEqual(row['unproved_draw_originals'],(0,2))
        self.assertEqual((row['candidate_attempts'],row['final_original_checks']),(4,2));self.assertEqual(r['calls'],dict(candidate_primitives=4,final_primitives=2))
        self.assertEqual(row['covered_triangle_corner_references'],6);self.assertEqual(row['exclusively_covered_local_indices'],())
        self.assertIsNone(row['actual_removed_transform_corners']);self.assertIsNone(row['modelled_ms']);self.assertFalse(row['nominal_cell_union_complete'])
    def test_fullpanel_first_normal_unknown_still_charges_each_original_slot(self):
        old=self.case((True,True,True));b=c.Budget()
        with patch.object(a,'make_assignment',return_value=a.q.Unknown('NO_FIXED_FIRST_NORMAL_DEPTH')) as normal:
            r=self.run_case((old,),b)
        self.assertEqual(normal.call_count,1);self.assertEqual((b.candidates,b.finals),(3,0));self.assertEqual(r['calls']['candidate_primitives'],0)
        self.assertEqual(r['results'][0]['unproved_draw_originals'],(0,1,2));self.assertEqual(b.reserved,(3,384,3,384))
    def test_final_failure_halts_and_discards_no_retry_or_partial_acceptance(self):
        original=q.cover_triangle;count=0
        def fail(*args):
            nonlocal count
            count+=1
            return q.Unknown('PUBLIC_FINAL_FAIL') if count==4 else original(*args)
        with patch.object(q,'cover_triangle',side_effect=fail):r=self.run_case((self.case((True,True)),self.case(rank=1)))
        self.assertTrue(r['results'][0]['partial_discarded']);self.assertFalse(r['results'][0]['nominal_cell_union_complete'])
        self.assertFalse(r['results'][1]['started']);self.assertNotIn('covered_originals',r['results'][0]);self.assertEqual(count,4)
    def test_budget_reserves_complete_case_atomically_and_never_refunds(self):
        b=c.Budget((1,128,1,128));r=self.run_case((self.case((True,True)),self.case(rank=1)),b)
        self.assertEqual(r['work']['reserved'],(0,0,0,0));self.assertEqual(r['calls']['candidate_primitives'],0)
        self.assertFalse(r['results'][1]['started'])
        b=c.Budget();self.run_case((self.case(),),b);self.assertEqual(b.reserved,(1,128,1,128));self.assertTrue(z.CAPS[0]>a.CAPS[0])
    def test_wall_and_allocation_refusals_halt_without_hidden_bits(self):
        r=self.run_case((self.case(),),clock=lambda:100)
        self.assertEqual(r['halt'],'UNKNOWN_WALL_BUDGET');self.assertFalse(r['results'][0]['nominal_cell_union_complete'])
        for error in (MemoryError,OverflowError):
            with patch.object(q,'cover_triangle',side_effect=error):r=self.run_case((self.case(),self.case(rank=1)))
            self.assertEqual(r['halt'],'UNKNOWN_MEMORY_ALLOCATION');self.assertFalse(r['results'][1]['started'])
        with patch.object(a,'make_assignment',return_value=a.q.Unknown('MEMORY_ALLOCATION')):r=self.run_case((self.case(),))
        self.assertEqual(r['halt'],'UNKNOWN_MEMORY_ALLOCATION')
    def test_domain_requires_all25_and_global16_and_does_not_count_alternative_lods(self):
        cases=tuple(self.case(rank=i,panel_id=i+1) for i in range(25))
        r=self.run_case(cases);self.assertEqual(r['domains'][0]['status'],'GLOBAL_CELL_FULL_PANEL_LIMIT')
        self.assertTrue(all(not row['nominal_cell_union_complete'] for row in r['results']))
        cases=tuple(self.case(rank=i,panel_id=1) for i in range(25));r=self.run_case(cases)
        self.assertEqual(r['domains'][0]['global_full_panel_dependencies'],(1,));self.assertTrue(all(row['nominal_cell_union_complete'] for row in r['results']))
        self.assertEqual(r['domains'][1]['status'],'INCOMPLETE_25LET_DOMAIN')
    def test_exact_three_domain_signatures_only_after_all_global_unions(self):
        cases=tuple(self.case((False,True),rank=i,size=s) for i in range(25) for s in (2000,500,250))
        r=self.run_case(cases);self.assertIsNone(r['halt']);self.assertEqual(len(r['signatures']),25)
        for s in r['signatures']:
            self.assertEqual([(g['mask'],g['ordinals']) for g in s['groups']],[(0,(0,)),(7,(1,))])
            self.assertEqual(s['drawn_group_counts'],(1,1,1));self.assertEqual(s['cost_gate'],'UNESTABLISHED')
        # Greater-than16 global union cannot leak the old locally covered bits.
        bad=tuple(self.case(rank=i,size=s,panel_id=i+1) for i in range(25) for s in (2000,500,250))
        r=self.run_case(bad)
        self.assertTrue(all([(g['mask'],g['ordinals']) for g in s['groups']]==[(0,(0,))] for s in r['signatures']))
    def test_universe_rejects_truncation_changed_counts_and_nonfinite_caps(self):
        for cases in ((self.case(),),tuple(self.case(rank=i//3,size=(2000,500,250)[i%3]) for i in range(75))):
            with self.assertRaises(ValueError):z.universe(cases)
        for caps in ((-1,0,0,0),(1.,128,1,128),(True,128,1,128)):
            with self.assertRaises(c.Refuse):c.Budget(caps)
        self.assertEqual(z.CAPS,(116088,14859264,2667,341376))
    def args(self,d):
        return types.SimpleNamespace(expected_source='1'*40,reader_repo=d/'reader',prepared_directory=d/'prepared',exposure_report=d/'MISSING.json',out=d/'out',grant=d/'grant.json',grant_sha256=None,review=d/'review.json',review_sha256=None)
    def test_new_rootgrant_exact_oldgrant_scope_caps_and_paths_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp);args=self.args(d);args.review.write_text('PUBLIC SYNTHETIC REVIEW ONLY');args.review_sha256=a.pin(args.review)['sha256']
            expected=z.grant_binding(args.expected_source,args.review_sha256,args.reader_repo,args.prepared_directory,args.exposure_report,args.out)
            for mutate in ('old_scope','caps','path','source','review','profile'):
                value=dict(expected)
                if mutate=='old_scope':value['scope']='SOURCE_QUAD24_PRIVATE_ORIGINAL75_ONLY'
                if mutate=='caps':value['limits']=dict(z.LIMITS,candidate_attempts=100000)
                if mutate=='path':value['output']=str(d/'foreign')
                if mutate=='source':value['adapter_source']='2'*40
                if mutate=='review':value['adapter_review_sha256']='0'*64
                if mutate=='profile':value['profile']=a.PROFILE
                args.grant.write_text(json.dumps(value));args.grant_sha256=a.pin(args.grant)['sha256']
                with self.assertRaises(ValueError):z.authorize(args)
            args.grant.write_text(json.dumps(expected));args.grant_sha256=a.pin(args.grant)['sha256'];self.assertIn('grant',z.authorize(args))
            args.grant_sha256='0'*64
            with self.assertRaises(ValueError):z.authorize(args)
    def test_default_zero_and_execute_without_grant_never_touch_binder_or_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp);args=self.args(d)
            argv=['tool','--repo',str(d/'repo'),'--reader-repo',str(args.reader_repo),'--prepared-directory',str(args.prepared_directory),'--exposure-report',str(args.exposure_report),'--out',str(args.out),'--expected-source',args.expected_source]
            with patch.object(sys,'argv',argv),patch.object(z,'own_sources',return_value={}),patch.object(a,'bind_cases',side_effect=AssertionError('private bind forbidden')),patch.object(z,'exposure_rows',side_effect=AssertionError('metadata read forbidden')),contextlib.redirect_stdout(io.StringIO()):z.main()
            r=json.loads((args.out/'report.json').read_bytes());self.assertEqual(r['private_reader_invocations'],0);self.assertEqual(r['classification'],'HELD_SOURCE_ONLY_ZERO_PRIVATE_CALLS')
            argv[argv.index(str(args.out))]=str(d/'out-execute')
            with patch.object(sys,'argv',argv+['--execute']),patch.object(z,'own_sources',return_value={}),patch.object(a,'bind_cases',side_effect=AssertionError('private bind forbidden')):
                with self.assertRaisesRegex(ValueError,'SEPARATE_NEW_ROOT_GRANT'):z.main()
    def test_private_mode_requires_explicit_one_numeric_thread_before_binding(self):
        import os
        keys=('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','VECLIB_MAXIMUM_THREADS')
        with patch.dict(os.environ,{k:'1' for k in keys}):self.assertEqual(z.numeric_environment(),{k:'1' for k in keys})
        for value in ('2','0','',None):
            env={k:'1' for k in keys}
            if value is None:env.pop(keys[0])
            else:env[keys[0]]=value
            with patch.dict(os.environ,env,clear=True):
                with self.assertRaises(ValueError):z.numeric_environment()
    def test_real_bootstrap_ignores_poisoned_import_caches_and_refuses_source_drift(self):
        import py_compile,subprocess,os
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp);folder=Path(z.__file__).parent
            for name in ('source_quad.py','adapter.py','original_chunks.py','original_chunks_adapter.py'):d.joinpath(name).write_bytes(folder.joinpath(name).read_bytes())
            caches={}
            for name in ('adapter.py','original_chunks.py'):
                p=d/name;original=p.read_bytes();p.write_text("raise RuntimeError('PUBLIC_POISON_SENTINEL')\n")
                cache=Path(py_compile.compile(str(p),invalidation_mode=py_compile.PycInvalidationMode.UNCHECKED_HASH,doraise=True));caches[cache]=cache.read_bytes();p.write_bytes(original)
            env=dict(os.environ,PYTHONPATH=str(d),PYTHONDONTWRITEBYTECODE='1')
            old=subprocess.run([sys.executable,'-B','-c','import adapter'],cwd=d,env=env,capture_output=True);self.assertNotEqual(old.returncode,0)
            ok=subprocess.run([sys.executable,'-B',str(d/'original_chunks_adapter.py'),'--help'],cwd=d,env=env,capture_output=True);self.assertEqual(ok.returncode,0,ok.stderr)
            p=d/'original_chunks.py';p.write_bytes(p.read_bytes()+b'\n# changed\n')
            drift=subprocess.run([sys.executable,'-B',str(d/'original_chunks_adapter.py'),'--help'],cwd=d,env=env,capture_output=True);self.assertNotEqual(drift.returncode,0);self.assertIn(b'PINNED_SOURCE_DRIFT',drift.stderr)
            self.assertTrue(all(p.read_bytes()==b for p,b in caches.items()))

if __name__=='__main__':unittest.main()
