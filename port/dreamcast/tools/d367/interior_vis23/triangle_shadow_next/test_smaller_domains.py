import struct
import unittest
from fractions import Fraction as Q
from smaller_domains import eye_from_bits,window

def bits(x):return '%08x'%struct.unpack('<I',struct.pack('<f',x))[0]

class DomainTests(unittest.TestCase):
 def test_exact_inverse_and_full_height(self):
  values=(1,0,0,-100,0,1,0,-200,0,0,1,300)
  eye=eye_from_bits([bits(v) for v in values]);self.assertEqual(eye,(100,200,-300))
  old=((0,50,-1000),(2000,650,1000))
  for size in (500,250):
   box=window(eye,old,size);self.assertEqual((box[0][1],box[1][1]),(50,650))
   self.assertEqual(box[1][0]-box[0][0],size);self.assertEqual(box[1][2]-box[0][2],size)
 def test_serialized_origin_and_fail_open(self):
  eye=(Q(1,3),Q(100),Q(2,3));old=((-2000,0,-2000),(2000,600,2000));box=window(eye,old,500)
  self.assertLess(box[0][0],eye[0]);self.assertGreater(box[1][2],eye[2])
  with self.assertRaises(ValueError):window(eye,old,100)
  with self.assertRaises(ValueError):window((0,1000,0),old,250)
  with self.assertRaises(ValueError):eye_from_bits([bits(0)]*12)

if __name__=='__main__':unittest.main()
