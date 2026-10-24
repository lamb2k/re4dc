"""Synthetic exact-rational controls; no scene/assets/ray queries."""
from fractions import Fraction as F
from itertools import permutations,product
import importlib.util,os,pathlib,resource,subprocess,sys,tempfile,unittest
HERE=pathlib.Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('shadow_under_test',os.environ.get('TRIANGLE_SHADOW_HELPER',str(HERE/'exact_shadow.py')))
es=importlib.util.module_from_spec(spec);sys.modules[spec.name]=es;spec.loader.exec_module(es)
S=((-1,-1,0),(1,-1,0),(0,1,0));E=((0,0,1),)
T=((F(-8,5),F(-8,5),-1),(F(8,5),F(-8,5),-1),(0,F(8,5),-1))

def gaussian_intersection(s,e,t):
    """Independent exact solve: A+u(B-A)+v(C-A)=E+tau(T-E)."""
    a,b,c=s
    m=[[F(b[k])-a[k],F(c[k])-a[k],F(e[k])-t[k],F(e[k])-a[k]] for k in range(3)]
    for col in range(3):
        pivot=next((i for i in range(col,3) if m[i][col]),None)
        if pivot is None:return None
        m[col],m[pivot]=m[pivot],m[col];scale=m[col][col]
        m[col]=[x/scale for x in m[col]]
        for row in range(3):
            if row!=col:
                factor=m[row][col];m[row]=[m[row][k]-factor*m[col][k] for k in range(4)]
    u,v,tau=(m[i][3] for i in range(3))
    return (1-u-v,u,v),tau

def inside(s,e,t):
    q=gaussian_intersection(s,e,t)
    return q is not None and min(q[0])>0 and 0<q[1]<1

def blend(points,weights):return tuple(sum((F(w)*p[k] for p,w in zip(points,weights)),F(0)) for k in range(3))
def det3(rows):
    total=F(0)
    for p in permutations(range(3)):
        inv=sum(p[i]>p[j] for i in range(3) for j in range(i+1,3))
        total+=(-1 if inv&1 else 1)*rows[0][p[0]]*rows[1][p[1]]*rows[2][p[2]]
    return total

def H(u,v,e,t):return det3(tuple(tuple(F(p[k])-u[k] for k in range(3)) for p in (e,v,t)))
def panel(i,s=S):return es.Panel(i,(s,(s[0],s[2],s[1])))

class Controls(unittest.TestCase):
    def yes(self,x):self.assertIsInstance(x,es.TriangleProof);return x
    def unknown(self,x,reason=None):
        self.assertIsInstance(x,es.Unknown)
        if reason:self.assertEqual(x.reason,reason)
    def test_actual_triangle_not_aabb_geometry(self):
        self.yes(es.cover_triangle(E,S,T))
        self.assertTrue(all(inside(S,E[0],t) for t in T))
        self.assertFalse(inside(S,E[0],(F(8,5),F(8,5),-1)))
        self.unknown(es.cover_triangle(E,S,tuple(product((F(-8,5),F(8,5)),(F(-8,5),F(8,5)),(-1,)))),'TRIANGLE_ARITY')
    def test_full_eye_volume_and_independent_oracle(self):
        eyes=es.eye_box((F(-1,16),F(-1,16),1),(F(1,16),F(1,16),2))
        large=((-4,-4,0),(4,-4,0),(0,4,0));proof=self.yes(es.cover_triangle(eyes,large,T));self.assertEqual(proof.cartesian_pairs,24)
        # Exact rational interior samples and an independent linear-system solve.
        for ew in [(F(1,8),)*8,(F(1,4),F(1,4),F(1,4),F(1,4),0,0,0,0)]:
            e=blend(eyes,ew)
            for tw in [(F(1,3),)*3,(F(1,2),F(1,4),F(1,4)),(0,F(2,3),F(1,3))]:
                t=blend(T,tw);weights,tau=gaussian_intersection(large,e,t)
                self.assertGreater(min(weights),0);self.assertTrue(0<tau<1)
                for edge in range(3):
                    u,v=large[edge],large[(edge+1)%3]
                    corner=sum((ew[i]*tw[j]*H(u,v,ee,tt) for i,ee in enumerate(eyes) for j,tt in enumerate(T)),F(0))
                    self.assertEqual(H(u,v,e,t),corner)
    def test_pointwise_grid_against_independent_linear_solve(self):
        # 2025 wholly synthetic rational cases, including source-plane/depth
        # contacts and eyes on either side; no scene ray query is performed.
        count=0
        for e in product((-1,0,1),(-1,0,1),(-1,0,1)):
            for t in product((-3,-1,0,1,3),(-3,-1,0,1,3),(-1,0,1)):
                got=isinstance(es.cover_triangle((e,),S,(t,)*3),es.TriangleProof)
                self.assertEqual(got,inside(S,e,t),(e,t));count+=1
        self.assertEqual(count,2025)
    def test_orientation_and_affine_controls(self):
        self.assertEqual(self.yes(es.cover_triangle(E,S,T)).sign,1)
        rev=(S[0],S[2],S[1]);self.assertEqual(self.yes(es.cover_triangle(E,rev,T)).sign,-1)
        f=lambda p:(F(-3,2)*p[0]+7,F(2,3)*p[1]-5,F(5,7)*p[2]+2)
        self.yes(es.cover_triangle(tuple(map(f,E)),tuple(map(f,S)),tuple(map(f,T))))
    def test_source_degenerate_and_target_dimension(self):
        self.unknown(es.cover_triangle(E,((0,0,0),(1,0,0),(2,0,0)),T),'DEGENERATE_SOURCE')
        self.yes(es.cover_triangle(E,S,((0,0,-1),)*3))
        self.yes(es.cover_triangle(E,S,((F(-1,10),0,-1),(0,0,-1),(F(1,10),0,-1))))
    def test_depth_plane_and_mixed_eye_refusal(self):
        for t in [((0,0,F(1,2)),)*3,((0,0,0),)*3,(T[0],T[1],(0,0,1))]:self.unknown(es.cover_triangle(E,S,t),'TARGET_DEPTH')
        self.unknown(es.cover_triangle(((0,0,0),),S,T),'EYE_PLANE')
        self.unknown(es.cover_triangle(((0,0,1),(0,0,F(-1,2))),S,((0,0,-1),)*3),'EYE_SIDE')
    def test_edge_contact_outside_and_boundary_depth(self):
        self.unknown(es.cover_triangle(E,S,((-2,-2,-1),)*3),'EDGE_VOLUME')
        tiny=F(1,1<<200);self.yes(es.cover_triangle(E,S,((0,0,-tiny),)*3))
        eps=F(1,1<<32);self.yes(es.cover_triangle(E,S,((0,-2+eps,-1),)*3))
        self.unknown(es.cover_triangle(E,S,((0,-2-eps,-1),)*3),'EDGE_VOLUME')
        self.unknown(es.cover_triangle(E,S,(T[0],T[1],(0,3,-1))),'EDGE_VOLUME')
        self.unknown(es.cover_triangle(E,S,((-3,0,-1),)*3),'EDGE_VOLUME')
    def test_no_per_vertex_or_per_eye_source_switch(self):
        patches=[]
        for t in T:
            x,y=F(t[0])/2,F(t[1])/2;r=F(1,20);patches.append(((x-r,y-r,0),(x+r,y-r,0),(x,y+r,0)))
        for p,t in zip(patches,T):self.yes(es.cover_triangle(E,p,(t,)*3));self.unknown(es.cover_triangle(E,p,T))
        center=blend(T,(F(1,3),)*3);self.assertTrue(all(not inside(p,E[0],center) for p in patches))
        eyes=((-1,0,1),(1,0,1));p=((F(-11,20),F(-1,20),0),(F(-9,20),F(-1,20),0),(F(-1,2),F(1,20),0));point=((0,0,-1),)*3
        self.yes(es.cover_triangle((eyes[0],),p,point));self.unknown(es.cover_triangle(eyes,p,point),'EDGE_VOLUME')
        # A source chosen for the other eye is also not an assignment for the cell.
        other=tuple((-v[0],v[1],v[2]) for v in p)
        self.yes(es.cover_triangle((eyes[1],),other,point));self.unknown(es.cover_triangle(eyes,other,point))
        self.assertFalse(inside(p,(0,0,1),point[0]));self.assertFalse(inside(other,(0,0,1),point[0]))
        self.unknown(es.cover_assigned(eyes,(point,),(es.SourceFace(panel(1,p),0),es.SourceFace(panel(2,other),0))),'ASSIGNMENT_COUNT')
    def test_cartesian_not_matched_endpoint_pairs(self):
        a,b=(0,0,0),(1,0,0);eyes=((0,-2,1),(0,2,1));targets=((0,3,-1),(0,-1,-1))
        self.assertTrue(all(H(a,b,e,t)>0 for e,t in zip(eyes,targets)))
        self.assertLess(H(a,b,eyes[0],targets[1]),0)
    def test_distinct_complete_triangles_and_and_dependencies(self):
        left=((-4,-1,0),(-2,-1,0),(-3,1,0));right=tuple((v[0]+6,v[1],v[2]) for v in left)
        tl=((F(-61,10),F(-1,10),-1),(F(-59,10),F(-1,10),-1),(-6,F(1,10),-1));tr=tuple((v[0]+12,v[1],v[2]) for v in tl)
        fixed=(es.SourceFace(panel(11,left),0),es.SourceFace(panel(22,right),0));proof=es.cover_assigned(E,(tl,tr),fixed)
        self.assertIsInstance(proof,es.AssignedProof);self.assertEqual(proof.dependencies,(11,22));self.assertEqual(len(proof.triangles),2)
        self.unknown(es.cover_assigned(E,(tl,tr),(fixed[0],fixed[0])))
        self.unknown(es.cover_assigned(E,(tl,tr),(fixed[0],)),'ASSIGNMENT_COUNT')
        self.unknown(es.cover_assigned(E,(),()),'TARGET_COUNT')
    def test_full_panel_identity_cap_and_faces(self):
        faces=tuple(es.SourceFace(panel(i//2),i%2) for i in range(32))
        proof=es.cover_assigned(E,(T,)*32,faces);self.assertIsInstance(proof,es.AssignedProof);self.assertEqual(len(proof.dependencies),16)
        self.unknown(es.cover_assigned(E,(T,)*33,faces+(es.SourceFace(panel(16),0),)),'PANEL_LIMIT')
        changed=es.Panel(0,(S,((-4,-4,0),(4,-4,0),(0,4,0))))
        self.unknown(es.cover_assigned(E,(T,T),(faces[0],es.SourceFace(changed,0))),'CONFLICTING_PANEL')
        for p in [es.Panel(-1,(S,S)),es.Panel(1<<32,(S,S)),es.Panel(True,(S,S))]:self.unknown(es.cover_assigned(E,(T,),(es.SourceFace(p,0),)),'PANEL_ID')
        self.unknown(es.cover_assigned(E,(T,),(es.SourceFace(es.Panel(1,(S,)),0),)),'PANEL_FACES')
        self.unknown(es.cover_assigned(E,(T,),(es.SourceFace(panel(1),2),)),'PANEL_FACE')
        # Conflicting unused face is still a full-Panel identity failure.
        self.unknown(es.cover_assigned(E,(T,T),(faces[0],es.SourceFace(es.Panel(0,(S,S)),0))),'CONFLICTING_PANEL')
    def test_input_bounds_nonfinite_and_work_budget(self):
        self.unknown(es.eye_box((1,0,0),(0,1,1)),'REVERSED_BOUNDS')
        self.assertIsInstance(es.eye_box((-2,-2,1),(-1,-1,1)),tuple)
        for v in [float('nan'),float('inf'),float('-inf'),0.5,True,'1/2']:
            self.unknown(es.cover_triangle(((0,0,v),),S,T),'NON_RATIONAL')
        for v in [1<<256,F(1,1<<256)]:self.unknown(es.cover_triangle(((0,0,v),),S,T),'INPUT_BITS')
        for eyes in [(),E*65,list(E),(x for x in E)]:self.unknown(es.cover_triangle(eyes,S,T),'EYE_COUNT')
        self.yes(es.cover_triangle(E*64,S,T))
        old=es.MAX_EDGE_TESTS
        try:
            es.MAX_EDGE_TESTS=9
            self.assertIsInstance(es.cover_assigned(E,(T,),(es.SourceFace(panel(1),0),)),es.AssignedProof)
            self.unknown(es.cover_assigned(E,(T,T),(es.SourceFace(panel(1),0),)*2),'WORK_LIMIT')
        finally:es.MAX_EDGE_TESTS=old
        self.unknown(es.cover_assigned(E,(T,)*1025,(es.SourceFace(panel(1),0),)*1025),'TARGET_COUNT')
        with self.assertRaises(TypeError):bool(es.Unknown('x'))
    def test_semantic_mutants(self):
        original=(HERE/'exact_shadow.py').read_text()
        mutants=[
          ('target_vertex_omission',[('for t in target:\n','for t in target[:1]:\n')],'test_edge_contact_outside_and_boundary_depth'),
          ('eye_vertex_omission',[('for e in eyes:\n','for e in eyes[:1]:\n')],'test_no_per_vertex_or_per_eye_source_switch'),
          ('third_edge_omission',[('for i in range(3):\n        u, v','for i in range(2):\n        u, v')],'test_edge_contact_outside_and_boundary_depth'),
          ('edge_touch',[('if h <= 0:','if h < 0:')],'test_edge_contact_outside_and_boundary_depth'),
          ('depth_touch',[('if any(sign*d >= 0 for d in dt):','if any(sign*d > 0 for d in dt):')],'test_depth_plane_and_mixed_eye_refusal'),
          ('mixed_eye_side',[('if any(sign*d <= 0 for d in de):','if False:')],'test_depth_plane_and_mixed_eye_refusal'),
          ('panel_cap32',[('MAX_PANELS = 16','MAX_PANELS = 32')],'test_full_panel_identity_cap_and_faces'),
          ('panel_alias',[('if identifier in panels and panels[identifier] != faces:','if False:')],'test_full_panel_identity_cap_and_faces'),
          ('zip_truncation',[('if len(targets) != len(sources):','if len(targets) < len(sources):'),('for i in range(len(targets)):','for i in range(min(len(targets),len(sources))):')],'test_distinct_complete_triangles_and_and_dependencies'),
          ('work_limit',[('if len(targets)*len(eyes)*9 > MAX_EDGE_TESTS:','if False:')],'test_input_bounds_nonfinite_and_work_budget')]
        with tempfile.TemporaryDirectory(prefix='triangle-shadow24-',dir='/dev/shm') as td:
            for name,replacements,method in mutants:
                with self.subTest(mutant=name):
                    code=original
                    for a,b in replacements:self.assertIn(a,code);code=code.replace(a,b)
                    path=pathlib.Path(td)/(name+'.py');path.write_text(code)
                    r=subprocess.run([sys.executable,'-B',str(HERE/'test_exact_shadow.py'),'Controls.'+method],env={**os.environ,'TRIANGLE_SHADOW_HELPER':str(path),'PYTHONDONTWRITEBYTECODE':'1'},capture_output=True,text=True,timeout=30)
                    self.assertEqual(r.returncode,1,r.stderr);self.assertIn('AssertionError',r.stderr);self.assertIn('FAILED (failures=',r.stderr)

if __name__=='__main__':
    resource.setrlimit(resource.RLIMIT_AS,(268435456,268435456))
    unittest.main()
