"""Focused fake native-allocation controls; no native queries."""
import importlib.util,pathlib,types,unittest
P=pathlib.Path(__file__).parent
s=importlib.util.spec_from_file_location('allocation',P/'allocation.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class API:
 def __init__(self,logical=2332,allocated=4096,attributes=0):self.value={'size':logical,'allocated':allocated,'attributes':attributes,'deleted':False,'directory':False};self.closed=[];self.k=types.SimpleNamespace(CreateFileW=lambda *args:88)
 def stat(self,h):return self.value
 def close(self,h):self.closed.append(h)
class Tests(unittest.TestCase):
 def test_allocated_cluster_exceeds_logical(self):
  api=API();self.assertEqual(m.file_charge(api,'C:/owned/file.json'),4096);self.assertEqual(api.closed,[88])
 def test_resident_or_compressed_allocation_cannot_discount_logical(self):
  api=API(399,400);self.assertEqual(m.file_charge(api,'C:/owned/file.json'),400)
  api=API(1000,256);self.assertEqual(m.file_charge(api,'C:/owned/file.json'),1000)
 def test_reparse_refusal_still_closes_owned_attributehandle(self):
  api=API(attributes=0x400)
  with self.assertRaises(RuntimeError):m.file_charge(api,'C:/owned/file.json')
  self.assertEqual(api.closed,[88])
if __name__=='__main__':unittest.main()
