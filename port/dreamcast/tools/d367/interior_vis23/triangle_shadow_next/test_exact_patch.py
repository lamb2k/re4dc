"""Public exact connected-disk controls; no private game geometry."""
import itertools
import unittest
from fractions import Fraction as Q
from exact_patch import indexed_disk,prove_patch


def fan():
    points={0:(-20,0,0),1:(-10,-20,0),2:(10,-20,0),3:(20,0,0),4:(10,20,0),5:(-10,20,0),6:(0,0,0)}
    return points,tuple((6,i,(i+1)%6) for i in range(6))


def ring(outer,inner):
    n=len(outer);vertices={i:v for i,v in enumerate(outer+inner)};triangles=[]
    for i in range(n):
        j=(i+1)%n;triangles.extend(((i,j,n+j),(i,n+j,n+i)))
    return vertices,tuple(triangles)


class ConnectedTests(unittest.TestCase):
    eye=((-1,-1,10),(1,1,12));target=((-3,-3,-12),(3,3,-10))
    def test_six_face_solid_and_warped_positive(self):
        v,t=fan();self.assertTrue(prove_patch(v,t,self.eye,self.target)['proven'])
        v[6]=(0,0,Q(1,3));v[1]=(-10,-20,1)
        self.assertTrue(prove_patch(v,t,self.eye,self.target)['proven'])
        self.assertTrue(prove_patch(v,tuple(tuple(reversed(f)) for f in t),self.eye,self.target)['proven'])
        top=indexed_disk(t);self.assertEqual(top['euler'],1);self.assertEqual(top['vertex_links'][6],'cycle')
    def test_six_face_eight_boundary_strip_style(self):
        cycle=(8,9,11,12,14,15,13,10)
        coordinates=((-30,-10,0),(-10,-30,0),(10,-30,0),(30,-10,0),(30,10,0),(10,30,0),(-10,30,0),(-30,10,0))
        v=dict(zip(cycle,coordinates));t=((8,9,10),(11,10,9),(10,11,12),(10,12,13),(14,13,12),(13,14,15))
        self.assertTrue(prove_patch(v,t,self.eye,self.target)['proven'])
        self.assertEqual(len(indexed_disk(t)['boundary']),8)
    def test_twelve_face_annulus_hole_rejected(self):
        outer=[(-20,0,0),(-10,-20,0),(10,-20,0),(20,0,0),(10,20,0),(-10,20,0)];inner=[tuple(Q(x,4) for x in p) for p in outer]
        v,t=ring(outer,inner);self.assertEqual(len(t),12)
        self.assertFalse(prove_patch(v,t,self.eye,self.target)['proven'])
    def test_missing_reversed_duplicate_copied_and_pinched(self):
        v,t=fan()
        self.assertFalse(prove_patch(v,t[:-1],self.eye,self.target)['proven'])
        self.assertFalse(prove_patch(v,(t[0][::-1],)+t[1:],self.eye,self.target)['proven'])
        self.assertFalse(prove_patch(v,t+(t[0],),self.eye,self.target)['proven'])
        v[7]=v[6];copied=((7,0,1),)+t[1:]
        self.assertFalse(prove_patch(v,copied,self.eye,self.target)['proven'])
        # Two disks meet at one source index: pinched link/disconnected faces.
        v.update({8:(40,0,0),9:(50,10,0)});pinched=t+((6,8,9),)
        self.assertFalse(prove_patch(v,pinched,self.eye,self.target)['proven'])
        with self.assertRaises(ValueError):indexed_disk(((0,1,2),(1,0,3),(0,1,4)))
    def test_common_chart_crossing_and_concave_boundary(self):
        v,t=fan();v[3]=(20,0,13)
        result=prove_patch(v,t,self.eye,self.target);self.assertFalse(result['proven']);self.assertEqual(result['reason'],'chart_unknown')
        v,t=fan();v[3]=(3,0,0)
        result=prove_patch(v,t,self.eye,self.target);self.assertFalse(result['proven']);self.assertEqual(result['reason'],'boundary_convexity_unknown')
    def test_every_face_and_target_plane_needed(self):
        v,t=fan();v[6]=(30,0,0)
        self.assertFalse(prove_patch(v,t,self.eye,self.target)['proven'])
        v,t=fan();v[6]=(0,0,-2)
        self.assertFalse(prove_patch(v,t,((0,0,10),)*2,((0,0,-1),)*2)['proven'])
        v,t=fan();self.assertFalse(prove_patch(v,t,((-1,-1,-1),(1,1,1)),self.target)['proven'])
    def test_outer_contact_refuses_internal_seam_accepts(self):
        v,t=fan();self.assertFalse(prove_patch(v,t,((0,0,10),)*2,((30,-20,-10),)*2)['proven'])
        self.assertTrue(prove_patch(v,t,((0,0,10),)*2,((0,0,-10),)*2)['proven'])
    def test_requested_interval_and_correlated_center(self):
        v,t=fan();v={i:tuple(1000*x for x in p) for i,p in v.items()}
        self.assertTrue(prove_patch(v,t,((-100,-100,10000),(100,100,12000)),((-500,-500,-12000),(500,500,-10000)),vertex_error=32,eye_error=32,target_error=32,eye_clearance=2000,target_clearance=32)['proven'])
        v,t=fan();self.assertFalse(prove_patch(v,t,self.eye,self.target,vertex_error=32)['proven'])
        for q in (Q(-1,10),Q(1,10)):
            v[6]=(q,q,q);self.assertTrue(prove_patch(v,t,self.eye,self.target)['proven'])
        self.assertTrue(prove_patch(v,t,self.eye,self.target,vertex_error=Q(1,10))['proven'])
    def test_twentyseven_samples_can_miss_a_real_hole(self):
        outer=[(-2,-2,0),(2,-2,0),(2,2,0),(-2,2,0)];inner=[(Q(1,5),Q(1,5),0),(Q(2,5),Q(1,5),0),(Q(2,5),Q(2,5),0),(Q(1,5),Q(2,5),0)]
        v,t=ring(outer,inner)
        def covered(p):
            def edge(a,b):return (b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0])
            return any(all(edge(v[f[i]],v[f[(i+1)%3]])>=0 for i in range(3)) for f in t)
        for x,y,z in itertools.product((-1,0,1),(-1,0,1),(-11,-10,-9)):
            scale=Q(10,10-z);self.assertTrue(covered((x*scale,y*scale)))
        self.assertFalse(covered((Q(3,10),Q(3,10))))
        self.assertFalse(prove_patch(v,t,((0,0,10),)*2,((-1,-1,-11),(1,1,-9)))['proven'])

if __name__=='__main__':unittest.main()
