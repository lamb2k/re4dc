"""Source gates for the scoped rectangle fixture's byte-level mutation contract."""
from pathlib import Path
import struct,sys,unittest,zlib
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools/d367/texture_rect21'))
import scoped_candidate as scoped
import world_bindings as world

def sidecar(width=128):
 parts=struct.pack('<IIHH4B',0x12345678,0xabcdef01,width,64,2,1,1,0)+struct.pack('<IIHH4B',7,8,256,256,0,2,1,0)
 placements=bytes(range(52));body=parts+placements
 return struct.pack('<4s7I',b'R4PW',1,1,2,1,zlib.crc32(body)&0xffffffff,0,0)+body

class ScopedNativeRectangle(unittest.TestCase):
 def test_only_key_words_and_body_crc_change(self):
  before=sidecar();after,changed=scoped.rebind(before,{'12345678-abcdef01':(0x11111111,0x22222222)})
  self.assertEqual(len(changed),1);self.assertEqual(changed[0]['part'],0)
  self.assertEqual(after[40:],before[40:])
  self.assertEqual(after[:20],before[:20]);self.assertEqual(after[24:32],before[24:32])
  self.assertEqual(world.inspect_sidecar(after)[0],dict(key='11111111-22222222',width=128,height=64,render_pass=2,cull=1,texture=1,flags=0,part=0))
  bad=bytearray(after);bad[-1]^=1
  with self.assertRaises(ValueError):world.inspect_sidecar(bytes(bad))
 def test_unselected_world_is_byte_exact(self):
  original=sidecar();out,changed=scoped.rebind(original,{'00000001-00000002':(3,4)})
  self.assertEqual(out,original);self.assertFalse(changed)
 def test_corrupt_and_mismatched_source_reject(self):
  corrupt=bytearray(sidecar());corrupt[-1]^=1
  with self.assertRaises(ValueError):scoped.rebind(bytes(corrupt),{'12345678-abcdef01':(1,2)})
  with self.assertRaises(AssertionError):scoped.rebind(sidecar(width=256),{'12345678-abcdef01':(1,2)})
 def test_scoped_ids_bind_both_original_and_candidate_identity(self):
  a=scoped.scoped_key((1,2),'00'*32)
  self.assertEqual(a,scoped.scoped_key((1,2),'00'*32))
  self.assertNotEqual(a,scoped.scoped_key((2,1),'00'*32))
  self.assertNotEqual(a,scoped.scoped_key((1,2),'01'*32))

if __name__=='__main__':unittest.main()
