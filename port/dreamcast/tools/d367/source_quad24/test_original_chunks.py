"""Finite public geometry and composition adversaries only; no private inputs."""
from dataclasses import replace
from fractions import Fraction as F
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import original_chunks as c
q=c.q

class Controls(unittest.TestCase):
    def panel(self, ident=1):
        pts=((-1,-1,1),(1,-1,1),(1,1,1),(-1,1,F(3,2)))
        return q.PhysicalPanel(ident,(ident,2,3,4,5,0,1,2,0,2,3),'b'*64,
                              ((pts[0],pts[1],pts[2]),(pts[0],pts[2],pts[3])))
    def assignment(self,ident=1): return q.Assignment(self.panel(ident),(0,0,-1),1)
    def eyes(self, r=F(1,100)):
        return q.EyeBox((-r,)*3,(r,)*3,'a'*64)
    def parent(self,ordinal=0,hidden=True):
        vertices=((F(-1,2),F(1,2),3),(F(1,2),F(-1,2),3),(F(1,2),F(1,2),3))
        if not hidden: vertices=tuple((x+20,y,z) for x,y,z in vertices)
        return q.Parent((99,2,3,4,0,5,ordinal),(0,1,2),'c'*64,vertices)
    def inv(self,hidden=(True,)):
        ps=tuple(self.parent(i,h) for i,h in enumerate(hidden))
        return q.Inventory(ps,'d'*64,q.inventory_digest(ps,'d'*64))
    def run_case(self,hidden=(True,),r=F(1,100),candidates=None,budget=None):
        return c.evaluate(self.inv(hidden),self.eyes(r),(self.assignment(),) if candidates is None else candidates,
                          c.Budget() if budget is None else budget)
    def positive(self,result): self.assertIs(type(result),c.Validated)
    def unknown(self,result,reason=None):
        self.assertIs(type(result),q.Unknown)
        if reason: self.assertEqual(result.reason,reason)
    def test_first_unproved_does_not_stop_complete_original_visit(self):
        b=c.Budget(); result=self.run_case((False,True,False,True),budget=b)
        self.positive(result);self.assertEqual(b.candidates,4);self.assertEqual(b.finals,2)
        self.assertEqual(tuple(p is not None for p in result.proofs),(False,True,False,True))
        self.assertEqual(result.partition.inventory.parents,self.inv((False,True,False,True)).parents)
        self.assertEqual(b.reserved,(4,512,4,512))
    def test_final_validates_each_covered_original_only_but_full_draw_partition(self):
        original=q.cover_triangle
        with patch.object(q,'cover_triangle',wraps=original) as cover:
            r=self.run_case((False,True,True))
        self.positive(r);self.assertEqual(cover.call_count,5)
        self.assertEqual([x.args[1].occurrence[-1] for x in cover.call_args_list],[0,1,2,1,2])
        self.assertEqual([p.volume_tests for p in r.proofs if p is not None],[128,128])
    def test_final_failure_cannot_leave_partially_verified_coverage(self):
        original=q.cover_triangle;calls=0
        def fail(*args):
            nonlocal calls
            calls+=1
            return q.Unknown('INJECTED_FINAL') if calls==4 else original(*args)
        with patch.object(q,'cover_triangle',side_effect=fail):
            self.unknown(self.run_case((True,True)),'FINAL_COVERED_SUBSET_FAILURE')
        self.assertEqual(calls,4)
    def test_complete_original_inventory_winding_indices_affine_and_order(self):
        inv=self.inv((False,True));p=inv.parents[1]
        variants=(inv.parents[:-1],inv.parents+(p,),tuple(reversed(inv.parents)),
                  (inv.parents[0],replace(p,indices=(0,2,1))),
                  (inv.parents[0],replace(p,affine_sha256='e'*64)),
                  (inv.parents[0],replace(p,vertices=tuple(reversed(p.vertices)))))
        for ps in variants:
            with self.subTest(ps=ps),patch.object(q,'cover_triangle',side_effect=AssertionError('early predicate')):
                self.unknown(c.evaluate(replace(inv,parents=ps),self.eyes(),(self.assignment(),),c.Budget()))
    def test_missing_duplicate_overlap_or_silent_unknown_draw_refused(self):
        r=self.run_case((False,True));p=r.partition
        variants=(replace(p,assignments=p.assignments[:-1]),replace(p,reasons=p.reasons[:-1]),
                  replace(p,reasons=(None,None)),replace(p,reasons=(p.reasons[0],'also drawn')),
                  replace(p,assignments=(p.assignments[1],p.assignments[1])))
        for x in variants:
            b=c.Budget();b.reserve(2,1);self.unknown(c.validate(x,b))
    def test_no_candidates_or_degenerate_originals_stay_explicitly_drawn(self):
        r=self.run_case((True,False),candidates=())
        self.positive(r);self.assertEqual(r.proofs,(None,None));self.assertEqual(r.dependencies,())
        inv=self.inv();p=inv.parents[0];p=replace(p,vertices=(p.vertices[0],)*3)
        inv=q.Inventory((p,),inv.source_binding_sha256,q.inventory_digest((p,),inv.source_binding_sha256))
        self.unknown(c.evaluate(inv,self.eyes(),(self.assignment(),),c.Budget()))
        self.unknown(c.evaluate(self.inv(),None,(),c.Budget()))
    def test_cell_global16_not_per_original_and_aliases(self):
        inv=self.inv((True,)*17);assignments=tuple(self.assignment(i+1) for i in range(17))
        p=c.Partition(inv,self.eyes(),assignments,(None,)*17);b=c.Budget();b.reserve(17,17)
        self.unknown(c.validate(p,b),'GLOBAL_CELL_FULL_PANEL_LIMIT');self.assertEqual(b.finals,0)
        a=self.assignment();alias=replace(a,panel=replace(a.panel,source_binding_sha256='f'*64))
        with patch.object(q,'cover_triangle',side_effect=AssertionError('alias reached predicate')):
            self.unknown(c.evaluate(self.inv(),self.eyes(),(a,alias),c.Budget()),'CANDIDATE_PANEL_ALIAS')
        alias=replace(a,panel=replace(a.panel,identifier=2))
        self.unknown(c.evaluate(self.inv(),self.eyes(),(a,alias),c.Budget()),'CANDIDATE_PANEL_ALIAS')
    def test_multiple_let_cell_union_uses_identical_domain_no_double_count(self):
        results=[]
        for i in range(17):
            inv=self.inv();p=replace(inv.parents[0],occurrence=(100+i,2,3,4,0,5,0))
            inv=q.Inventory((p,),inv.source_binding_sha256,q.inventory_digest((p,),inv.source_binding_sha256))
            results.append(c.evaluate(inv,self.eyes(),(self.assignment(i+1),),c.Budget()))
        self.assertEqual(c.cell_dependencies(tuple(results[:16])),tuple(range(1,17)))
        self.unknown(c.cell_dependencies(tuple(results)),'GLOBAL_CELL_FULL_PANEL_LIMIT')
        self.unknown(c.cell_dependencies((results[0],results[0])),'DUPLICATE_PHYSICAL_PARENT')
        self.unknown(c.cell_dependencies((results[0],replace(results[1],partition=replace(results[1].partition,eyes=self.eyes(F(1,200)))))))
    def test_three_cell_signature_partition_retains_originals_and_material_scope(self):
        inv=self.inv((False,True,True));results=tuple(c.evaluate(inv,self.eyes(r),(self.assignment(),),c.Budget()) for r in (F(1,100),F(1,200),F(1,300)))
        gs=c.groups(results,'e'*64);self.assertEqual([(g.mask,g.ordinals) for g in gs],[(0,(0,)),(7,(1,2))])
        self.assertEqual(tuple(p for g in gs for p in g.parents),inv.parents)
        self.unknown(c.groups(results,''),'EXPLICIT_MATERIAL_SCOPE_REQUIRED')
        self.unknown(c.groups(results[:2],'e'*64),'THREE_COMPLETE_PARTITIONS')
        self.unknown(c.groups((results[0],)*3,'e'*64),'THREE_DISTINCT_CELL_DOMAINS')
        other=self.run_case((True,));self.unknown(c.groups((results[0],results[1],other),'e'*64))
    def test_stale_or_forged_metadata_cannot_change_group_signature(self):
        results=tuple(self.run_case((False,True),r) for r in (F(1,100),F(1,200),F(1,300)))
        r=results[0];proof=r.proofs[1]
        mutations=(replace(r,proofs=(proof,proof)),replace(r,proofs=(None,replace(proof,input_sha256='0'*64))),
                   replace(r,dependencies=()),replace(r,runtime_admitted=True),
                   replace(r,partition=replace(r.partition,assignments=(None,None))))
        for bad in mutations: self.unknown(c.groups((bad,results[1],results[2]),'e'*64))
    def test_new_whole_work_caps_atomic_and_persistent_before_first_call(self):
        b=c.Budget((1,128,1,128));self.positive(self.run_case(budget=b))
        with patch.object(q,'cover_triangle',side_effect=AssertionError('overbudget called')):
            self.unknown(self.run_case(budget=b),'WHOLE_CASE_BUDGET')
        self.assertEqual(b.reserved,(1,128,1,128));self.assertEqual(b.candidates,1)
        for caps in ((-1,0,0,0),(1.0,128,1,128),(True,128,1,128),(116089,14859264,2667,341376)):
            with self.assertRaises(c.Refuse): c.Budget(caps)
    def test_memory_overflow_and_budget_refusals_are_unknown_no_partial_result(self):
        for error in (MemoryError,OverflowError):
            with patch.object(q,'cover_triangle',side_effect=error):self.unknown(self.run_case(),'MEMORY_ALLOCATION')
        with patch.object(q,'cover_triangle',return_value=q.Unknown('MEMORY_ALLOCATION')):
            self.unknown(self.run_case(),'MEMORY_ALLOCATION')
        b=c.Budget();b.reserve(1,1);b.candidates=1
        with self.assertRaises(c.Refuse): b.candidate()
        b.finals=1
        with self.assertRaises(c.Refuse): b.final()
    def test_declared_list_cost_not_original_strip_or_performance(self):
        results=tuple(self.run_case((False,True),r) for r in (F(1,100),F(1,200),F(1,300)))
        gs=c.groups(results,'e'*64);cost=c.explicit_triangle_list_cost(gs,2,16)
        self.assertEqual(cost['corner_records'],6);self.assertEqual(cost['known_subtotal_bytes'],44)
        self.assertIsNone(cost['actual_strip_delta_bytes']);self.assertIsNone(cost['modelled_ms'])
        for index,header in ((0,16),(True,16),(2,-1),(2,1.5)):
            self.unknown(c.explicit_triangle_list_cost(gs,index,header))
    def test_partial_three_cell_signature_retains_explicit_unproved_draw_bit(self):
        results=tuple(self.run_case((False,True),r) for r in (F(1,100),F(1),F(1,200)))
        gs=c.groups(results,'e'*64)
        self.assertEqual([(g.mask,g.ordinals) for g in gs],[(0,(0,)),(5,(1,))])
        bad=(gs[0],replace(gs[1],ordinals=(0,)))
        self.unknown(c.explicit_triangle_list_cost(bad,1,0))
    def test_direct_generic_source_bootstrap_ignores_poisoned_cache_and_refuses_drift(self):
        import tempfile,py_compile,subprocess,hashlib,os
        with tempfile.TemporaryDirectory() as directory:
            d=Path(directory);src=Path(c.__file__)
            generic=src.with_name('source_quad.py').read_bytes()
            d.joinpath(src.name).write_bytes(src.read_bytes())
            g=d/'source_quad.py';g.write_text("raise RuntimeError('UNCHECKED_CACHE_SENTINEL')\n")
            py_compile.compile(str(g),invalidation_mode=py_compile.PycInvalidationMode.UNCHECKED_HASH,doraise=True)
            g.write_bytes(generic)
            cache=next((d/'__pycache__').iterdir());cached=cache.read_bytes()
            env=dict(os.environ,PYTHONPATH=str(d),PYTHONDONTWRITEBYTECODE='1')
            old=subprocess.run([sys.executable,'-B','-c','import source_quad'],cwd=d,env=env,capture_output=True)
            self.assertNotEqual(old.returncode,0);self.assertIn(b'UNCHECKED_CACHE_SENTINEL',old.stderr)
            new=subprocess.run([sys.executable,'-B','-c','import original_chunks'],cwd=d,env=env,capture_output=True)
            self.assertEqual(new.returncode,0,new.stderr.decode())
            g.write_bytes(generic+b'\n# drift\n')
            drift=subprocess.run([sys.executable,'-B','-c','import original_chunks'],cwd=d,env=env,capture_output=True)
            self.assertNotEqual(drift.returncode,0);self.assertIn(b'FROZEN_GENERIC_SOURCE',drift.stderr)
            self.assertEqual(cache.read_bytes(),cached)
    def test_final_fixed_full_panel_does_not_switch_sources_within_original(self):
        inv=self.inv((True,True));a=self.assignment();b=c.Budget();r=self.run_case((True,True),budget=b)
        self.positive(r);self.assertEqual(r.partition.assignments,(a,a))
        for proof in r.proofs:self.assertEqual(proof.panel,a.panel.identifier)
        self.assertFalse(r.runtime_admitted)
        with self.assertRaises(TypeError):bool(r)

if __name__=='__main__': unittest.main()
