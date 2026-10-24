"""RAM-only synthetic controls for guarded source state; no native process or guest is opened."""
import copy,hashlib,importlib.util,json,pathlib,struct,tempfile,unittest
path=pathlib.Path(__file__).with_name('aud23-event-observer-v2.py');spec=importlib.util.spec_from_file_location('aud23_event_observer',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
FIX=path.parent/'event-fixtures'
META=json.loads((FIX/'on-5e4d-symbols-v2.json').read_text());ABI=m.validate_abi(META)
BASE=0x8c000000;MGR=BASE+0x1000;ARRAY=BASE+0x10000;RD=BASE+0x3000;SAVEHDR=BASE+0x70000;STRIDE=ABI['actor.sizeof']
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
 r=Memory();r.put(MGR,'<IIII',BASE+0x2000,ARRAY,3,STRIDE);r.put(MGR+ABI['manager.pAlive'],'<I',ARRAY)
 for i in range(3):
  a=ARRAY+i*STRIDE;r.put(a,'<III',BASE+0x2004,1,ARRAY+(i+1)*STRIDE if i<2 else 0);r.put(a+0xf8,'<I',100+i);r.data[a-BASE+0x100]=0x12;r.data[a-BASE+0x12e]=0;r.data[a-BASE+0x398]=i+2;r.put(a+0x1d8,'<I',BASE+0x90000);r.put(a+0x290,'<f',2.0);r.put(a+0x294,'<H',60)
 return r
def save():
 r=Memory();r.put(RD+2,'<H',2);r.put(RD+0x14,'<II',SAVEHDR,SAVEHDR+16);r.put(SAVEHDR,'<II',16+2*0xd8,2)
 for i,room in enumerate([0x117,0x10c]):
  a=SAVEHDR+16+i*0xd8;r.data[a-BASE:a-BASE+2]=bytes([room>>8,room&255]);r.put(a+4,'<I',0x20000000)
 return r
class GuardControls(unittest.TestCase):
 def test_pool_positive_current_whole_elements(self):
  p=m.read_pool(pool(),MGR,ABI);self.assertTrue(p['target_sample_complete']);self.assertTrue(p['membership_double_read']);self.assertEqual([a['entry'] for a in p['actors']],[2,3,4])
 def test_huge_count_and_wrong_stride_are_rejected(self):
  for count,stride in [(513,STRIDE),(0,STRIDE),(3,0x398),(512,0x10000)]:
   r=pool();r.put(MGR+ABI['manager.nArray'],'<II',count,stride)
   with self.assertRaises(m.UnknownSample):m.read_pool(r,MGR,ABI)
 def test_array_extent_cannot_leave_main_ram(self):
  r=pool();r.put(MGR+ABI['manager.pArray'],'<I',0x8cfffff0)
  with self.assertRaises(m.UnknownSample):m.read_pool(r,MGR,ABI)
 def test_alive_link_misalignment_and_cycle_rejected(self):
  for link in [ARRAY+1,ARRAY]:
   r=pool();r.put(ARRAY+ABI['actor.pNext'],'<I',link)
   with self.assertRaises(m.UnknownSample):m.read_pool(r,MGR,ABI)
 def test_serial_reuse_does_not_promote(self):
  r=pool();r.hook=lambda r,n:r.put(ARRAY+0xf8,'<I',999) if n==2 else None
  p=m.read_pool(r,MGR,ABI);self.assertFalse(p['target_sample_complete']);self.assertNotIn(2,[a['entry'] for a in p['actors']])
 def test_retirement_does_not_promote(self):
  for flags in [0x201,0]:
   r=pool();r.hook=lambda r,n:r.put(ARRAY+ABI['actor.be_flag'],'<I',flags) if n==2 else None
   p=m.read_pool(r,MGR,ABI);self.assertFalse(p['target_sample_complete']);self.assertNotIn(2,[a['entry'] for a in p['actors']])
 def test_membership_change_does_not_promote(self):
  r=pool();r.hook=lambda r,n:r.put(ARRAY+ABI['actor.pNext'],'<I',ARRAY+2*STRIDE) if n==2 else None
  with self.assertRaises(m.UnknownSample):m.read_pool(r,MGR,ABI)
 def test_manager_changes_are_unknown(self):
  r=pool();r.hook=lambda r,n:r.put(MGR+ABI['manager.pAlive'],'<I',ARRAY+STRIDE) if n==2 else None
  with self.assertRaises(m.UnknownSample):m.read_pool(r,MGR,ABI)
 def test_unlinked_or_wrong_class_not_counted(self):
  r=pool();r.put(MGR+ABI['manager.pAlive'],'<I',ARRAY+STRIDE)
  self.assertNotIn(2,[a['entry'] for a in m.read_pool(r,MGR,ABI)['actors']])
  r=pool();r.data[ARRAY-BASE+0x12e]=2
  self.assertNotIn(2,[a['entry'] for a in m.read_pool(r,MGR,ABI)['actors']])
 def test_direct_object_role_is_mandatory(self):
  roles={'pG':'pointer_global','pPL':'pointer_global','_RoomData':'direct_object','_EmMgr':'direct_object'};meta={'schema':2,'programme_symbols':{n:{'address':hex(BASE+16*i),'storage':v} for i,(n,v) in enumerate(roles.items())}}
  self.assertEqual(len(m.symbols_from_manifest(meta)),4);meta['programme_symbols']['_RoomData']['storage']='pointer_global'
  with self.assertRaises(m.UnknownSample):m.symbols_from_manifest(meta)
 def test_room_record_native_id_not_assumed(self):
  x=m.read_room_save(save(),RD,0x117,ABI);self.assertEqual(x['raw_id_bytes'],'0117');self.assertEqual(x['rsf'],'20000000')
 def test_duplicate_missing_and_bad_save_header_reject(self):
  r=save();a=SAVEHDR+16+0xd8;r.data[a-BASE:a-BASE+2]=b'\1\x17'
  with self.assertRaises(m.UnknownSample):m.read_room_save(r,RD,0x117,ABI)
  with self.assertRaises(m.UnknownSample):m.read_room_save(save(),RD,0x118,ABI)
  r=save();r.put(SAVEHDR+4,'<I',3)
  with self.assertRaises(m.UnknownSample):m.read_room_save(r,RD,0x117,ABI)
 def test_r117_preseed_and_entry_only_do_not_pass(self):
  row=lambda rsf,event,pos:{'room':'117','room_save':{'rsf':f'{rsf:08x}'},'event_active':event,'player':{'pos':pos}}
  base=row(0,False,[0,0,0]);started=row(0x20000000,True,[0,0,0]);end=row(0x40000000,False,[-2910,4000,6610])
  good=m.r117_summary([base,started,end]);self.assertTrue(good['source_state_sequence_observed']);self.assertFalse(good['acceptance_pass'])
  for bad in [[base],[end],[base,end],[started,end],[base,started,row(0x40000000,True,[-2910,4000,6610])]]:
   self.assertFalse(m.r117_summary(bad)['source_state_sequence_observed'])
 def test_dam_progress_requires_header_serial_onset_and_exit(self):
  p=m.read_pool(pool(),MGR,ABI);p['actors']=[p['actors'][0]]
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
 def test_both_actual_compiler_receipts_and_section_hashes(self):
  for name in ['on-5e4d-symbols-v2.json','off-control-2a-symbols-v2.json']:
   meta=json.loads((FIX/name).read_text());abi=m.validate_abi(meta);self.assertEqual(abi,ABI)
   proof=json.loads(pathlib.Path(meta['target_abi_receipt']).read_text())
   section=struct.pack('<'+'I'*len(proof['fields']),*(abi[k] for k,expr in proof['fields']))
   self.assertEqual(hashlib.sha256(section).hexdigest(),proof['layout_bytes_sha256'])
   self.assertIn('-m4-single',proof['actual_probe_command']);self.assertIn('-DRE4DC_GAME',proof['actual_probe_command'])
  self.assertEqual([ABI['manager.'+k] for k in ['pArray','nArray','stride','pAlive']],[4,8,12,20])
  self.assertEqual([ABI['actor.'+k] for k in ['be_flag','pNext']],[4,8])
 def test_actual_programme_object_corroborates_probe(self):
  proof=json.loads((FIX/'target-abi-actual-em-object-v2.json').read_text())
  self.assertEqual(proof['source'],META['source'])
  members={(r['name'],r['offset']) for r in proof['actual_dwarf_members']}
  for name,key in [('be_flag','actor.be_flag'),('pNext','actor.pNext'),('pArray','manager.pArray'),('nArray','manager.nArray'),('size','manager.stride'),('pAlive','manager.pAlive')]:self.assertIn((name,ABI[key]),members)
  self.assertIn('@(12,r4)',proof['actual_constructor_disassembly']);self.assertIn('@(4,r4)',proof['actual_initWork_disassembly'])
 def test_schema_layout_source_elf_and_receipt_tamper_rejected(self):
  for change in [lambda x:x.update(schema=1),lambda x:x['target_layout'].update({'actor.be_flag':0}),lambda x:x.update(source='0'*40),lambda x:x.update(program_elf_sha256='0'*64),lambda x:x.update(target_abi_receipt_sha256='0'*64)]:
   meta=copy.deepcopy(META);change(meta)
   with self.assertRaises(m.UnknownSample):m.validate_abi(meta)
  meta=copy.deepcopy(META);meta['target_abi_receipt']='nonexistent-abi-receipt.json'
  with self.assertRaises(OSError):m.validate_abi(meta)
 def test_unknown_retains_actual_raw_and_parsed_header(self):
  r=pool();r.put(MGR+ABI['manager.nArray'],'<I',513);raw=r.read_pointer(MGR,ABI['manager.sizeof']).hex()
  with self.assertRaises(m.UnknownSample) as caught:m.read_pool(r,MGR,ABI)
  d=caught.exception.diagnostics;self.assertEqual(d['raw_pool_headers']['before'],raw);self.assertEqual(d['parsed_pool_headers']['before']['nArray'],513);self.assertEqual(d['compiler_manager_offsets']['manager.pArray'],4)
 def test_old_comment_layout_is_not_a_fallback(self):
  r=Memory();r.put(MGR,'<III',ARRAY,3,STRIDE);r.put(MGR+0x10,'<I',ARRAY)
  with self.assertRaises(m.UnknownSample):m.read_pool(r,MGR,ABI)
 def test_optional_stills_source_states_and_exact_maximum_two(self):
  row=lambda rsf,event,pos:{'room':'117','room_save':{'rsf':f'{rsf:08x}'},'event_active':event,'player':{'pos':pos}}
  baseline=row(0,False,[0,0,0]);solved=row(0x40000000,False,[-2910,4000,6610]);budget=m.StillBudget()
  for bad in [dict(baseline,unknown='missing'),dict(baseline,room='10c'),row(0x20000000,True,[0,0,0]),row(0x60000000,False,[-2910,4000,6610]),row(0x40000000,True,[-2910,4000,6610]),row(0x40000000,False,[0,0,0])]:self.assertIsNone(budget.reserve(bad))
  self.assertEqual(budget.reserve(baseline),'unsolved-baseline');self.assertIsNone(budget.reserve(baseline));self.assertEqual(budget.reserve(solved),'solved-disarmed-event-clear');self.assertIsNone(budget.reserve(solved));self.assertEqual(len(budget.phases),2)
if __name__=='__main__':unittest.main(verbosity=2)
