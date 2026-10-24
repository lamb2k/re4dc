"""Public preparation admission controls. No private geometry or predicates."""
import ast,copy,subprocess,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import prepare_private as p
class PreparationControls(unittest.TestCase):
 def row(self):
  return dict(original_parents=2,canonical_children=8,source_faces=3,whole_case_candidate_calls_reserve=24,candidate_edge_upper_reserve=1728,whole_case_final_child_calls_reserve=8,final_edge_upper_reserve=576)
 def test_four_independent_caps_refuse_before_any_partial_reservation(self):
  row=self.row();values=p.reservation(row)
  for i in range(4):
   with self.subTest(cap=p.FIELDS[i]):
    caps=tuple(v-(j==i) for j,v in enumerate(values));b=p.Budget(caps)
    self.assertFalse(b.reserve(row));self.assertEqual(b.reserved,(0,0,0,0))
  b=p.Budget(values);self.assertTrue(b.reserve(row));self.assertEqual(b.reserved,values)
  self.assertFalse(b.reserve(row));self.assertEqual(b.reserved,values)
 def test_full_fourfold_inventory_and_reserves_cannot_be_downgraded(self):
  row=self.row()
  for field in p.FIELDS+('canonical_children',):
   mutant=dict(row);mutant[field]//=4
   with self.subTest(field=field),self.assertRaises(ValueError):p.reservation(mutant)
  for value in (-1,True,1.0):
   mutant=dict(row);mutant['source_faces']=value
   with self.assertRaises(ValueError):p.reservation(mutant)
  for caps in ((100001,7200000,10668,768096),(100000,7200001,10668,768096),(100000,7200000,10669,768096),(100000,7200000,10668,768097)):
   with self.assertRaises(ValueError):p.Budget(caps)
 def test_source_pin_check_rejects_dirty_owned_bytes(self):
  with tempfile.TemporaryDirectory(dir='/dev/shm') as temp:
   root=Path(temp);folder=root/'tools';folder.mkdir()
   def git(*args):return subprocess.check_output(['git','-C',str(root),*args],stderr=subprocess.DEVNULL).decode().strip()
   git('init');git('config','user.email','host-control@invalid');git('config','user.name','Public host control')
   for name in p.OWNED:(folder/name).write_text('public synthetic '+name)
   git('add','tools');git('commit','-m','Public synthetic tool pins');sha=git('rev-parse','HEAD')
   with patch.object(p,'__file__',str(folder/'prepare_private.py')):
    pins=p.own_sources(root,sha);self.assertEqual(set(pins),set(p.OWNED))
    (folder/'PRIVATE-PREPARATION.md').write_text('different source bytes')
    with self.assertRaisesRegex(ValueError,'differ from frozen'):p.own_sources(root,sha)
 def test_preparation_tools_have_no_scene_execution_switch_or_calls(self):
  root=Path(p.__file__).parent
  for name in ('prepare_private.py','verify_private.py','seal_private.py'):
   text=(root/name).read_text();tree=ast.parse(text)
   for node in ast.walk(tree):
    if isinstance(node,ast.Call):
     function=node.func;call=function.attr if isinstance(function,ast.Attribute) else function.id if isinstance(function,ast.Name) else ''
     self.assertNotIn(call,('cover_partition','cover_triangle','cover_assigned','frozen_oracle'))
     if call=='add_argument':self.assertNotIn('--execute',[a.value for a in node.args if isinstance(a,ast.Constant)])
if __name__=='__main__':unittest.main()
