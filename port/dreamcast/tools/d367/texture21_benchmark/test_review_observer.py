import unittest
from review_observer import assess
class ReviewObserverTests(unittest.TestCase):
 def setUp(self):
  self.selected=[{'scoped_key':'00000001-00000002','original_key':'00000003-00000004','candidate_crc32':7,'physical':[64,64]}]
  self.r={'event':'sample','source_tick':100,'table_end_source_tick':100,'pose':{'camera_param':[1.0]},'table':{'selected':[{'key':'00000001-00000002','slot':1,'admission':'sampled_valid_uploaded','package':{'upload_complete_':1},'header':{'payload_crc32':7},'texture':{'width':64,'height':64,'format':0,'flags':4,'payload':2,'data_size':3414},'pvr_sampled':0xa4001000,'pvr_allocation_base':0xa4001000,'owns_texture':1}]}}
 def test_exact_descriptor_and_known_base_only(self):
  r=assess(self.r,self.selected);self.assertTrue(r['stable_table']);self.assertEqual(len(r['selected']),1);self.assertEqual(r['selected'][0]['payload_bytes'],3414);self.assertNotIn('minimum_header_witness',r)
 def test_cross_tick_table_rejected(self):
  self.r['table_end_source_tick']=101;r=assess(self.r,self.selected);self.assertFalse(r['stable_table']);self.assertFalse(r['selected'])
 def test_torn_and_wrong_crc_rejected(self):
  self.r['table']['selected'][0]['admission']='UNKNOWN';self.assertFalse(assess(self.r,self.selected)['selected']);self.r['table']['selected'][0]['admission']='sampled_valid_uploaded';self.r['table']['selected'][0]['header']['payload_crc32']=8;self.assertFalse(assess(self.r,self.selected)['selected'])
if __name__=='__main__':unittest.main()
