"""RAM-only synthetic controls for guarded source state; no native process or guest is opened."""
import copy,importlib.util,pathlib,struct,unittest
path=pathlib.Path(__file__).with_name('aud23-event-observer.py');spec=importlib.util.spec_from_file_location('aud23_event_observer',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
BASE=0x8c000000;MGR=BASE+0x1000;ARRAY=BASE+0x10000;RD=BASE+0x3000;SAVEHDR=BASE+0x70000;STRIDE=0xde0
class Memory:
 def __init__(self):self.data=bytearray(0x1000000);self.hook=None;self.full_reads=0
 def put(self,address,fmt,*values):struct.pack_into(fmt,self.data,address-BASE,*values)
 def read_pointer(self,address,count):
  offset=m.ram.ram_offset(address)
  if count<1 or offset+count>len(self.data):raise OSError('bad extent')
  if address==ARRAY and count==3*STRIDE:
   self.full_reads+=1
   if self.hook:self.hook(self,self.full_reads)
  return bytes(self.data[offset:offset+count])
 def u32(self,address):return struct.unpack('<I',self.read_pointer(address,4))[0]
def pool():
 r=Memory();r.put(MGR,'<III',ARRAY,3,STRIDE);r.put(MGR+0x10,'<I',ARRAY)
 for i in range(3):
  a=ARRAY+i*STRIDE;r.put(a,'<II',1,ARRAY+(i+1)*STRIDE if i<2 else 0);r.put(a+0xf8,'<I',100+i);r.data[a-BASE+0x100]=0x12;r.data[a-BASE+0x12e]=0;r.data[a-BASE+0x398]=i+2;r.put(a+0x1d8,'<I',BASE+0x90000);r.put(a+0x290,'<f',2.0);r.put(a+0x294,'<H',60)
 return r
def save():
 r=Memory();r.put(RD+2,'<H',2);r.put(RD+0x14,'<II',SAVEHDR,SAVEHDR+16);r.put(SAVEHDR,'<II',16+2*0xd8,2)
 for i,room in enumerate([0x117,0x10c]):
  a=SAVEHDR+16+i*0xd8;r.data[a-BASE:a-BASE+2]=bytes([room>>8,room&255]);r.put(a+4,'<I',0x20000000)
 return r
class GuardControls(unittest.TestCase):
 def test_pool_positive_current_whole_elements(self):
  p=m.read_pool(pool(),MGR);self.assertTrue(p['target_sample_complete']);self.assertTrue(p['membership_double_read']);self.assertEqual([a['entry'] for a in p['actors']],[2,3,4])
 def test_huge_count_and_wrong_stride_are_rejected(self):
  for count,stride in [(513,STRIDE),(0,STRIDE),(3,0x398),(512,0x10000)]:
   r=pool();r.put(MGR+4,'<II',count,stride)
   with self.assertRaises(m.UnknownSample):m.read_pool(r,MGR)
 def test_array_extent_cannot_leave_main_ram(self):
  r=pool();r.put(MGR,'<I',0x8cfffff0)
  with self.assertRaises(m.UnknownSample):m.read_pool(r,MGR)
 def test_alive_link_misalignment_and_cycle_rejected(self):
  for link in [ARRAY+1,ARRAY]:
   r=pool();r.put(ARRAY+4,'<I',link)
   with self.assertRaises(m.UnknownSample):m.read_pool(r,MGR)
 def test_serial_reuse_does_not_promote(self):
  r=pool();r.hook=lambda r,n:r.put(ARRAY+0xf8,'<I',999) if n==2 else None
  p=m.read_pool(r,MGR);self.assertFalse(p['target_sample_complete']);self.assertNotIn(2,[a['entry'] for a in p['actors']])
 def test_retirement_does_not_promote(self):
  for flags in [0x201,0]:
   r=pool();r.hook=lambda r,n:r.put(ARRAY,'<I',flags) if n==2 else None
   p=m.read_pool(r,MGR);self.assertFalse(p['target_sample_complete']);self.assertNotIn(2,[a['entry'] for a in p['actors']])
 def test_membership_change_does_not_promote(self):
  r=pool();r.hook=lambda r,n:r.put(ARRAY+4,'<I',ARRAY+2*STRIDE) if n==2 else None
  with self.assertRaises(m.UnknownSample):m.read_pool(r,MGR)
 def test_manager_changes_are_unknown(self):
  r=pool();r.hook=lambda r,n:r.put(MGR+0x10,'<I',ARRAY+STRIDE) if n==2 else None
  with self.assertRaises(m.UnknownSample):m.read_pool(r,MGR)
 def test_unlinked_or_wrong_class_not_counted(self):
  r=pool();r.put(MGR+0x10,'<I',ARRAY+STRIDE)
  self.assertNotIn(2,[a['entry'] for a in m.read_pool(r,MGR)['actors']])
  r=pool();r.data[ARRAY-BASE+0x12e]=2
  self.assertNotIn(2,[a['entry'] for a in m.read_pool(r,MGR)['actors']])
 def test_direct_object_role_is_mandatory(self):
  roles={'pG':'pointer_global','pPL':'pointer_global','_RoomData':'direct_object','_EmMgr':'direct_object'};meta={'schema':1,'programme_symbols':{n:{'address':hex(BASE+16*i),'storage':v} for i,(n,v) in enumerate(roles.items())}}
  self.assertEqual(len(m.symbols_from_manifest(meta)),4);meta['programme_symbols']['_RoomData']['storage']='pointer_global'
  with self.assertRaises(m.UnknownSample):m.symbols_from_manifest(meta)
 def test_room_record_native_id_not_assumed(self):
  x=m.read_room_save(save(),RD,0x117);self.assertEqual(x['raw_id_bytes'],'0117');self.assertEqual(x['rsf'],'20000000')
 def test_duplicate_missing_and_bad_save_header_reject(self):
  r=save();a=SAVEHDR+16+0xd8;r.data[a-BASE:a-BASE+2]=b'\1\x17'
  with self.assertRaises(m.UnknownSample):m.read_room_save(r,RD,0x117)
  with self.assertRaises(m.UnknownSample):m.read_room_save(save(),RD,0x118)
  r=save();r.put(SAVEHDR+4,'<I',3)
  with self.assertRaises(m.UnknownSample):m.read_room_save(r,RD,0x117)
 def test_r117_preseed_and_entry_only_do_not_pass(self):
  row=lambda rsf,event,pos:{'room':'117','room_save':{'rsf':f'{rsf:08x}'},'event_active':event,'player':{'pos':pos}}
  base=row(0,False,[0,0,0]);started=row(0x20000000,True,[0,0,0]);end=row(0x40000000,False,[-2910,4000,6610])
  good=m.r117_summary([base,started,end]);self.assertTrue(good['source_state_sequence_observed']);self.assertFalse(good['acceptance_pass'])
  for bad in [[base],[end],[base,end],[started,end],[base,started,row(0x40000000,True,[-2910,4000,6610])]]:
   self.assertFalse(m.r117_summary(bad)['source_state_sequence_observed'])
 def test_dam_progress_requires_header_serial_onset_and_exit(self):
  p=m.read_pool(pool(),MGR);p['actors']=[p['actors'][0]]
  def row(event,frame,actors,pos,onset=True):
   v=copy.deepcopy(p);v['actors']=copy.deepcopy(actors)
   for a in v['actors']:a['frame']=frame
   return {'room':'10c','event_active':event,'Frame_cnt':int(frame+10),'area_onset_marker_observed':onset,'pool':v,'player':{'pos':pos}}
  actors=p['actors'];base=row(False,0,[],[1,0,2],False);a=row(True,1,actors,[1,0,2]);b=row(True,3,actors,[1,0,2]);end=row(False,5,[],[6609,0,17172])
  good=m.dam_summary([base,a,b,end]);self.assertTrue(good['pool_event_sequence_observed']);self.assertFalse(good['phase_witness_pass']);self.assertFalse(good['acceptance_pass'])
  variants=[]
  v=copy.deepcopy(b);v['pool']['actors'][0].pop('motion_header_sha256',None);variants.append([base,a,v,end])
  v=copy.deepcopy(b);v['pool']['actors'][0]['serial']+=1;variants.append([base,a,v,end])
  v=copy.deepcopy(b);v['pool']['actors'][0]['motion_header_sha256']='f'*64;variants.append([base,a,v,end])
  v=copy.deepcopy(a);v['area_onset_marker_observed']=False;w=copy.deepcopy(b);w['area_onset_marker_observed']=False;variants.append([base,v,w,end])
  v=copy.deepcopy(end);v['player']['pos']=[1,0,2];variants.append([base,a,b,v]);variants.append([base,a,end]);variants.append([a,b,end])
  for bad in variants:self.assertFalse(m.dam_summary(bad)['pool_event_sequence_observed'])
if __name__=='__main__':unittest.main(verbosity=2)
