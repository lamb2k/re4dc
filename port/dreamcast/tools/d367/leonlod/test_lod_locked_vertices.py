"""Actual reducer regressions: protected source faces, default behavior, bad indices."""
import json, subprocess, sys, tempfile, unittest
from pathlib import Path
TOOL=Path(__file__).with_name('lod_mesh.py')

def mesh():
    positions=[[x,y,0] for y in range(7) for x in range(7)]
    triangles=[]
    for y in range(6):
        for x in range(6):
            a=y*7+x
            for face in ((a,a+1,a+8),(a,a+8,a+7)):
                triangles.append(dict(source_info=0,corners=[dict(vertex=i,normal=[0,0,1],uv=[positions[i][0]/6,positions[i][1]/6]) for i in face]))
    return dict(schema='re4dc-approved-render-mesh-1',mesh='lock-test',positions_mm=positions,weights=[[[0,1.0]] for _ in positions],bones=[dict(id=i,parent=-1) for i in range(18)],triangles=triangles)

def faces(m):
    return [tuple((tuple(m['positions_mm'][c['vertex']]),tuple(map(tuple,m['weights'][c['vertex']])),tuple(c['normal']),tuple(c['uv'])) for c in t['corners']) for t in m['triangles']]

class VertexLocks(unittest.TestCase):
    def reduce(self, locked=None):
        td=tempfile.TemporaryDirectory();self.addCleanup(td.cleanup);p=Path(td.name);m=mesh()
        spec=dict(targets={'0':{'*':30}},keep_roles=[],allow_border=False,hard_cap_mm=1,w_bone=0)
        if locked is not None:spec['locked_vertices']=locked
        (p/'src.json').write_text(json.dumps(m));(p/'spec.json').write_text(json.dumps(spec))
        r=subprocess.run([sys.executable,str(TOOL),str(p/'src.json'),str(p/'out.json'),'--spec',str(p/'spec.json')],capture_output=True,text=True)
        return m,r,json.loads((p/'out.json').read_text()) if (p/'out.json').exists() else None
    def test_protected_faces_survive_while_other_geometry_reduces(self):
        source=mesh();protected=source['triangles'][28:32];locked=sorted({c['vertex'] for t in protected for c in t['corners']})
        original,r,reduced=self.reduce(locked);self.assertEqual(r.returncode,0,r.stderr)
        self.assertLess(len(reduced['triangles']),len(original['triangles']))
        expected=faces(dict(original,triangles=protected));actual=faces(reduced)
        self.assertTrue(all(f in actual for f in expected))
    def test_default_and_empty_locks_match(self):
        _,r,a=self.reduce();_,s,b=self.reduce([])
        self.assertEqual((r.returncode,s.returncode),(0,0));self.assertEqual(a,b)
    def test_invalid_locks_fail_closed(self):
        for locks in ([-1],[49],[True],[0.5],{}):
            with self.subTest(locks=locks):
                _,r,result=self.reduce(locks);self.assertNotEqual(r.returncode,0);self.assertIsNone(result)
if __name__=='__main__':unittest.main()