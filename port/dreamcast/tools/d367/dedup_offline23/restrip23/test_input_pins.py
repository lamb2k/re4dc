import unittest,tempfile
from pathlib import Path
from estimate_graph import require_pin
from estimate_loaded import pin
class Pins(unittest.TestCase):
 def test_hash_and_extent_are_separate_required_inputs(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'input';p.write_bytes(b'abcd');row=pin(p);require_pin(p,row)
   p.write_bytes(b'abce')
   with self.assertRaisesRegex(ValueError,'pin mismatch'):require_pin(p,row)
   p.write_bytes(b'abcd!')
   with self.assertRaisesRegex(ValueError,'pin mismatch'):require_pin(p,row)
   p.write_bytes(b'abcd')
   with self.assertRaisesRegex(ValueError,'pin mismatch'):require_pin(p,{**row,'bytes':3})
if __name__=='__main__':unittest.main()
