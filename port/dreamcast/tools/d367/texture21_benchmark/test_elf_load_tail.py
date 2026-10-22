import unittest
from elf_load_tail import inspect
class ElfAdmissionTests(unittest.TestCase):
 def test_wrong_class_or_endian_rejected_before_tables(self):
  for magic in (b'bad',b'\x7fELF\x02\x01'+bytes(100),b'\x7fELF\x01\x02'+bytes(100)):
   with self.assertRaisesRegex(ValueError,'ELF32'):inspect(magic,100,{})
 def test_short_table_rejected(self):
  import struct
  b=bytearray(52);b[:6]=b'\x7fELF\x01\x01';struct.pack_into('<HHIIIIIHHHHHH',b,16,2,42,1,0x8c010000,100,100,0,52,32,1,40,1,0)
  with self.assertRaisesRegex(ValueError,'truncated'):inspect(bytes(b),100,{})
if __name__=='__main__':unittest.main()
