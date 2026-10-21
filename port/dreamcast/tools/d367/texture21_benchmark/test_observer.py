import copy,struct,unittest
from observer import Typed,Invalid,ram_range,vram_pointer

class ObserverTests(unittest.TestCase):
 def setUp(self):
  self.raw=bytearray(0x1000000);self.sy={};self.next=0x8c010000
  def add(n,size=4):
   a=self.next;self.next+=16;self.sy[n]={'address':a,'size':size};return a
  self.add=add
  for n in ('frame','direct_open','model_handle','model_used','model_pending','model_packets','m_tot_reads','m_tot_bytes','m_tot_block'):add('__ZN12_GLOBAL__N_1L'+str(len(n))+n+'E')
  for n in ('_pG','_pPL','_CamCtrl'):add(n)
  self.sy['native_ui_entries']={'address':0x8c020000,'size':100352}
  self.plan={'selected':[{'original_key':'00000001-00000002','scoped_key':'00000003-00000004','candidate_crc32':7,'physical':[64,64]}],'read_only_observer':{'symbols':self.sy,'typed_layouts':{'native_ui':{'types':{'Package':{'members':{}}}},'scene':{'types':{'GlobalWork':{'members':{'Frame_cnt':0,'room_id':4,'pl_life':8}},'Camera':{'members':{'param':0,'mat':32,'v_mat':80,'ProjMat':128}},'CameraControl':{'members':{'camera':0}}}},'player':{'types':{'cCoord':{'members':{'pos':0,'ang':12}}}}}}}
  self.typed=Typed(self.read,self.plan)
 def put(self,a,b):o=ram_range(a,len(b));self.raw[o:o+len(b)]=b
 def read(self,a,n):o=ram_range(a,n);return bytes(self.raw[o:o+n])
 def local(self,n,v):self.put(self.typed.sym('__ZN12_GLOBAL__N_1L'+str(len(n))+n+'E'),struct.pack('<I',v))
 def test_invalid_start_waits_no_death(self):
  with self.assertRaises(Invalid):self.typed.scene()
 def test_bounds_and_aliases(self):
  for a in (0,0x8bffffff,0x8cfffffe):
   with self.assertRaises(Invalid):ram_range(a,4)
  self.assertTrue(vram_pointer(0xa4001000));self.assertFalse(vram_pointer(0x8c001000));self.assertFalse(vram_pointer(0xa4800000))
 def test_byte_direct_latch_does_not_read_neighbor(self):
  self.local('direct_open',0xffffff00);self.assertEqual(self.typed.local('direct_open'),0);self.assertIsNone(self.typed.witness())
 def witness_setup(self):
  e=0x8c020000;p=0x8c040000
  for n,v in [('frame',12),('direct_open',1),('model_handle',e),('model_used',0),('model_pending',1),('model_packets',p)]:self.local(n,v)
  self.put(e+64,struct.pack('<II',3,4));self.put(e+72,struct.pack('<I',12));self.put(p,struct.pack('<8I',0,0,27,0xc0000000,0,0,0,0))
 def test_minimum_stable_header_only(self):
  self.witness_setup();r=self.typed.witness();self.assertTrue(r['physical_64_square']);self.assertTrue(r['vq']);self.assertTrue(r['mipmap']);self.assertIn('no total/vertex/raster',r['scope'])
 def test_reject_bad_packet_range_and_torn_tuple(self):
  self.witness_setup();self.local('model_pending',385)
  with self.assertRaises(Invalid):self.typed.witness()
  self.local('model_pending',1);old=self.typed.local;calls=[0]
  def changed(n):
   calls[0]+=1
   return old(n)+(1 if calls[0]==7 else 0)
  self.typed.local=changed
  with self.assertRaises(Invalid):self.typed.witness()
 def test_absent_table_no_candidate_claim(self):
  r=self.typed.table();self.assertEqual(r['selected'],[]);self.assertEqual(r['valid_slots'],0);self.assertFalse(r['draw_proof']);self.assertIn('UNAVAILABLE',r['allocation_bytes'])
 def test_64bit_counter_and_torn_high(self):
  self.local('m_tot_bytes',5);a=self.typed.sym('__ZN12_GLOBAL__N_1L11m_tot_bytesE');self.put(a+4,struct.pack('<I',2));self.assertEqual(self.typed.count64('m_tot_bytes'),(2<<32)+5)
  old=self.typed.read;calls=[0]
  def changed(a,n):
   calls[0]+=1
   return struct.pack('<I',3) if calls[0]==3 else old(a,n)
  self.typed.read=changed
  with self.assertRaises(Invalid):self.typed.count64('m_tot_bytes')
if __name__=='__main__':unittest.main()
