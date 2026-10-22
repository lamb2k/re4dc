import unittest
import numpy as np
from pvs_prove import triangle_hides,corners,quad_hides

class ProofTests(unittest.TestCase):
    def setUp(self):
        self.tri=np.array([[-20000.,-20000.,0.],[20000.,-20000.,0.],[0.,20000.,0.]])
        self.e0=np.array([-100.,-100.,4000.]);self.e1=np.array([100.,100.,4100.])
        self.t0=np.array([-100.,-100.,-4100.]);self.t1=np.array([100.,100.,-4000.])
    def hide(self,**kw):return triangle_hides(self.tri,self.e0,self.e1,self.t0,self.t1,**kw)
    def test_full_volume_proof(self):self.assertTrue(self.hide())
    def test_reverse_winding_retained(self):
        self.tri=self.tri[::-1];self.assertFalse(self.hide());self.assertTrue(self.hide(front_sign=-1))
    def test_two_sided(self):
        self.tri=self.tri[::-1];self.assertTrue(self.hide(two_sided=True))
    def test_behind_eye_retained(self):
        self.t0[2]=5000;self.t1[2]=5100;self.assertFalse(self.hide())
    def test_narrow_opening_retained(self):
        self.tri[:,0]+=20000;self.assertFalse(self.hide())
    def test_near_plane_retained(self):
        self.e0[2]=100;self.e1[2]=200;self.assertFalse(self.hide())
    def test_boundary_retained(self):
        self.t0=self.t1=np.array([0.,40000.,-4000.]);self.assertFalse(self.hide())
    def test_vertex_uncertainty_retained(self):self.assertFalse(self.hide(vertex_error=10000.))
    def test_nan_retained(self):self.tri[0,0]=np.nan;self.assertFalse(self.hide())
    def test_degenerate_retained(self):self.tri[:]=0;self.assertFalse(self.hide())
    def test_endpoint_cancellation(self):
        pts=corners(np.array([-1e16,-1e16,-1e16]),np.ones(3))
        self.assertTrue(np.array_equal(pts.max(0),np.ones(3)))
    def test_clearance_bound(self):self.assertFalse(self.hide(clearance=5000.))
    def test_interior_eyes_targets(self):
        self.assertTrue(self.hide())
        # Regression corroboration only: the interval proof is the gate.
        rng=np.random.default_rng(23)
        for _ in range(100):
            e=rng.uniform(self.e0,self.e1);t=rng.uniform(self.t0,self.t1)
            hit=e+(t-e)*(e[2]/(e[2]-t[2]))
            self.assertGreater(hit[1],-20000)
            self.assertLess(abs(hit[0]),(20000-hit[1])/2)

class QuadTests(unittest.TestCase):
    def setUp(self):
        self.q=np.array([[-20000.,-20000.,0.],[20000.,-20000.,0.],[20000.,20000.,0.],[-20000.,20000.,0.]])
        self.tris=self.q[[[0,1,2],[0,2,3]]].copy()
    def hide(self,**kw):return quad_hides(self.tris,self.q,[-100.,-100.,4000.],[100.,100.,4100.],[-100.,-100.,-4100.],[100.,100.,-4000.],**kw)
    def test_real_pair(self):self.assertTrue(self.hide())
    def test_reverse_winding(self):
        self.q=self.q[::-1].copy();self.tris=self.q[[[0,1,2],[0,2,3]]]
        self.assertFalse(self.hide());self.assertTrue(self.hide(two_sided=True))
    def test_broken_diagonal(self):
        self.tris[1,0,0]+=0.001;self.assertFalse(self.hide())
    def test_reversed_shared_edge(self):
        self.tris[1]=self.tris[1,::-1];self.assertFalse(self.hide())
    def test_self_crossing(self):
        self.q=self.q[[0,2,1,3]];self.assertFalse(self.hide())
    def test_nonconvex(self):
        self.q[2]=[-5000.,-5000.,0.];self.tris=self.q[[[0,1,2],[0,2,3]]]
        self.assertFalse(self.hide())
    def test_degenerate(self):self.q[:]=0;self.tris[:]=0;self.assertFalse(self.hide())
    def test_warped_actual_triangles(self):
        self.q[2,2]=10.;self.tris=self.q[[[0,1,2],[0,2,3]]];self.assertTrue(self.hide())
    def test_large_uncertainty(self):self.assertFalse(self.hide(vertex_error=10000.))
    def test_near_ambiguity(self):self.assertFalse(self.hide(clearance=5000.))

if __name__=='__main__':unittest.main()
