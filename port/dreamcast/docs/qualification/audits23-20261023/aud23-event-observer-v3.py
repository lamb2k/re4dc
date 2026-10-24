"""V3 native-sparse compiler-ABI-bound read-only aud23 event observer. Run only inside census-bound-run.py; no guest on import."""
import hashlib,importlib.util,json,math,os,pathlib,queue,re,runpy,struct,subprocess,sys,threading,time
BACKEND=pathlib.Path(__file__).with_name('event-fixtures')/'stat_owned_ram.py'
spec=importlib.util.spec_from_file_location('aud23_owned_ram',BACKEND);ram=importlib.util.module_from_spec(spec);spec.loader.exec_module(ram)
MAX_RECORDS=512;MAX_POOL_BYTES=4*1024*1024;MAX_SAVE_BYTES=512*0xd8
class UnknownSample(ValueError):
 def __init__(self,message,diagnostics=None):
  super().__init__(message);self.diagnostics=diagnostics or {}


def digest(path):
 h=hashlib.sha256()
 with pathlib.Path(path).open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def extent(pointer,count):
 off=ram.ram_offset(pointer)
 if pointer%4 or count<1 or off+count>0x1000000:raise UnknownSample('unaligned/out-of-RAM extent')
 return off
def symbols_from_manifest(meta):
 if meta.get('schema')!=3:raise UnknownSample('v3 symbol and compiler ABI schema required')
 roles={'pG':'pointer_global','pPL':'pointer_global','_RoomData':'direct_object','_EmMgr':'direct_object'}
 rows=meta.get('programme_symbols',{})
 if set(rows)!=set(roles):raise UnknownSample('exact symbols missing/extra')
 out={}
 for name,role in roles.items():
  if rows[name].get('storage')!=role:raise UnknownSample('pointer/direct-object role mismatch: '+name)
  out[name]=int(rows[name]['address'],0);extent(out[name],4)
 return out

def validate_abi(meta):
 if meta.get('schema')!=3:raise UnknownSample('v3 compiler ABI manifest required; no v1/v2 fallback')
 path=pathlib.Path(meta['target_abi_receipt']);raw=path.read_bytes()
 if hashlib.sha256(raw).hexdigest()!=meta['target_abi_receipt_sha256']:raise UnknownSample('target ABI receipt digest mismatch')
 proof=json.loads(raw);abi=proof['layout']
 if proof.get('schema')!=3 or proof.get('derivation')!='actual compiler builtin_offsetof/sizeof constant section plus exact pinned native Pool/Chunk declarations':raise UnknownSample('ABI derivation missing')
 if proof.get('elf_sha256')!=meta['program_elf_sha256'] or proof.get('source')!=meta['source']:raise UnknownSample('ABI receipt belongs to another exact programme')
 if abi!=meta.get('target_layout'):raise UnknownSample('manifest/compiler constant disagreement')
 if abi.get('magic')!=0x33494241 or abi.get('schema')!=3 or abi.get('pointer_bytes')!=4 or abi.get('u32_bytes')!=4:raise UnknownSample('unsupported target words')
 # The reused player decoder has these offsets. Refuse a new target ABI instead of guessing.
 fixed={'actor.serial':0xf8,'actor.id':0x100,'actor.type':0x101,'actor.kindid':0x12e,'actor.emset_no':0x398,'actor.pos':0x94,'actor.stat':0xfc,'actor.pMotion':0x1d8,'actor.motState':0x21a,'actor.frame':0x290,'actor.frameMax':0x294}
 if any(abi.get(k)!=v for k,v in fixed.items()):raise UnknownSample('compiler layout incompatible with pinned player decoder')
 for prefix,fields,widths in [('manager',['pArray','nArray','stride','pAlive','Guid'],[4]*5),('actor',['be_flag','pNext','serial','id','type','kindid','emset_no'],[4,4,4,1,1,1,1]),('roomdata',['num','pSaveBuf','pSave'],[2,4,4])]:
  size=abi[prefix+'.sizeof']
  if not 1<=size<=0x10000:raise UnknownSample('ABI object size outside cap')
  for name,width in zip(fields,widths):
   off=abi[prefix+'.'+name]
   if not isinstance(off,int) or off<0 or off+width>size:raise UnknownSample('ABI field outside actual compiler sizeof')
 if not proof.get('actual_probe_command') or not proof.get('probe_object_sha256') or not proof.get('source_headers_sha256'):raise UnknownSample('compiler proof incomplete')
 if proof['frozen_pools_symbol']!=meta.get('frozen_pools_symbol') or meta['frozen_pools_symbol'].get('storage')!='direct_object':raise UnknownSample('frozen-state symbol mismatch')
 extent(int(meta['frozen_pools_symbol']['address'],0),4)
 if proof['parts_bridge_sha256']!=meta.get('native_backing',{}).get('parts_bridge_sha256'):raise UnknownSample('native backing source mismatch')
 text=proof['parts_budget_header_text']
 if hashlib.sha256(text.encode()).hexdigest()!=proof['parts_budget_header_sha256'] or '#define RE4DC_ENEMY_DEMAND 1\n' not in text or abi.get('target.WORKAT_INLINE')!=1:raise UnknownSample('native sparse backing flags not authenticated')
 if hashlib.sha256(proof['exact_native_declarations'].encode()).hexdigest()!=proof['exact_native_declarations_sha256']:raise UnknownSample('native declarations digest mismatch')
 if abi.get('pool.sizeof')!=64 or abi.get('chunk.sizeof')!=32:raise UnknownSample('native header ABI incompatible with source slot lookup')
 return abi

def read_room_save(reader,roomdata,room,abi):
 first=reader.read_pointer(roomdata,abi['roomdata.sizeof']);num=struct.unpack_from('<H',first,abi['roomdata.num'])[0]
 buf=struct.unpack_from('<I',first,abi['roomdata.pSaveBuf'])[0];save=struct.unpack_from('<I',first,abi['roomdata.pSave'])[0]
 stride=abi['roomsave.sizeof']
 if not 0<num<=MAX_RECORDS:raise UnknownSample('room-save count outside bound',{'raw_roomdata_header':first.hex(),'num':num})
 count=num*stride;extent(save,count);extent(buf,16+count)
 if count>MAX_SAVE_BYTES or save!=buf+16:raise UnknownSample('room-save extent/header mismatch',{'raw_roomdata_header':first.hex()})
 header=reader.read_pointer(buf,16)
 if struct.unpack_from('<II',header)!=(16+count,num):raise UnknownSample('room-save header size/count mismatch',{'raw_roomdata_header':first.hex(),'raw_save_header':header.hex()})
 data=reader.read_pointer(save,count)
 if reader.read_pointer(roomdata,abi['roomdata.sizeof'])!=first or reader.read_pointer(buf,16)!=header:raise UnknownSample('room-save owner/header changed during read')
 wanted=bytes([room>>8,room&255]);hits=[i for i in range(num) if data[i*stride:i*stride+2]==wanted]
 if len(hits)!=1:raise UnknownSample('room-save record absent/duplicate')
 index=hits[0];address=save+index*stride;rec=data[index*stride:(index+1)*stride];check=reader.read_pointer(address,8)
 if check[:4]!=rec[:4]:raise UnknownSample('room-save record changed identity')
 return {'record':hex(address),'record_index':index,'records':num,'raw_id_bytes':wanted.hex(),'rsf':f'{struct.unpack_from("<I",check,4)[0]:08x}','compiler_layout_used':True}

def raw_pool_fields(raw,abi):
 return {name:(hex(struct.unpack_from('<I',raw,abi['manager.'+name])[0]) if name in ['pArray','pAlive'] else struct.unpack_from('<I',raw,abi['manager.'+name])[0]) for name in ['pArray','nArray','stride','pAlive','Guid']}
def actor_at(data,index,stride,array,abi):
 off=index*stride;flags=struct.unpack_from('<I',data,off+abi['actor.be_flag'])[0];serial=struct.unpack_from('<I',data,off+abi['actor.serial'])[0]
 return {'address':hex(array+off),'index':index,'serial':serial,'be_flag':f'{flags:08x}','alive':(flags&0x201)==1,'id':data[off+abi['actor.id']],'kind':data[off+abi['actor.kindid']],'entry':data[off+abi['actor.emset_no']]}

class ReadBudget:
 def __init__(self,reader):self.reader=reader;self.used=0
 def read(self,address,count):
  extent(address,count)
  if self.used+count>MAX_POOL_BYTES:raise UnknownSample('combined sparse snapshots exceed total read cap')
  self.used+=count;return self.reader.read_pointer(address,count)
 def u32(self,address):return struct.unpack('<I',self.read(address,4))[0]

def fields(raw,prefix,names,abi):
 return {name:struct.unpack_from('<I',raw,abi[prefix+'.'+name])[0] for name in names}
def aligned32(n):return (n+31)&~31

def sparse_snapshot(budget,manager,abi,frozen_address,diagnostics,label):
 detail={};diagnostics['snapshots'][label]=detail
 freeze1=budget.u32(frozen_address);detail['frozen_before']=freeze1
 manager_raw=budget.read(manager,abi['manager.sizeof']);detail['raw_manager_before']=manager_raw.hex();mf=fields(manager_raw,'manager',['pArray','nArray','stride','pAlive','Guid','pArrayPush','pAlivePush','nArrayPush'],abi);detail['manager_fields']=mf
 if freeze1 or mf['pArrayPush']:raise UnknownSample('frozen or debug-pushed pool is not authenticated native room backing')
 a,n,stride,head=mf['pArray'],mf['nArray'],mf['stride'],mf['pAlive']
 if not 0<n<=MAX_RECORDS or stride!=abi['actor.sizeof']:raise UnknownSample('pool count/stride outside exact compiler ABI bound')
 if a%32:raise UnknownSample('native pool header is not 32-byte aligned')
 pool_raw=budget.read(a,abi['pool.sizeof']);pf=fields(pool_raw,'pool',['chunks','capacity','bytes','peak','chunks_count','reclaims','failures','heap','handle'],abi);detail.update(raw_pool_header=pool_raw.hex(),pool_fields=pf,chunks=[])
 if pf['capacity']!=n or pf['chunks_count']>(n+1)//2:raise UnknownSample('native pool capacity/chunk count mismatch')
 pool_bytes=aligned32(abi['pool.sizeof']+4*n);extent(a,pool_bytes)
 slots_raw=budget.read(a+abi['pool.sizeof'],4*n);slots=struct.unpack('<'+'I'*n,slots_raw);detail['raw_slots']=slots_raw.hex()
 present=[v for v in slots if v]
 if len({extent(p,4) for p in present})!=len(present):raise UnknownSample('duplicate physical slot pointers')
 ranges=[(extent(a,pool_bytes),extent(a,pool_bytes)+pool_bytes)];owners={};records={};headers=[];seen=set();chunk=pf['chunks'];accounted=pool_bytes+64
 while chunk:
  physical=extent(chunk,abi['chunk.sizeof'])
  if chunk%32 or physical in seen or len(seen)>=(n+1)//2:raise UnknownSample('chunk alignment/cycle/count outside native page bound')
  seen.add(physical);raw=budget.read(chunk,abi['chunk.sizeof']);cf=fields(raw,'chunk',['next','first','count','bytes'],abi);detail['chunks'].append({'address':hex(chunk),'raw_header':raw.hex(),**cf})
  first,count=cf['first'],cf['count']
  if first>=n or first%2 or count!=min(2,n-first):raise UnknownSample('chunk is not an exact native enemy two-slot page')
  allocation=aligned32(abi['chunk.sizeof']+count*stride);lo=extent(chunk,allocation);hi=lo+allocation
  if cf['bytes']!=allocation+64:raise UnknownSample('chunk allocation accounting mismatch')
  if any(lo<end and hi>begin for begin,end in ranges):raise UnknownSample('physical chunk/pool ranges overlap')
  ranges.append((lo,hi));accounted+=cf['bytes']
  if accounted>MAX_POOL_BYTES:raise UnknownSample('native allocated backing exceeds cap')
  for j in range(count):
   index=first+j;expected=chunk+abi['chunk.sizeof']+j*stride
   if index in owners or slots[index]!=expected:raise UnknownSample('slot/chunk ownership mismatch or duplicate logical page')
   owners[index]=expected
  payload=budget.read(chunk+abi['chunk.sizeof'],count*stride)
  for j in range(count):records[first+j]=payload[j*stride:(j+1)*stride]
  if budget.read(chunk,abi['chunk.sizeof'])!=raw:raise UnknownSample('chunk ownership changed during payload read')
  headers.append((chunk,raw));chunk=cf['next']
 if len(headers)!=pf['chunks_count'] or accounted!=pf['bytes'] or pf['peak']<pf['bytes']:raise UnknownSample('pool chunk/accounting metadata mismatch')
 if set(owners)!={i for i,p in enumerate(slots) if p}:raise UnknownSample('nonzero slot is not owned by a linked native chunk')
 # Recheck every ownership boundary; never follow an unauthenticated alive-list pointer.
 for address,raw in headers:
  if budget.read(address,abi['chunk.sizeof'])!=raw:raise UnknownSample('chunk ownership changed at snapshot end')
 if budget.read(a+abi['pool.sizeof'],4*n)!=slots_raw or budget.read(a,abi['pool.sizeof'])!=pool_raw:raise UnknownSample('slot table or pool header changed during snapshot')
 manager_after=budget.read(manager,abi['manager.sizeof']);freeze2=budget.u32(frozen_address);detail.update(raw_manager_after=manager_after.hex(),frozen_after=freeze2)
 if manager_after!=manager_raw or freeze2!=freeze1 or freeze2:raise UnknownSample('manager/push/frozen state changed during snapshot')
 by_address={address:index for index,address in owners.items()};order=[];visited=set();p=head
 while p:
  if p not in by_address:raise UnknownSample('alive link is not an authenticated current native slot')
  index=by_address[p]
  if index in visited or len(visited)>=n:raise UnknownSample('alive list cycle/overrun')
  visited.add(index);order.append(index);p=struct.unpack_from('<I',records[index],abi['actor.pNext'])[0]
 ownership=(manager_raw,pool_raw,slots_raw,tuple(headers))
 return {'array':a,'count':n,'stride':stride,'head':head,'records':records,'owners':owners,'order':order,'ownership':ownership,'chunks':detail['chunks'],'accounted_bytes':accounted}

def read_pool(reader,manager,abi,frozen_address):
 diagnostics={'manager_address':hex(manager),'frozen_symbol':hex(frozen_address),'snapshots':{},'compiler_manager_offsets':{k:v for k,v in abi.items() if k.startswith('manager.')}};budget=ReadBudget(reader)
 try:
  one=sparse_snapshot(budget,manager,abi,frozen_address,diagnostics,'first');two=sparse_snapshot(budget,manager,abi,frozen_address,diagnostics,'second')
  if one['ownership']!=two['ownership'] or set(one['order'])!=set(two['order']):raise UnknownSample('native backing ownership or alive membership changed across snapshots')
  actors=[];unstable=[]
  for index in two['order']:
   address=two['owners'][index];b1=one['records'][index];b2=two['records'][index];before=actor_at(b1,0,two['stride'],address,abi);after=actor_at(b2,0,two['stride'],address,abi);after['index']=index
   target=lambda x:x['kind']==0 and 0x10<=x['id']<=0x20 and x['entry'] in [2,3,4]
   if not(target(before) or target(after)):continue
   if any(before[k]!=after[k] for k in ['serial','id','kind','entry','alive']) or not(before['alive'] and after['alive']):unstable.append({'index':index,'reason':'serial/class/list-entry/liveness changed or retired'});continue
   after.update(ram.decode_model(b2[:0x298]));p1=struct.unpack_from('<I',b1,abi['actor.pMotion'])[0];p2=int(after['pMotion'],16);after['motion_stable_during_pool_read']=p1==p2
   if p2 and p1==p2:
    try:after['motion_header_sha256']=hashlib.sha256(budget.read(p2,64)).hexdigest()
    except (OSError,ValueError) as exc:after['motion_header_unknown']=str(exc)
   actors.append(after)
  manager_raw,pool_raw,slots_raw,headers=two['ownership']
  final={'raw_manager':budget.read(manager,abi['manager.sizeof']).hex(),'frozen':budget.u32(frozen_address)};diagnostics['final_ownership_guard']=final
  if final['raw_manager']!=manager_raw.hex() or final['frozen']:raise UnknownSample('manager/push/frozen state changed after motion header reads')
  if budget.read(two['array'],abi['pool.sizeof'])!=pool_raw or budget.read(two['array']+abi['pool.sizeof'],4*two['count'])!=slots_raw:raise UnknownSample('pool or table changed after motion header reads')
  for address,raw in headers:
   if budget.read(address,abi['chunk.sizeof'])!=raw:raise UnknownSample('chunk ownership changed after motion header reads')
  return {'array':hex(two['array']),'count':two['count'],'stride':two['stride'],'backing':'native-sparse-enemy-two-slot-pages','allocated_slots':len(two['records']),'chunks':two['chunks'],'accounted_bytes':two['accounted_bytes'],'bytes_read_total':budget.used,'active_members':len(two['order']),'membership_double_read':True,'ownership_rechecked_after_motion_headers':True,'actors':actors,'unstable_targets':unstable,'target_sample_complete':not unstable,'native_ownership_diagnostics':diagnostics,'compiler_layout_used':True,'lifetime_limit':'Two asynchronous ownership snapshots do not prove an unobserved ABA or durable owner generation.'}
 except (OSError,ValueError) as exc:
  diagnostics['bytes_read_total']=budget.used
  raise UnknownSample(str(exc),diagnostics) from exc

def common(reader,symbols,abi):
 pg=reader.u32(symbols['pG']);extent(pg,0x51e8)
 player=reader.player(symbols['pPL'])
 sf1=reader.u32(pg+abi['global.SF1']);frame=reader.u32(pg+abi['global.Frame_cnt']);room=struct.unpack('<H',reader.read_pointer(pg+abi['global.room_id'],2))[0]
 if reader.u32(symbols['pG'])!=pg or reader.u32(symbols['pPL'])!=int(player['pPL'],16):raise UnknownSample('player/global pointer changed during sample')
 return {'player':player,'pG':hex(pg),'room':f'{room:03x}','SF1':f'{sf1:08x}','event_active':bool(sf1&0x10000000),'Frame_cnt':frame,'sample_monotonic':time.monotonic()}

START_POSES={'r117':('117',[-2910,4000,6610]),'dam':('10c',[27865,-15316,43935])}

def placement_marker(line,mode):
 match=re.search(r'warp: placed room=([0-9a-f]{3}) pl=(-?\d+),(-?\d+),(-?\d+) ',line)
 if not match:return None
 room,pose=START_POSES[mode];actual=[int(match[i]) for i in [2,3,4]]
 if match[1]!=room or any(abs(a-b)>=100 for a,b in zip(actual,pose)):return None
 return {'line':line,'room':room,'position':actual,'anchor_frame':None}

def placement_readiness(row,marker,mode):
 room,pose=START_POSES[mode];player=row['player'];motion=int(player['pMotion'],16);initialized=False
 try:extent(motion,64);initialized=player['frameMax']>0 and all(math.isfinite(v) for v in player['pos']+[player['frame']])
 except (ValueError,OSError):pass
 placed=bool(marker and row['room']==room)
 if placed and marker['anchor_frame'] is None:marker['anchor_frame']=row['Frame_cnt']
 delta=row['Frame_cnt']-marker['anchor_frame'] if placed else None
 normal=placed and initialized
 baseline=normal and delta is not None and delta>=30 and delta<0x80000000 and all(abs(a-b)<100 for a,b in zip(player['pos'],pose))
 return {'placed_marker_observed':placed,'initialized_player':initialized,'placed_sample_anchor_frame':marker['anchor_frame'] if placed else None,'source_frames_since_placed_sample':delta,'observation_ready':normal,'baseline_ready':bool(baseline),'expected_initial_pose':pose,'limits':'Anchor is first RAM sample after actual placed log, not an exact render/simulation tick.'}

def r117_summary(rows):
 baseline=False;started=False;last=None
 for row in rows:
  if row.get('unknown') or row.get('room')!='117' or 'room_save' not in row or not row.get('placement_readiness',{}).get('observation_ready'):continue
  rsf=int(row['room_save']['rsf'],16)
  if not started and (rsf&0x60000000)==0 and not row['event_active'] and row['placement_readiness']['baseline_ready']:baseline=True
  if baseline and (rsf&0x20000000) and row['event_active']:started=True
  pos=row['player']['pos']
  if baseline and started and (rsf&0x60000000)==0x40000000 and not row['event_active'] and abs(pos[0]+2910)<100 and abs(pos[1]-4000)<100 and abs(pos[2]-6610)<100:last=row
 return {'baseline_unsolved_observed':baseline,'started_in_event_observed':started,'solved_disarmed_event_clear_endpose_observed':last is not None,'source_state_sequence_observed':bool(baseline and started and last),'final_witness':last,'acceptance_pass':False,'overlay_work_phase_claim':'omitted; exact current st1_3 work binding not authenticated','limits':'Root must inspect actual inputs/rendered gate and retain exact target/data binding; no allocation-failure injection or physical-console acceptance.'}

def dam_summary(rows):
 baseline=False;first=None;progress=[];previous={};end=None;seen_entry2=False
 for row in rows:
  if row.get('unknown') or row.get('room')!='10c' or not row.get('placement_readiness',{}).get('observation_ready'):continue
  pool=row.get('pool')
  if not pool or not pool.get('target_sample_complete'):continue
  entry2=[a for a in pool['actors'] if a['entry']==2 and a['id']==0x12 and a['kind']==0 and a['alive']]
  if not seen_entry2 and not row['event_active'] and not entry2 and row['placement_readiness']['baseline_ready']:baseline=True
  if entry2 and row['event_active'] and row.get('area_onset_marker_observed'):
   seen_entry2=True
   if first is None:first=row
   for actor in entry2:
    key=(pool['array'],pool['count'],pool['stride'],actor['index'],actor['serial'])
    old=previous.get(key)
    if old and actor.get('motion_header_sha256') and actor['motion_stable_during_pool_read'] and old['motion_stable_during_pool_read'] and actor['pMotion']==old['pMotion'] and actor['motion_header_sha256']==old.get('motion_header_sha256') and actor['frame']>old['frame']:
     progress.append({'actor':actor['address'],'serial':actor['serial'],'from_frame':old['frame'],'to_frame':actor['frame'],'global_frame':row['Frame_cnt'],'motion_header_sha256':actor['motion_header_sha256']})
    previous[key]=actor
  pos=row['player']['pos']
  if first and progress and not row['event_active'] and not entry2 and abs(pos[0]-6609)<100 and abs(pos[1])<100 and abs(pos[2]-17172)<100:end=row
 return {'baseline_clear_without_list2_observed':baseline,'guarded_list2_during_event_observed':first is not None,'guarded_motion_progress_pairs':progress,'normal_event_clear_source_exit_observed':end is not None,'pool_event_sequence_observed':bool(baseline and first and progress and end),'first_list2_witness':first,'final_witness':end,'phase_witness_pass':False,'acceptance_pass':False,'overlay_work_phase_claim':'omitted; no exact current st1_2 work/phase binding authenticated','limits':'Pool+event evidence is retained without claiming exact r10c ISSUE52 phases, admission cause, full dam traversal, owner generations or console acceptance. Missing/unstable/unknown is not a pass.'}

def r117_capture_phase(row):
 if row.get('room')!='117' or 'room_save' not in row or row.get('unknown') or not row.get('placement_readiness',{}).get('observation_ready'):return None
 rsf=int(row['room_save']['rsf'],16)
 if (rsf&0x60000000)==0 and not row['event_active'] and row['placement_readiness']['baseline_ready']:return 'unsolved-baseline'
 pos=row['player']['pos']
 if (rsf&0x60000000)==0x40000000 and not row['event_active'] and abs(pos[0]+2910)<100 and abs(pos[1]-4000)<100 and abs(pos[2]-6610)<100:return 'solved-disarmed-event-clear'
 return None

class StillBudget:
 def __init__(self):self.phases=set()
 def reserve(self,row):
  wanted=r117_capture_phase(row)
  if wanted is None or wanted in self.phases or len(self.phases)>=2:return None
  self.phases.add(wanted);return wanted

class Tail:
 def __init__(self,path):self.path=path;self.offset=0;self.pending=b''
 def poll(self):
  try:
   with self.path.open('rb') as f:
    if f.seek(0,2)<self.offset:raise UnknownSample('log truncated')
    f.seek(self.offset);new=f.read();self.offset=f.tell()
  except FileNotFoundError:return []
  lines=(self.pending+new).split(b'\n');self.pending=lines.pop();return [s.decode('ascii','replace') for s in lines]

def main():
 harness=pathlib.Path(sys.argv[1]);manifest=pathlib.Path(sys.argv[2]);mode=sys.argv[3];args=sys.argv[4:]
 if mode not in ['r117','dam']:raise ValueError('mode must be r117 or dam')
 original=subprocess.Popen
 if original.__name__!='BoundedPopen' or os.environ.get('RE4DC_EMU')!='console':raise RuntimeError('outer census-bound-run exact-child console guard required')
 meta=json.loads(manifest.read_text());symbols=symbols_from_manifest(meta);abi=validate_abi(meta);frozen_address=int(meta['frozen_pools_symbol']['address'],0)
 if digest(BACKEND)!=meta['ram_backend_sha256']:raise RuntimeError('RAM backend digest mismatch')
 if digest(harness)!=meta['source_sha256']['port/dreamcast/tools/d367/fullplay/fp_run.py']:raise RuntimeError('frozen fp_run source mismatch')
 if digest(meta['program_elf_windows'])!=meta['program_elf_sha256']:raise RuntimeError('bound ELF changed')
 base=pathlib.Path(args[args.index('--base')+1]);cap=pathlib.Path(args[args.index('--cap')+1]);base_meta=json.loads((base/'base.json').read_text())
 if base_meta.get('elf')!=meta['program_elf']:raise RuntimeError('base is not bound to this exact programme ELF')
 stop=threading.Event();worker=None;guest=None;rows=[];markers=[];errors=[];t0=time.monotonic();still_enabled=os.environ.get('AUD23_CAPTURE_STILLS')=='1';still_queue=queue.Queue(maxsize=2);still_budget=StillBudget();stills=[];still_worker=None;placed_marker=None
 receipt={'mode':mode,'source':meta['source'],'program_elf_sha256':meta['program_elf_sha256'],'symbol_manifest_sha256':digest(manifest),'symbol_manifest':str(manifest),'symbols':meta['programme_symbols'],'backend_sha256':digest(BACKEND),'read_only':True,'observer_version':3,'target_abi_receipt_sha256':meta['target_abi_receipt_sha256'],'target_layout':abi,'source_contract':meta['source_contract'],'frozen_pools_symbol':meta['frozen_pools_symbol'],'max_pool_records':MAX_RECORDS,'max_pool_bytes_total_per_observation':MAX_POOL_BYTES,'sample_period_s':.1,'overlay_work_phase_claim':'omitted: no authenticated current overlay binding','acceptance_owner':'root; all acceptance_pass fields remain false'}
 def capture_worker(proc):
  reader=None
  try:
   while not stop.is_set() or not still_queue.empty():
    try:wanted,requested=still_queue.get(timeout=.05)
    except queue.Empty:continue
    record={'phase':wanted,'requested_state':requested,'capture_status':'in-progress'};stills.append(record)
    if proc.poll() is not None:record.update(skipped='owned guest exited before capture',capture_status='skipped');continue
    try:
     if reader is None:reader=ram.OwnedRam(cap,proc.pid)
     actual=common(reader,symbols,abi);actual['placement_readiness']=placement_readiness(actual,placed_marker,mode);actual['room_save']=read_room_save(reader,symbols['_RoomData'],0x117,abi);record['capture_start_state']=actual
     if r117_capture_phase(actual)!=wanted:record.update(skipped='target source phase changed before VRAM read',capture_status='skipped');continue
     dest=cap/'event-stills'/wanted
     ram.capture_frames(cap,dest,actual);record.update(path=str(dest.relative_to(cap)),capture_end_monotonic=time.monotonic())
     try:
      after=common(reader,symbols,abi);after['placement_readiness']=placement_readiness(after,placed_marker,mode);after['room_save']=read_room_save(reader,symbols['_RoomData'],0x117,abi);record['capture_end_state']=after;record['source_phase_still_matches_after_capture']=r117_capture_phase(after)==wanted
     except (OSError,ValueError) as exc:record['capture_end_state_unknown']=str(exc)
     record['capture_status']='completed'
     (dest/'capture-binding.json').write_text(json.dumps(record,indent=2)+'\n')
    except Exception as exc:record.update(capture_error=repr(exc),capture_status='error')
  finally:
   if reader:reader.close()
 def observe(proc):
  nonlocal still_worker,placed_marker
  reader=None;onset=False;tail=Tail(cap/'run-output.txt')
  if still_enabled and mode=='r117':still_worker=threading.Thread(target=capture_worker,args=(proc,),daemon=True);still_worker.start()
  try:
   with (cap/'aud23-event-ram.jsonl').open('x') as out:
    while not stop.is_set() and proc.poll() is None:
     row={}
     try:
      for line in tail.poll():
       candidate=placement_marker(line,mode)
       if candidate is not None:placed_marker=candidate;markers.append({'host_s':round(time.monotonic()-t0,3),'line':line,'authenticated_fixture_placement':True})
       if 'warp: goto 0 at room frame' in line:
        onset=True;markers.append({'host_s':round(time.monotonic()-t0,3),'line':line})
      if reader is None:reader=ram.OwnedRam(cap,proc.pid)
      row=common(reader,symbols,abi);row['host_s']=round(time.monotonic()-t0,3);row['placement_readiness']=placement_readiness(row,placed_marker,mode)
      if mode=='r117' and row['room']=='117':row['room_save']=read_room_save(reader,symbols['_RoomData'],0x117,abi)
      if mode=='dam' and row['room']=='10c':
       row['area_onset_marker_observed']=onset;row['room_save']=read_room_save(reader,symbols['_RoomData'],0x10c,abi);row['pool']=read_pool(reader,symbols['_EmMgr'],abi,frozen_address)
      rows.append(row);out.write(json.dumps(row)+'\n');out.flush()
      wanted=still_budget.reserve(row) if still_enabled and mode=='r117' else None
      if wanted:still_queue.put_nowait((wanted,row.copy()))
     except (OSError,ValueError) as exc:
      row.update(host_s=round(time.monotonic()-t0,3),unknown=str(exc),diagnostics=getattr(exc,'diagnostics',{}));rows.append(row);out.write(json.dumps(row)+'\n');out.flush()
      if len(errors)<20:errors.append(row)
     stop.wait(.1)
  except Exception as exc:errors.append({'fatal':repr(exc)})
  finally:
   if reader:reader.close()
   if still_worker:still_worker.join(timeout=.5)
   receipt.update(stills_requested=still_enabled,maximum_stills=2,stills_queued=sorted(still_budget.phases),stills=stills,capture_worker_still_running=bool(still_worker and still_worker.is_alive()),pid=proc.pid,markers=markers,samples=len(rows),unknown_samples=sum('unknown' in r for r in rows),errors=errors,summary=r117_summary(rows) if mode=='r117' else dam_summary(rows))
   (cap/'aud23-event-observation.json').write_text(json.dumps(receipt,indent=2)+'\n')
 class ObservedPopen(original):
  def __init__(self,*a,**kw):
   nonlocal worker,guest
   cmd=a[0] if a else kw.get('args',[]);owned=isinstance(cmd,(list,tuple)) and pathlib.Path(str(cmd[0])).name.lower()=='flycast.exe'
   if owned and guest is not None:raise RuntimeError('second guest refused before spawn')
   super().__init__(*a,**kw)
   if owned:
    guest=self;worker=threading.Thread(target=observe,args=(self,),daemon=True);worker.start()
 subprocess.Popen=ObservedPopen
 try:
  sys.argv=[str(harness),*args];runpy.run_path(str(harness),run_name='__main__')
 finally:
  stop.set()
  if worker:worker.join(timeout=1)
if __name__=='__main__':main()
