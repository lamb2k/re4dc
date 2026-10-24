"""Finite PUBLIC rational geometry only. No assets, scans or private predicates."""
import dataclasses
from fractions import Fraction as Q
from itertools import permutations, product
import unittest
from unittest.mock import patch
import source_quad as q

class Controls(unittest.TestCase):
    def eyes(self, low=None, high=None):
        return q.EyeBox((Q(-1,100),)*3 if low is None else low,
                        (Q(1,100),)*3 if high is None else high, 'a'*64)
    def panel(self, points=None, identifier=1):
        if points is None:
            points=((-1,-1,1),(1,-1,1),(1,1,1),(-1,1,Q(3,2)))
        return q.PhysicalPanel(identifier, (identifier,2,3,4,5,0,1,2,0,2,3), 'b'*64,
                               ((points[0],points[1],points[2]),(points[0],points[2],points[3])))
    def parent(self, vertices=None, ordinal=0):
        if vertices is None:
            vertices=((Q(-1,2),Q(1,2),3),(Q(1,2),Q(-1,2),3),(Q(1,2),Q(1,2),3))
        return q.Parent((99,2,3,4,0,5,ordinal),(0,1,2),'c'*64,vertices)
    def assignment(self, panel=None):
        return q.Assignment(self.panel() if panel is None else panel,(0,0,-1),1)
    def inventory(self, parents=None):
        parents=(self.parent(),) if parents is None else parents
        return q.Inventory(parents,'d'*64,q.inventory_digest(parents,'d'*64))
    def flat(self, z=1):
        return self.panel(((-1,-1,z),(1,-1,z),(1,1,z),(-1,1,z)))
    def point_eye(self):
        return self.eyes((0,0,0),(0,0,0))
    def test_actual_noncoplanar_union_whole_volume_eye_and_target(self):
        panel=self.panel();limits=q.Limits();normal=q._normal(panel.faces[0],limits)
        self.assertNotEqual(q._dot(normal,q._sub(panel.faces[1][2],panel.faces[0][0],limits),limits),0)
        with patch.object(q,'_volume',wraps=q._volume) as volume:
            result=q.cover_triangle(self.eyes(),self.parent(),self.assignment(panel))
        self.assertIs(type(result),q.TriangleOpportunity);self.assertEqual(result.volume_tests,128);self.assertEqual(volume.call_count,128)
        self.assertGreaterEqual(result.minimum_convex_volume,Q(197,50));self.assertGreaterEqual(result.minimum_outer_volume,Q(35,8));self.assertFalse(result.runtime_admitted)
        # At eye0 each old fixed face has a failing diagonal-side target vertex.
        s0,s1,s2=panel.faces[0];s3=panel.faces[1][2];u,v,w=self.parent().vertices
        self.assertLess(q._volume((0,0,0),s2,s0,u,limits),0)
        self.assertLess(q._volume((0,0,0),s0,s2,v,limits),0)
        self.assertEqual(q._volume((0,0,0),s0,s2,w,limits),0) # real internal seam is permitted
    def test_coplanar_special_case_and_valid_tilted_fixed_functional(self):
        for functional in ((0,0,-1),(Q(1,10),0,-1)):
            result=q.cover_triangle(self.eyes(),self.parent(),dataclasses.replace(self.assignment(self.flat()),functional=functional))
            self.assertIs(type(result),q.TriangleOpportunity)
    def test_signed_axis_permutations_and_mirrors(self):
        base_parent=self.parent();base_panel=self.panel();box=self.eyes()
        for perm in permutations(range(3)):
            parity=(-1)**sum(perm[i]>perm[j] for i in range(3) for j in range(i+1,3))
            for signs in product((-1,1),repeat=3):
                def transform(p):return tuple(signs[i]*p[perm[i]] for i in range(3))
                faces=tuple(tuple(transform(p) for p in t) for t in base_panel.faces)
                corners=tuple(transform(p) for p in q._eyes(box,q.Limits()))
                eyes=q.EyeBox(tuple(min(p[i] for p in corners) for i in range(3)),tuple(max(p[i] for p in corners) for i in range(3)),box.source_binding_sha256)
                functional=transform((0,0,-1));orientation=parity*signs[0]*signs[1]*signs[2]
                parent=dataclasses.replace(base_parent,vertices=tuple(transform(p) for p in base_parent.vertices))
                panel=dataclasses.replace(base_panel,faces=faces)
                with self.subTest(permutation=perm,signs=signs):
                    result=q.cover_triangle(eyes,parent,q.Assignment(panel,functional,orientation))
                    self.assertIs(type(result),q.TriangleOpportunity)
    def test_translation_and_rational_scale_preserve_positive(self):
        for scale in (Q(1,3),Q(2)):
            def transform(p):return tuple(scale*x+t for x,t in zip(p,(17,-23,5)))
            panel=self.panel();panel=dataclasses.replace(panel,faces=tuple(tuple(transform(p) for p in t) for t in panel.faces))
            parent=dataclasses.replace(self.parent(),vertices=tuple(transform(p) for p in self.parent().vertices))
            box=self.eyes();box=dataclasses.replace(box,low=transform(box.low),high=transform(box.high))
            self.assertIs(type(q.cover_triangle(box,parent,self.assignment(panel))),q.TriangleOpportunity)
    def test_projective_concave_bowtie_and_eye_singular_sources_refuse(self):
        examples=[((-1,-1,1),(1,-1,1),(Q(-1,4),Q(-1,4),1),(-1,1,1)),
                  ((-1,-1,1),(1,1,1),(-1,1,1),(1,-1,1)),
                  ((-1,-1,1),(1,-1,1),(2,-2,2),(-1,1,1))]
        for points in examples:
            self.assertIs(type(q.cover_triangle(self.point_eye(),self.parent(),self.assignment(self.panel(points)))),q.Unknown)
    def test_depth_before_target_is_required_even_when_every_cone_passes(self):
        panel=self.flat(3);target=self.parent(((Q(-1,10),Q(1,10),2),(Q(1,10),Q(-1,10),2),(Q(1,10),Q(1,10),2)))
        quad,definition=q._panel(panel,q.Limits())
        for i in range(4):
            self.assertGreater(q._volume((0,0,0),quad[i],quad[(i+1)%4],quad[(i+2)%4],q.Limits()),0)
            for t in target.vertices:self.assertGreater(q._volume((0,0,0),quad[i],quad[(i+1)%4],t,q.Limits()),0)
        self.assertEqual(q.cover_triangle(self.point_eye(),target,self.assignment(panel)).reason,'SOURCE_TARGET_DEPTH')
    def test_strict_depth_equalities_and_fixed_wrong_L_refuse(self):
        self.assertEqual(q.cover_triangle(self.eyes((0,0,1),(0,0,1)),self.parent(),self.assignment()).reason,'EYE_SOURCE_DEPTH')
        target=dataclasses.replace(self.parent(),vertices=tuple((x,y,Q(3,2)) for x,y,z in self.parent().vertices))
        self.assertEqual(q.cover_triangle(self.point_eye(),target,self.assignment()).reason,'SOURCE_TARGET_DEPTH')
        self.assertEqual(q.cover_triangle(self.point_eye(),self.parent(),q.Assignment(self.panel(),(0,0,1),1)).reason,'EYE_SOURCE_DEPTH')
    def test_outer_boundary_contact_refuses_but_internal_diagonal_passes(self):
        target=self.parent(((2,0,2),(0,0,2),(0,1,2)))
        self.assertEqual(q.cover_triangle(self.point_eye(),target,self.assignment(self.flat())).reason,'OUTER_CONE')
        self.assertIs(type(q.cover_triangle(self.point_eye(),self.parent(),self.assignment())),q.TriangleOpportunity)
    def test_one_missing_outer_edge_would_falsely_accept(self):
        target=self.parent(((Q(11,5),0,2),(Q(12,5),Q(1,10),2),(Q(12,5),Q(-1,10),2)))
        quad,definition=q._panel(self.flat(),q.Limits())
        for i in range(4):
            values=[q._volume((0,0,0),quad[i],quad[(i+1)%4],t,q.Limits()) for t in target.vertices]
            self.assertTrue(all(v<0 for v in values) if i==1 else all(v>0 for v in values))
        self.assertEqual(q.cover_triangle(self.point_eye(),target,self.assignment(self.flat())).reason,'OUTER_CONE')
    def test_matched_pairs_and_one_eye_cannot_replace_full_cartesian_domain(self):
        target=self.parent(((Q(-3,2),0,2),(Q(3,2),0,2),(0,Q(1,2),2)));panel=self.flat();quad,_=q._panel(panel,q.Limits())
        for eye,t in zip(((1,0,0),(-1,0,0),(0,0,0)),target.vertices):
            self.assertTrue(all(q._volume(eye,quad[i],quad[(i+1)%4],t,q.Limits())>0 for i in range(4)))
        self.assertIs(type(q.cover_triangle(self.point_eye(),target,self.assignment(panel))),q.TriangleOpportunity)
        self.assertEqual(q.cover_triangle(self.eyes((-1,0,0),(1,0,0)),target,self.assignment(panel)).reason,'OUTER_CONE')
    def test_shared_corner_realization_and_index_incidence_are_required(self):
        panel=self.panel();shifted=tuple((p[0]+Q(1,100),p[1],p[2]) for p in panel.faces[1])
        bad=[dataclasses.replace(panel,faces=(panel.faces[0],shifted)),
             dataclasses.replace(panel,faces=panel.faces[:1]),
             dataclasses.replace(panel,record=panel.record[:5]+(0,1,2,0,1,2)),
             dataclasses.replace(panel,record=panel.record[:5]+(0,1,2,0,4,3)),
             dataclasses.replace(panel,record=panel.record[:5]+(0,1,2,0,3,2),faces=(panel.faces[0],(panel.faces[1][0],panel.faces[1][2],panel.faces[1][1])))]
        for source in bad:self.assertIs(type(q.cover_triangle(self.eyes(),self.parent(),self.assignment(source))),q.Unknown)
        self.assertEqual(q.cover_triangle(self.eyes(),self.parent(),self.assignment(bad[0])).reason,'SHARED_REALIZED_CORNER')
    def test_physical_seam_gap_cannot_be_welded_into_nominal_union(self):
        d=Q(1,100);a0=(-1,-1-d,1);b=(1,-1,1);c0=(1+d,1,1);a1=(-1-d,-1,1);c1=(1,1+d,1);dd=(-1,1,1)
        panel=q.PhysicalPanel(1,(1,2,3,4,5,0,1,2,3,4,5),'b'*64,((a0,b,c0),(a1,c1,dd)))
        self.assertTrue(all(y-x<=-d for x,y,z in panel.faces[0]));self.assertTrue(all(y-x>=d for x,y,z in panel.faces[1]))
        self.assertEqual(q.cover_triangle(self.point_eye(),self.parent(),self.assignment(panel)).reason,'TWO_ADJACENT_ACTUAL_TRIANGLES')
    def test_wrong_orientation_missing_functional_and_unsupported_inputs(self):
        for assignment in (None,dataclasses.replace(self.assignment(),orientation=-1),dataclasses.replace(self.assignment(),orientation=True),
                           dataclasses.replace(self.assignment(),functional=(0,0,0)),dataclasses.replace(self.assignment(),functional=(0.0,0,-1))):
            self.assertIs(type(q.cover_triangle(self.eyes(),self.parent(),assignment)),q.Unknown)
        for eye in (None,dataclasses.replace(self.eyes(),low=(float('inf'),0,0)),dataclasses.replace(self.eyes(),low=(1,0,0),high=(0,0,0))):
            self.assertIs(type(q.cover_triangle(eye,self.parent(),self.assignment())),q.Unknown)
        self.assertIs(type(q.cover_triangle(self.eyes(),dataclasses.replace(self.parent(),vertices=list(self.parent().vertices)),self.assignment())),q.Unknown)
    def test_degenerate_originals_and_sources_are_unknown_never_omitted(self):
        for vertices in (((0,0,3),(0,0,3),(1,0,3)),((0,0,3),(1,0,3),(2,0,3))):
            self.assertEqual(q.cover_triangle(self.eyes(),self.parent(vertices),self.assignment()).reason,'DEGENERATE_PARENT')
        panel=self.panel(((0,0,1),(1,0,1),(2,0,1),(0,1,1)))
        self.assertEqual(q.cover_triangle(self.eyes(),self.parent(),self.assignment(panel)).reason,'DEGENERATE_SOURCE')
    def test_all_original_occurrences_and_complete_assignments_are_mandatory(self):
        parents=tuple(self.parent(ordinal=i) for i in range(2));inv=self.inventory(parents);assignments=(self.assignment(),)*2
        result=q.cover_assigned(inv,self.eyes(),assignments)
        self.assertIs(type(result),q.AssignedOpportunity);self.assertEqual(result.original_occurrences,tuple(p.occurrence for p in parents));self.assertEqual(len(result.triangles),2);self.assertEqual(result.dependencies,(1,));self.assertEqual(result.volume_tests,256)
        with patch.object(q,'_cover',wraps=q._cover) as call:
            self.assertEqual(q.cover_assigned(dataclasses.replace(inv,parents=parents[:1]),self.eyes(),assignments[:1]).reason,'ORIGINAL_INVENTORY_BINDING');self.assertEqual(call.call_count,0)
        for bad in (assignments[:1],assignments+(self.assignment(),),list(assignments)):
            self.assertEqual(q.cover_assigned(inv,self.eyes(),bad).reason,'COMPLETE_ORIGINAL_ASSIGNMENT')
        for bad in (parents[::-1],(parents[0],parents[0])):
            self.assertIs(type(q.cover_assigned(dataclasses.replace(inv,parents=bad),self.eyes(),assignments)),q.Unknown)
    def test_last_parent_failure_cannot_return_partial_positive(self):
        outside=((20,0,3),(21,0,3),(20,1,3));parents=(self.parent(),self.parent(outside,1));inv=self.inventory(parents)
        with patch.object(q,'_cover',wraps=q._cover) as call:result=q.cover_assigned(inv,self.eyes(),(self.assignment(),)*2)
        self.assertIs(type(result),q.Unknown);self.assertEqual(call.call_count,2);self.assertFalse(hasattr(result,'triangles'))
    def test_full_panel_limit_is_global_across_originals(self):
        for n in (16,17):
            inv=self.inventory(tuple(self.parent(ordinal=i) for i in range(n)));assignments=tuple(self.assignment(self.panel(identifier=i+1)) for i in range(n))
            with patch.object(q,'_cover',wraps=q._cover) as call:result=q.cover_assigned(inv,self.eyes(),assignments)
            if n==16:
                self.assertIs(type(result),q.AssignedOpportunity);self.assertEqual(result.dependencies,tuple(range(1,17)));self.assertEqual(len(result.physical_dependencies),16)
            else:
                self.assertEqual(result.reason,'GLOBAL_FULL_PANEL_LIMIT');self.assertEqual(call.call_count,0)
    def test_full_panel_identity_and_record_bijections(self):
        inv=self.inventory(tuple(self.parent(ordinal=i) for i in range(2)));a=self.panel();b=self.panel(identifier=2)
        bad=[dataclasses.replace(b,identifier=1),dataclasses.replace(a,identifier=2),dataclasses.replace(a,source_binding_sha256='e'*64)]
        for other in bad:
            self.assertIs(type(q.cover_assigned(inv,self.eyes(),(self.assignment(a),self.assignment(other)))),q.Unknown)
    def test_work_caps_refuse_before_first_volume(self):
        inv=self.inventory(tuple(self.parent(ordinal=i) for i in range(2)))
        with patch.object(q,'_volume',side_effect=AssertionError('no coverage work admitted')):
            self.assertEqual(q.cover_triangle(self.eyes(),self.parent(),self.assignment(),q.Limits(max_volume_tests=127)).reason,'VOLUME_WORK_BUDGET')
            self.assertEqual(q.cover_assigned(inv,self.eyes(),(self.assignment(),)*2,q.Limits(max_volume_tests=255)).reason,'VOLUME_WORK_BUDGET')
    def test_finite_bit_serialized_and_limit_inputs(self):
        self.assertEqual(q.cover_triangle(self.eyes(),self.parent(),self.assignment(),q.Limits(max_serialized_bytes=1)).reason,'MEMORY_ACCOUNTING_BUDGET')
        q._point(self.eyes().low,q.Limits(max_bits=7)) # valid inputs can still exceed intermediate cap
        self.assertEqual(q.cover_triangle(self.eyes(),self.parent(),self.assignment(),q.Limits(max_bits=7)).reason,'ARITHMETIC_BITS')
        parent=dataclasses.replace(self.parent(),vertices=((1<<257,0,3),)+self.parent().vertices[1:])
        self.assertEqual(q.cover_triangle(self.eyes(),parent,self.assignment()).reason,'ARITHMETIC_BITS')
        for limits in (None,q.Limits(max_bits=-1),q.Limits(max_parents=True),q.Limits(max_bits=257),q.Limits(max_volume_tests=32769),q.Limits(max_serialized_bytes=q.MAX_BYTES+1)):
            self.assertEqual(q.cover_triangle(self.eyes(),self.parent(),self.assignment(),limits).reason,'LIMITS')
    def test_allocation_and_overflow_refuse_at_all_public_entries(self):
        inv=self.inventory()
        for failure in (MemoryError,OverflowError):
            for function in ('_account','_volume'):
                with patch.object(q,function,side_effect=failure):
                    self.assertEqual(q.cover_triangle(self.eyes(),self.parent(),self.assignment()).reason,'MEMORY_ALLOCATION')
                    self.assertEqual(q.cover_assigned(inv,self.eyes(),(self.assignment(),)).reason,'MEMORY_ALLOCATION')
            with patch.object(q,'_account',side_effect=failure):
                self.assertEqual(q.inventory_digest((self.parent(),),'d'*64).reason,'MEMORY_ALLOCATION')
            calls=[0];real=q._cover
            def last(*args):
                calls[0]+=1
                if calls[0]==2:raise failure
                return real(*args)
            inv2=self.inventory(tuple(self.parent(ordinal=i) for i in range(2)))
            with patch.object(q,'_cover',side_effect=last):
                answer=q.cover_assigned(inv2,self.eyes(),(self.assignment(),)*2)
                self.assertEqual(answer.reason,'MEMORY_ALLOCATION');self.assertFalse(hasattr(answer,'triangles'))
    def test_results_do_not_coerce_to_runtime_visibility(self):
        for result in (q.Unknown('PUBLIC'),q.cover_triangle(self.eyes(),self.parent(),self.assignment()),q.cover_assigned(self.inventory(),self.eyes(),(self.assignment(),))):
            with self.assertRaises(TypeError):bool(result)

if __name__=='__main__':unittest.main()
