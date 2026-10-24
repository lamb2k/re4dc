"""Exact oracle and adversarial controls, independent of private assets."""
import random
import unittest
from fractions import Fraction as Q
from exact_shadow import I, corners, cross, det, dot, h, prove, sub


class ExactShadowTests(unittest.TestCase):
    tri = ((-20,-20,0),(20,-20,0),(0,20,0))
    eye = ((-1,-1,10),(1,1,12))
    target = ((-1,-1,-12),(1,1,-10))

    def test_product_and_both_orientations(self):
        for tri in (self.tri, self.tri[::-1]):
            self.assertTrue(prove(tri,self.eye,self.target)['proven'])
        self.assertEqual(prove(self.tri,self.eye,self.target)['sigma'],1)
        self.assertEqual(prove(self.tri[::-1],self.eye,self.target)['sigma'],-1)

    def test_fail_open_cases(self):
        cases = [(((40,40,-12),(50,50,-10)),'edge_unknown'),
                 (((0,0,0),(0,0,0)),'plane_unknown'),
                 (((-1,-1,20),(1,1,21)),'plane_unknown'),
                 (((-1,-1,-1),(1,1,1)),'plane_unknown')]
        for target, reason in cases:
            self.assertEqual(prove(self.tri,self.eye,target)['reason'],reason)
        self.assertFalse(prove(((0,0,0),(1,0,0),(2,0,0)),self.eye,self.target)['proven'])
        self.assertFalse(prove(self.tri,self.eye,self.target,vertex_error=20)['proven'])
        self.assertFalse(prove(self.tri,self.eye,self.target,eye_clearance=12)['proven'])
        self.assertFalse(prove(self.tri,self.eye,self.target,target_error=20)['proven'])
        self.assertFalse(prove(self.tri,((0,0,0),(0,0,2)),self.target)['proven'])

    def test_exact_edge_contact_refused(self):
        self.assertFalse(prove(self.tri,((0,-20,10),(0,-20,10)),((0,-20,-10),(0,-20,-10)))['proven'])

    def test_interval_arithmetic_contains_endpoints(self):
        rng=random.Random(367)
        for _ in range(200):
            a,b=sorted(rng.sample(range(-20,21),2));c,d=sorted(rng.sample(range(-20,21),2))
            x,y=I(a,b),I(c,d)
            for u in (a,b):
                for v in (c,d):
                    for z,w in ((x+y,u+v),(x-y,u-v),(x*y,u*v)):
                        self.assertLessEqual(z.lo,w);self.assertGreaterEqual(z.hi,w)

    def test_uncertain_source_contains_each_vertex_choice(self):
        tri=[tuple(I(x-Q(1,10),x+Q(1,10)) for x in v) for v in self.tri]
        box=prove(self.tri,self.eye,self.target,vertex_error=Q(1,10),eye_error=Q(1,10),target_error=Q(1,10))
        self.assertTrue(box['proven'])
        rng=random.Random(23)
        for _ in range(60):
            t=[tuple(x.lo if rng.randrange(2) else x.hi for x in v) for v in tri]
            self.assertTrue(prove(t,self.eye,self.target)['proven'])

    def test_bilinear_interpolation_exact(self):
        es,ts=corners(self.eye),corners(self.target)
        # Independent product interpolation, including all cross-corner pairs.
        rng=random.Random(101)
        for _ in range(60):
            we=[Q(rng.randrange(11),10) for _ in range(3)]
            wt=[Q(rng.randrange(11),10) for _ in range(3)]
            def mix(box,w):return tuple(Q(a)+(Q(b)-Q(a))*v for a,b,v in zip(*box,w))
            def weights(w):
                return [((1-w[0]) if not i&4 else w[0])*((1-w[1]) if not i&2 else w[1])*((1-w[2]) if not i&1 else w[2]) for i in range(8)]
            e,t=mix(self.eye,we),mix(self.target,wt)
            for a,b in ((self.tri[0],self.tri[1]),(self.tri[1],self.tri[2]),(self.tri[2],self.tri[0])):
                interpolated=sum(x*y*h(a,b,u,v) for x,u in zip(weights(we),es) for y,v in zip(weights(wt),ts))
                self.assertEqual(h(a,b,e,t),interpolated)
            se=dot(cross(sub(self.tri[1],self.tri[0]),sub(self.tri[2],self.tri[0])),sub(e,self.tri[0]))
            st=dot(cross(sub(self.tri[1],self.tri[0]),sub(self.tri[2],self.tri[0])),sub(t,self.tri[0]))
            lam=[h(a,b,e,t)/(se-st) for a,b in ((self.tri[0],self.tri[1]),(self.tri[1],self.tri[2]),(self.tri[2],self.tri[0]))]
            self.assertEqual(sum(lam),1)
            self.assertTrue(all(x>0 for x in lam))

    def test_no_negative_perturbation_or_invalid_box(self):
        for kwargs in (dict(vertex_error=-1),dict(eye_error=-1),dict(target_error=-1),dict(eye_clearance=-1)):
            with self.assertRaises(ValueError):prove(self.tri,self.eye,self.target,**kwargs)
        with self.assertRaises(ValueError):prove(self.tri,((1,0,0),(0,0,0)),self.target)
        with self.assertRaises(ValueError):prove(self.tri,((float('nan'),0,0),(1,1,1)),self.target)

if __name__=='__main__':unittest.main()
