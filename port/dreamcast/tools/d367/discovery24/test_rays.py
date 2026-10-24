import unittest
from unittest.mock import patch
from rays import Scene,discover

SRC=dict(placement=1,field=1,owner=250,part=2,cluster=3,level=0,meshlet=4)
def quad(z=1000,size=1200,source=SRC):
    s=Scene();s.add_let(source,[(-size,-size,z),(size,-size,z),(size,size,z),(-size,size,z)],[(0,1,2),(0,2,3)]);s.build();return s

def ring(hole):
    s=Scene();xs=[-1200,*hole,1200];vs=[(x,y,1000) for y in xs for x in xs];ts=[]
    for y in range(3):
        for x in range(3):
            if x==1 and y==1:continue
            a=4*y+x;ts.extend([(a,a+1,a+5),(a,a+5,a+4)])
    s.add_let(SRC,vs,ts);s.build();return s

class Controls(unittest.TestCase):
    def test_positive_plane_is_only_hint(self):
        s=quad();r=discover(s,(0,0,0),((-800,-800,1990),(800,800,2010)))
        self.assertEqual((r['sample_count'],r['usable_hit_count']),(27,27));self.assertIsNone(r['certificate']);self.assertFalse(r['full_domain_coverage_proven']);self.assertFalse(r['runtime_admitted'])
        self.assertEqual(len(s.patches),1);self.assertEqual(s.patches[0]['boundary_edges'],4)
    def test_real_hole_exposes_false_corner_inference(self):
        s=ring((-100,100));r=discover(s,(0,0,0),((-800,-800,2000),(800,800,2000)))
        self.assertGreater(r['sample_miss_count'],0)
        self.assertTrue(all(s.nearest((0,0,0),(x,y,2000))['kind']=='prior_triangle_hit' for x in (-800,800) for y in (-800,800)))
    def test_all_fixed_samples_can_miss_offcentre_hole(self):
        s=ring((180,220));r=discover(s,(0,0,0),((-800,-800,1990),(800,800,2010)))
        self.assertTrue(r['all_fixed_samples_hit']);self.assertEqual(s.nearest((0,0,0),(400,400,2000))['kind'],'no_prior_hit');self.assertIsNone(r['certificate'])
        self.assertEqual(len(s.patches),1);self.assertEqual(s.patches[0]['boundary_edges'],16)
    def test_sliver_not_full(self):
        s=Scene();s.add_let(SRC,[(-2,-1000,1000),(2,-1000,1000),(0,1000,1000)],[(0,1,2)]);s.build()
        r=discover(s,(0,0,0),((-800,-800,1990),(800,800,2010)));self.assertFalse(r['all_fixed_samples_hit']);self.assertGreater(r['sample_miss_count'],0)
    def test_near_not_usable(self):
        r=discover(quad(20),(0,0,0),((-10,-10,1990),(10,10,2010)));self.assertEqual(r['usable_hit_count'],0);self.assertEqual(r['near_blocker_count'],27)
    def test_self_cluster_excludes_other_let(self):
        s=quad();s.add_let(dict(SRC,meshlet=99),[(-1200,-1200,900),(1200,-1200,900),(1200,1200,900)],[(0,1,2)]);s.nodes=[];s.order=__import__('array').array('I');s.build()
        self.assertIsNone(s.nearest((0,0,0),(0,0,2000),exclude_cluster=(1,3))['hit'])
        self.assertIsNotNone(s.nearest((0,0,0),(0,0,2000),exclude_meshlet=(1,3,4))['hit'])
    def test_behind_target_or_eye_no_hit(self):
        for z in (-100,2100):self.assertIsNone(quad(z).nearest((0,0,0),(0,0,2000))['hit'])
    def test_index_and_caps_fail_not_truncate(self):
        with self.assertRaises(ValueError):Scene().add_let(SRC,[(0,0,1)]*3,[(0,1,5)])
        with patch('rays.MAX_TRIANGLES',1):
            with self.assertRaises(ValueError):quad()
        s=quad()
        with patch('rays.MAX_RAYS',1):
            s.nearest((0,0,0),(0,0,2000))
            with self.assertRaises(ValueError):s.nearest((0,0,0),(0,0,2000))
    def test_nearest_not_farthest_and_provenance(self):
        s=quad(1000);s.add_let(dict(SRC,placement=2,meshlet=5),[(-1000,-1000,500),(1000,-1000,500),(0,1000,500)],[(0,1,2)]);s.nodes=[];s.order=__import__('array').array('I');s.build()
        h=s.nearest((0,0,0),(0,0,2000))['hit'];self.assertEqual(h['distance_mm'],500);self.assertEqual(s.provenance(h['triangle'])['placement'],2)
    def test_bvh_matches_complete_naive_nearest(self):
        import random,math
        rng=random.Random(24647);s=Scene()
        for i in range(40):
            x,y,z=(rng.uniform(-600,600),rng.uniform(-600,600),rng.uniform(200,1600))
            s.add_let(dict(SRC,placement=i+10),[(x-300,y-250,z),(x+300,y-250,z),(x,y+300,z)],[(0,1,2)])
        s.build()
        for _ in range(256):
            target=(rng.uniform(-1000,1000),rng.uniform(-1000,1000),2000);length=math.sqrt(sum(v*v for v in target));best=1-1/length;expected=None
            for i in range(len(s.patch)):
                hit=s.ray_triangle(i,(0,0,0),target)
                if hit and hit[0]<best:best=hit[0];expected=i
            got=s.nearest((0,0,0),target)['hit']
            self.assertEqual(None if got is None else got['triangle'],expected)
    def test_prefix_pass_does_not_let_nearest_late_source_hide_earlier(self):
        s=quad(1000,source=dict(SRC,placement=1));s.add_let(dict(SRC,placement=3),[(-1200,-1200,500),(1200,-1200,500),(0,1200,500)],[(0,1,2)])
        s.nodes=[];s.order=__import__('array').array('I');s.build()
        self.assertEqual(s.provenance(s.nearest((0,0,0),(0,0,2000))['hit']['triangle'])['placement'],3)
        hit=s.nearest((0,0,0),(0,0,2000),source_before=2)['hit']
        self.assertEqual(s.provenance(hit['triangle'])['placement'],1)
        self.assertIsNone(s.nearest((0,0,0),(0,0,2000),source_before=1)['hit'])
    def test_source_lod_namespace_refusals(self):
        from rank import validate_selection
        class P:clusters=[dict(first_level=0)];levels=[(0,2,0)]
        t=[dict(instance=0,placement=1,part=2,cluster=0,selectable=[0])]
        r=dict(instance=0,placement=1,part=2,cluster=0,level=0,meshlets=2)
        validate_selection(P,t,[r]);validate_selection(P,t,[dict(r,meshlets=1)])
        for bad in (dict(r,placement=3),dict(r,level=1),dict(r,meshlets=3)):
            with self.assertRaises(ValueError):validate_selection(P,t,[bad])
if __name__=='__main__':unittest.main()
