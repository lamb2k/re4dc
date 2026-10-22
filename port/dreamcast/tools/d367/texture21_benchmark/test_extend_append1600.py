import unittest
from plan_append1596 import layout
from extend_append1600 import shifts
def row(n):return dict(bytes=n,sha256='synthetic')
def key(n):return'%08x-00000000'%n
class ShiftTests(unittest.TestCase):
 def test_interleaved_insertions_retain_exact_offsets_with_three_runs(self):
  parent={r['key']:r for r in layout({key(n):row(1000)for n in[1,3,5]})[2]};combined={**parent,key(2):row(3000),key(4):row(3000)};final={r['key']:r for r in layout(combined)[2]};runs=shifts(parent,final);self.assertEqual([r['delta_bytes']for r in runs],[0,4096,8192]);self.assertEqual(sum(r['members']for r in runs),3)
 def test_index_sector_expansion_is_included(self):
  parent={r['key']:r for r in layout({key(n):row(20)for n in range(128)})[2]};final={r['key']:r for r in layout({**parent,key(200):row(20)})[2]};self.assertEqual([r['delta_bytes']for r in shifts(parent,final)],[2048])
 def test_append_only_does_not_move_existing_payload(self):
  parent={r['key']:r for r in layout({key(1):row(20)})[2]};final={r['key']:r for r in layout({**parent,key(2):row(20)})[2]};self.assertEqual(shifts(parent,final)[0]['delta_bytes'],0)
if __name__=='__main__':unittest.main()
