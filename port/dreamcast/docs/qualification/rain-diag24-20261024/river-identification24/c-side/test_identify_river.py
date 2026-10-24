#!/usr/bin/env python3
"""Small synthetic controls for the actual read-only boundary parser; no private bytes."""
import hashlib,importlib.util,json,pathlib,struct,sys,unittest
sys.dont_write_bytecode=True
p=pathlib.Path(__file__).with_name('identify_river.py');s=importlib.util.spec_from_file_location('identify_river',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Controls(unittest.TestCase):
 def test_dat_positive(self):
  b=bytearray(32);struct.pack_into('<I',b,0,1);struct.pack_into('<I',b,16,24);b[20:24]=b'EFF\0'
  self.assertEqual(m.dat_entries(b),[(0,'EFF',24,32)])
 def test_dat_truncated(self):
  with self.assertRaises((AssertionError,struct.error)):m.dat_entries(b'\x01\0\0\0')
 def test_dat_invalid_offset(self):
  b=bytearray(32);struct.pack_into('<I',b,0,1);struct.pack_into('<I',b,16,4)
  with self.assertRaises(AssertionError):m.dat_entries(b)
 def picture(self):
  b=bytearray(240);struct.pack_into('<12I',b,0,11,48,0,0,0,0,60,0,0,0,0,0);struct.pack_into('<I',b,48,1);struct.pack_into('<H',b,52,0xfe);struct.pack_into('<2I',b,60,1,8);struct.pack_into('<3I',b,68,0x1000,1,12);struct.pack_into('<4H',b,80,2,2,8,0);struct.pack_into('<2I',b,112,60,64);b[128:130]=b'\x12\x34';return b
 def test_picture_exact_span_positive(self):
  b=self.picture();row=m.pictures(b,{0xfe})[0];self.assertEqual(row['frames'][0]['index_sha256'],hashlib.sha256(b'\x12\x34').hexdigest());self.assertEqual(row['frames'][0]['palette_span_bytes'],96)
 def test_picture_bad_count(self):
  b=self.picture();struct.pack_into('<I',b,60,2)
  with self.assertRaises(AssertionError):m.pictures(b,{0xfe})
 def test_picture_pixel_escape(self):
  b=self.picture();struct.pack_into('<I',b,112,239)
  with self.assertRaises(AssertionError):m.pictures(b,{0xfe})
 def test_picture_palette_escape(self):
  b=self.picture();struct.pack_into('<I',b,116,239)
  with self.assertRaises(AssertionError):m.pictures(b,{0xfe})
if __name__=='__main__':unittest.main()