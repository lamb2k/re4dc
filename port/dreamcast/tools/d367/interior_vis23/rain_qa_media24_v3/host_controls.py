"""Public host controls only: no stage/SDK/guest/real process API calls."""
from pathlib import Path
import copy,hashlib,json,os,struct,subprocess,sys,tempfile,types,unittest
HERE=Path(__file__).resolve().parent
for n in ['common','rain_record','process_group','future_master']:
 p=HERE/(n+'.py');m=types.ModuleType(n);m.__file__=str(p);sys.modules[n]=m;exec(compile(p.read_bytes(),str(p),'exec'),m.__dict__)
c=sys.modules['common'];rr=sys.modules['rain_record'];fm=sys.modules['future_master']
class Host(unittest.TestCase):
 def valid(self):
  v=[0]*44;v[0]=2;v[1]=1;v[2]=v[3]=7;v[9]=v[10]=v[11]=11;v[12]=0x10c010c;v[13]=8;v[14]=1|2|4|8192|16384;v[17]=v[18]=320;return v
 def blob(self,v):return struct.pack('<20I24H',*v)
 def test_valid_record(self):
  b=self.blob(self.valid());d=rr.stable(b,b);self.assertTrue(d['stable'] and d['source_join_candidate']);self.assertFalse(d['physical_cache_or_presentation_proven']);self.assertFalse(d['archive_owner_authenticated'])
 def test_changed_record(self):
  v=self.valid();a=self.blob(v);v[0]=4;self.assertFalse(rr.stable(a,self.blob(v))['stable'])
 def test_size(self):
  for n in [0,127,129]:
   with self.assertRaises(ValueError):rr.decode(bytes(n))
 def test_ABI_fault(self):
  for n in [0,2,0x80000001]:
   v=self.valid();v[1]=n;b=self.blob(v);self.assertFalse(rr.stable(b,b)['stable'])
 def test_sequence(self):
  for n in [1,0xfffffffe,0xffffffff]:
   v=self.valid();v[0]=n;b=self.blob(v);self.assertFalse(rr.stable(b,b)['stable'])
 def test_counter_terminal(self):
  for n in [0xfffe,0xffff]:
   v=self.valid();v[20]=n;b=self.blob(v);self.assertFalse(rr.stable(b,b)['stable'])
 def test_source_join_negatives(self):
  for i,n in [(2,0),(3,8),(10,12),(11,12),(12,0x10c010d),(13,9),(14,1),(18,321)]:
   v=self.valid();v[i]=n;b=self.blob(v);self.assertFalse(rr.stable(b,b)['source_join_candidate'],(i,n))
 def test_partial_zero_returns(self):
  for n in [0,17,320]:
   v=self.valid();v[18]=n;b=self.blob(v);self.assertTrue(rr.stable(b,b)['source_join_candidate'])
 def test_extents(self):
  with tempfile.TemporaryDirectory(dir='/dev/shm') as t:
   root=Path(t);self.assertEqual(fm.absolute_fresh(root/'new',root),root/'new')
   for p in [root,root/'../escaped',Path('relative')]:
    with self.assertRaises(ValueError):fm.absolute_fresh(p,root)
   (root/'old').mkdir()
   with self.assertRaises(ValueError):fm.absolute_fresh(root/'old',root)
 def test_symlinks(self):
  with tempfile.TemporaryDirectory(dir='/dev/shm') as t:
   root=Path(t);(root/'target').mkdir();(root/'link').symlink_to(root/'target',target_is_directory=True)
   with self.assertRaises(ValueError):fm.owned_bytes([root])
 def test_source_keys(self):
  for k in ['../x','/abs','a/../x','./x','a//b','']:
   with self.assertRaises(ValueError):fm.safe_key(k)
 def test_manifest(self):
  old={'a':1};new={'a':2,'b':3};self.assertEqual(fm.exact_manifest(old,new,{'a','b'},new),['a','b'])
  for actual,allow in [({'a':2},['a','b']),(new,['a']),(dict(new,c=4),['a','b'])]:
   with self.assertRaises(ValueError):fm.exact_manifest(old,actual,allow,new)
 def test_host_tool(self):
  self.assertEqual(fm.host_argv(['/usr/bin/genisoimage','a']),['/usr/bin/genisoimage','a'])
  for x in ['genisoimage','python3','/tmp/genisoimage']:
   with self.assertRaises(ValueError):fm.host_argv([x])
 def test_stage_guest_grant_missing(self):
  for scope in ['stage','guest','pair']:
   env={'PATH':'/usr/bin:/bin','HOME':'/root'}
   p=subprocess.run(['/usr/bin/python3','-I','-S','-B',str(HERE/'launch.py'),scope,'off'],env=env,capture_output=True,text=True,timeout=4)
   self.assertNotEqual(p.returncode,0);self.assertIn('Separate exact root',p.stderr)
 def test_cleanup_missing_grant_no_API(self):
  p=subprocess.run(['/usr/bin/python3','-I','-S','-B',str(HERE/'cleanup_guest.py'),'off'],env={'PATH':'/usr/bin:/bin'},capture_output=True,text=True,timeout=4)
  self.assertNotEqual(p.returncode,0);self.assertIn('Exact separate root guest',p.stderr)
 def test_original_caps_and_symbols(self):
  p=c.read(HERE/'PLAN.json');self.assertEqual(p['observation']['harness_seconds'],45);self.assertEqual(p['observation']['child_seconds'],55);self.assertEqual(p['observation']['held'],0);self.assertEqual(p['observation']['root_slots'],3);self.assertEqual(p['observation']['global_slots'],16);self.assertEqual(p['syms']['on'],'0x3ebd60 0x3fbd64 0x3fbd60');self.assertEqual(p['syms']['off'],'0x3eaf60 0x3faf64 0x3faf60')
 def test_prior_readback(self):
  p=c.read(HERE/'REUSE-OFF-READBACK.json');self.assertEqual(p['files'],1715);self.assertEqual(len(p['redirects']),6);self.assertTrue(p['no_stage_or_hardlink'])
 def test_mutant_detected(self):
  text=(HERE/'rain_record.py').read_text();text=text.replace("d['seq']&1 or d['seq']>=0xfffffffe","d['seq']>=0xfffffffe")
  m={};exec(compile(text,'review_odd_mutant.py','exec'),m);v=self.valid();v[0]=3;b=self.blob(v);self.assertTrue(m['stable'](b,b)['stable']);self.assertFalse(rr.stable(b,b)['stable'])
if __name__=='__main__':unittest.main(verbosity=2)
