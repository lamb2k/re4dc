"""Controls for the all-LOD source subset lemma; no game geometry in fixtures."""
import itertools,tempfile,unittest
from pathlib import Path
import lod_surface_audit as a
V=[(0,0,0),(8,0,0),(0,8,0),(0,0,8)]
T={a.canonical([V[i] for i in ix]) for ix in [(0,2,1),(0,1,3),(1,2,3),(2,0,3)]}
class Geometry(unittest.TestCase):
 def test_cyclic_retains_winding(self):
  t=next(iter(T));self.assertEqual(a.canonical(t[1:]+t[:1]),t);self.assertNotEqual(a.canonical(t[::-1]),t)
 def test_exact_closed_graph_never_admits(self):
  r=a.topology(T)[0];self.assertTrue(r['closed_oriented_graph_prerequisite']);self.assertFalse(r['enclosure_proven']);self.assertFalse(r['runtime_admitted']);self.assertTrue(r['fail_open'])
 def test_missing_face_stays_open(self):
  r=a.topology(list(T)[1:])[0];self.assertFalse(r['closed_oriented_graph_prerequisite']);self.assertEqual(len(r['boundary_edges']),3)
 def test_winding_conflict(self):
  ts=list(T);ts[0]=a.canonical(ts[0][::-1]);r=a.topology(ts)[0];self.assertTrue(r['winding_conflicts']);self.assertFalse(r['closed_oriented_graph_prerequisite'])
 def test_duplicate_cannot_seal(self):
  r=a.topology([*T,next(iter(T))])[0];self.assertTrue(r['nonmanifold_edges']);self.assertFalse(r['closed_oriented_graph_prerequisite'])
 def test_mixed_lod_does_not_assume_global_level(self):
  t=next(iter(T));rest=T-{t};levels=[{t},set()];keep,selected=a.invariant(levels,[1,1]);self.assertEqual(keep,set())
  self.assertTrue(a.topology(T)[0]['closed_oriented_graph_prerequisite']);self.assertFalse(a.topology(keep|rest)[0]['closed_oriented_graph_prerequisite'])
  for ca,cb in itertools.product(range(2),repeat=2):self.assertTrue(keep|rest<=levels[ca]|rest)
 def test_nonempty_finer_fallback(self):
  keep,selected=a.invariant([T,set(),set()],[1,0,0]);self.assertEqual(selected,[0]);self.assertEqual(keep,T)
 def test_authored_empty_base_stays_empty(self):
  keep,selected=a.invariant([set(),T],[0,1]);self.assertEqual(selected,[0,1]);self.assertFalse(keep)
 def test_near_seam_not_welded(self):
  ts=list(T);t=ts[0];ts[0]=a.canonical(((t[0][0]+1,*t[0][1:]),t[1],t[2]));self.assertFalse(all(r['closed_oriented_graph_prerequisite'] for r in a.topology(ts)))
 def test_tjunction_unresolved(self):
  ts=list(T);x,y,z=ts.pop(0);mid=tuple((x[k]+y[k])//2 for k in range(3));ts += [a.canonical([x,mid,z]),a.canonical([mid,y,z])];self.assertTrue(any(r['boundary_edges'] for r in a.topology(ts)))
 def test_degenerate_rejected(self):self.assertIsNone(a.canonical([(0,0,0),(1,1,1),(2,2,2)]))
 def test_missing_lod_refused(self):
  with self.assertRaises(ValueError):a.invariant([T],[1,1])
  with self.assertRaises(ValueError):a.selectable([])

if __name__=='__main__':unittest.main()
