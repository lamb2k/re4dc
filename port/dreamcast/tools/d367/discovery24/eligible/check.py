import argparse,ast,copy,json,math,os,random,sys,tempfile,unittest,resource,hashlib
from pathlib import Path
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    if os.environ.get(key)!='1':raise ValueError('Single numeric thread environment required')
resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,256*1024*1024))
from pool import EligibleScene,source_allowed
from ledger import Ledger,Token
import selection
import runtime
TOKEN=None

def src(placement=1,**changes):
    p=dict(static=True,unconditional=True,nonsingular=True,level_count=1,pass_=0,cull=2,vertex_alpha=False,material_eligible=True)
    p['pass']=p.pop('pass_');p.update(changes)
    return dict(placement=placement,field=placement,owner=254,part=2,cluster=3,level=0,meshlet=4,prerequisites=p)
def triangle(s,z=1000):return s,[(-1200,-1200,z),(1200,-1200,z),(0,1200,z)],[(0,1,2)]
def build(*sources):
    s=EligibleScene(TOKEN)
    for one in sources:s.add_source(*one)
    s.build();return s
class Controls(unittest.TestCase):
    def test_nearer_ineligible_never_masks_farther(self):
        for bad in (dict(level_count=2),dict(static=False),dict(unconditional=False),dict(nonsingular=False),{'pass':2},dict(cull=1),dict(vertex_alpha=True),dict(material_eligible=False)):
            s=build(triangle(src(1)),triangle(src(2,**bad),500));h=s.nearest((0,0,0),(0,0,2000),source_before=5)['hit']
            self.assertEqual(s.provenance(h['triangle'])['placement'],1);self.assertEqual(s.refused,1)
    def test_late_and_prefix_boundary_cannot_mask(self):
        for p in (5,6):
            s=build(triangle(src(1)),triangle(src(p),500));h=s.nearest((0,0,0),(0,0,2000),source_before=5)['hit'];self.assertEqual(s.provenance(h['triangle'])['placement'],1)
        self.assertIsNone(s.nearest((0,0,0),(0,0,2000),source_before=1)['hit'])
    def test_self_instance_and_shared_geometry_placement(self):
        s=build(triangle(src(1)),triangle(src(5),250));h=s.nearest((0,0,0),(0,0,2000),source_before=5,exclude_cluster=(5,3))['hit']
        self.assertEqual(s.provenance(h['triangle'])['placement'],1)
        # Same global meshlet/cluster under another placement stays a distinct
        # physical source. Never exclude all aliases of a target's geometry ID.
        self.assertEqual(s.provenance(h['triangle'])['meshlet'],4)
    def test_edges_and_near_remain_uncertain(self):
        s=build(triangle(src(1)));h=s.nearest((0,0,0),(0,2400,2000),source_before=2)['hit'];self.assertTrue(h['source_edge_contact'])
        near=build(triangle(src(1),20));self.assertEqual(near.nearest((0,0,0),(0,0,2000),source_before=2)['kind'],'nearest_inside_near')
    def test_bvh_brute_equivalence(self):
        rng=random.Random(20261024);s=EligibleScene(TOKEN)
        for i in range(60):
            x,y,z=rng.uniform(-800,800),rng.uniform(-800,800),rng.uniform(150,1700);source=src(i%10+1,level_count=2 if i%7==0 else 1)
            s.add_source(source,[(x-500,y-500,z),(x+500,y-500,z),(x,y+500,z)],[(0,1,2)])
        s.build()
        for _ in range(256):
            target=(rng.uniform(-1200,1200),rng.uniform(-1200,1200),2000);boundary=rng.randrange(1,12)
            a=s.nearest((0,0,0),target,source_before=boundary,exclude_cluster=(boundary,3))['hit'];b=s.brute((0,0,0),target,source_before=boundary,exclude_cluster=(boundary,3))
            self.assertEqual(None if a is None else a['triangle'],None if b is None else b[0])
    def test_source_boundary_required(self):
        s=build(triangle(src(1)))
        with self.assertRaises(ValueError):s.nearest((0,0,0),(0,0,2000))
    def test_ledger_reservation_and_failed_run_no_refund(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'ledger';l=Ledger(p);l.create();l.reserve(109999,'failed planned run')
            with self.assertRaises(ValueError):l.reserve(2,'cannot reset by rerun')
            self.assertEqual(json.loads(p.read_text())['reserved'],109999)
            bad=json.loads(p.read_text());bad['reserved']=-1;bad['runs']=[dict(reserved=-1)];p.write_text(json.dumps(bad))
            with self.assertRaises(ValueError):l.reserve(2,'negative counter cannot extend capacity')
            with self.assertRaises(FileExistsError):l.create()
        token=Token(1);token.take()
        with self.assertRaises(ValueError):token.take()
    def test_triangle_cap_refuses_not_truncates(self):
        from unittest.mock import patch
        with patch('rays.MAX_TRIANGLES',1):
            s=EligibleScene(TOKEN);s.add_source(*triangle(src(1)))
            with self.assertRaises(ValueError):s.add_source(*triangle(src(2)))
    def test_observer_integrity_and_wrong_source_refusal(self):
        raw=(Path(__file__).parent/'reference_replay.py').read_bytes();tree=selection.observed_ast(raw)
        self.assertIsInstance(tree,ast.Module)
        with self.assertRaises(ValueError):selection.observed_ast(raw.replace(b'count+=ml',b'count-=ml'))
    def test_nonoverlap_refuses_duplicate_or_alternative_lod(self):
        from run import audit_union
        row=dict(target=dict(instance=1,level=0,meshlet=4,host_corner_records=3))
        self.assertEqual(audit_union([row]),3)
        for other in (row,dict(target=dict(instance=1,level=1,meshlet=5,host_corner_records=2))):
            with self.assertRaises(ValueError):audit_union([row,other])
    def test_actual_numeric_visible_let_observer(self):
        import numpy as np
        rm,_=selection.load()
        class P:
            placements=[dict(mesh=0,affine=np.array([[1.,0,0,0],[0,1.,0,0],[0,0,1.,0]]))]
            meshes=[dict(first_part=0,part_count=1,bmin=[-10,-10,-1100],bmax=[100100,10,-900])]
            plod=[(0,1)];pmeta=[{'pass_':0}];clusters=[dict(bmin=[-10,-10,-1100],bmax=[100100,10,-900],first_level=0,level_count=1)];levels=[(0,2,0.)]
            lets=[dict(bmin=[-10,-10,-1100],bmax=[10,10,-900],vc=3),dict(bmin=[100000,-10,-1100],bmax=[100100,10,-900],vc=3)]
            def wq(self,pl):return pl['affine']
        cam=[1.,0,0,0,0,1.,0,0,0,0,1.,0,0,1.,0,1.,0,2.,100.,5000.]
        rows=rm.replay(P(),cam,5.,4.);self.assertEqual(rows[0]['selected_meshlet_ids'],[0]);self.assertEqual((rows[0]['meshlets'],rows[0]['corners']),(1,3))
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--ledger',required=True,type=Path);ap.add_argument('--out',required=True,type=Path);a=ap.parse_args();a.out.mkdir(exist_ok=False);l=Ledger(a.ledger)
    if not a.ledger.exists():l.create()
    TOKEN=l.reserve(1024,'host controls including brute/reruns');suite=unittest.defaultTestLoader.loadTestsFromTestCase(Controls)
    with (a.out/'tests.log').open('x') as f:result=unittest.TextTestRunner(stream=f,verbosity=2).run(suite)
    runtime_pin=runtime.snapshot();(a.out/'HOST-RUNTIME.json').write_text(json.dumps(runtime_pin,indent=2)+'\n')
    r=dict(status='PASS' if result.wasSuccessful() else 'FAIL',tests=result.testsRun,ray_queries_used=TOKEN.used,ray_reservation_charged=TOKEN.reserved,ledger=json.loads(a.ledger.read_text()),peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,selection_label='CURRENT_HOST_REPLAY; consistency not historical identity',runtime=runtime_pin,source_pins={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(__file__).parent.glob('*.py')})
    (a.out/'HOST-CONTROLS.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r));sys.exit(0 if result.wasSuccessful() else 1)
