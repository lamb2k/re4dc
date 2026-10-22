import importlib.util,pathlib,struct,unittest
P=pathlib.Path(__file__).parent
spec=importlib.util.spec_from_file_location('planner',P/'virtual-stage-plan.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
i=__import__('sys').modules.get('iso_independent')
spec=importlib.util.spec_from_file_location('iso',P/'iso-independent.py');iso=importlib.util.module_from_spec(spec);spec.loader.exec_module(iso)
class Planner(unittest.TestCase):
 def test_virtual_splice_boundaries_and_immutable_source(self):
  source=b'abcdefghij';r=lambda p,n:source[p:p+n]
  v=m.Virtual(r,[{'offset':2,'data':b'XY'},{'offset':7,'data':b'Z'}])
  self.assertEqual(v.read(0,10),b'abXYefgZij');self.assertEqual(v.read(3,5),b'YefgZ');self.assertEqual(source,b'abcdefghij')
 def test_overlapping_patch_rejected(self):
  with self.assertRaises(ValueError):m.Virtual(None,[{'offset':2,'data':b'xxx'},{'offset':4,'data':b'xx'}])
 def test_mirrored_endian_mismatch_rejected(self):
  self.assertEqual(iso.both(struct.pack('<I',10)+struct.pack('>I',10),0),10)
  with self.assertRaises(ValueError):iso.both(struct.pack('<I',10)+struct.pack('>I',11),0)
 def test_hash_virtual_and_source_distinct(self):
  source=b'abc'*4096;v=m.Virtual(lambda p,n:source[p:p+n],[{'offset':100,'data':b'xyz'}])
  self.assertNotEqual(m.digest_range(v.read,0,len(source)),m.hashlib.sha256(source).hexdigest());self.assertEqual(m.digest_range(v.read,0,len(source)),m.hashlib.sha256(v.read(0,len(source))).hexdigest())
if __name__=='__main__':unittest.main(verbosity=2)
