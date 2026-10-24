"""Bounded read-only aud23 event observer. Run only inside census-bound-run.py; no guest on import."""
import hashlib,importlib.util,json,math,os,pathlib,re,runpy,struct,subprocess,sys,threading,time
BACKEND=pathlib.Path(__file__).with_name('event-fixtures')/'stat_owned_ram.py'
spec=importlib.util.spec_from_file_location('aud23_owned_ram',BACKEND);ram=importlib.util.module_from_spec(spec);spec.loader.exec_module(ram)
MAX_RECORDS=512;MAX_POOL_BYTES=4*1024*1024;MAX_SAVE_BYTES=512*0xd8
class UnknownSample(ValueError):pass

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
 if meta.get('schema')!=1:raise UnknownSample('unsupported symbol schema')
 roles={'pG':'pointer_global','pPL':'pointer_global','_RoomData':'direct_object','_EmMgr':'direct_object'}
 rows=meta.get('programme_symbols',{})
 if set(rows)!=set(roles):raise UnknownSample('exact symbols missing/extra')
 out={}
 for name,role in roles.items():
  if rows[name].get('storage')!=role:raise UnknownSample('pointer/direct-object role mismatch: '+name)
  out[name]=int(rows[name]['address'],0);extent(out[name],4)
 return out

def read_room_save(reader,roomdata,room):
 # RoomData is the direct cRoomData object, never a pointer global.
 first=reader.read_pointer(roomdata,0x20);num=struct.unpack_from('<H',first,2)[0]
 buf,save=struct.unpack_from('<II',first,0x14)
 if not 0<num<=MAX_RECORDS:raise UnknownSample('room-save count outside bound')
 count=num*0xd8;extent(save,count);extent(buf,16+count)
 if count>MAX_SAVE_BYTES or save!=buf+16:raise UnknownSample('room-save extent/header mismatch')
 header=reader.read_pointer(buf,16)
 if struct.unpack_from('<II',header)!= (16+count,num):raise UnknownSample('room-save header size/count mismatch')
 data=reader.read_pointer(save,count)
 second=reader.read_pointer(roomdata,0x20)
 if first!=second or reader.read_pointer(buf,16)!=header:raise UnknownSample('room-save owner/header changed during read')
 wanted=bytes([room>>8,room&255]);hits=[i for i in range(num) if data[i*0xd8:i*0xd8+2]==wanted]
 if len(hits)!=1:raise UnknownSample('room-save record absent/duplicate')
 index=hits[0];address=save+index*0xd8;rec=data[index*0xd8:(index+1)*0xd8]
 # Recheck this record header around its aligned flag read; no guest function executes.
 check=reader.read_pointer(address,8)
 if check[:4]!=rec[:4]:raise UnknownSample('room-save record changed identity')
 return {'record':hex(address),'record_index':index,'records':num,'raw_id_bytes':wanted.hex(),'rsf':f'{struct.unpack_from("<I",check,4)[0]:08x}'}

def pool_header(raw):
 array,count,stride=struct.unpack_from('<III',raw)
 head=struct.unpack_from('<I',raw,0x10)[0]
 if not 0<count<=MAX_RECORDS or stride<0x39c or stride>0x10000 or stride%4:raise UnknownSample('pool count/stride outside bound')
 total=count*stride
 if total>MAX_POOL_BYTES:raise UnknownSample('whole pool exceeds read cap')
 extent(array,total)
 return array,count,stride,head

def chain_indices(header,data):
 array,count,stride,head=header;array_off=extent(array,count*stride);seen=set();order=[];p=head
 while p:
  physical=ram.ram_offset(p)
  if physical<array_off or physical>=array_off+count*stride or (physical-array_off)%stride:raise UnknownSample('alive link not a current whole pool element')
  index=(physical-array_off)//stride
  if index in seen or len(order)>=count:raise UnknownSample('alive list cycle/overrun')
  seen.add(index);order.append(index);p=struct.unpack_from('<I',data,index*stride+4)[0]
 return order

def actor_at(data,index,stride,array):
 off=index*stride;flags=struct.unpack_from('<I',data,off)[0];serial=struct.unpack_from('<I',data,off+0xf8)[0]
 return {'address':hex(array+off),'index':index,'serial':serial,'be_flag':f'{flags:08x}','alive':(flags&0x201)==1,'id':data[off+0x100],'kind':data[off+0x12e],'entry':data[off+0x398]}

def read_pool(reader,manager):
 # EmMgr is the direct cEmMgr object. Read bounded complete allocation twice.
 h1=reader.read_pointer(manager,0x34);a,n,stride,head=pool_header(h1)
 b1=reader.read_pointer(a,n*stride);h2=reader.read_pointer(manager,0x34)
 b2=reader.read_pointer(a,n*stride);h3=reader.read_pointer(manager,0x34)
 # maxAlive and diagnostic counters may change without ownership changing.
 key=lambda h:(h[:12],h[0x10:0x14])
 if key(h1)!=key(h2) or key(h1)!=key(h3):raise UnknownSample('pool allocation/head changed across two reads')
 indices1=chain_indices((a,n,stride,head),b1);indices2=chain_indices((a,n,stride,head),b2)
 if set(indices1)!=set(indices2):raise UnknownSample('alive membership changed across two reads')
 actors=[];unstable=[]
 for index in indices2:
  one=actor_at(b1,index,stride,a);two=actor_at(b2,index,stride,a)
  # Observe only Ganados, but reject identity changes of any potential target.
  target=lambda x:x['kind']==0 and 0x10<=x['id']<=0x20 and x['entry'] in [2,3,4]
  if not(target(one) or target(two)):continue
  if any(one[k]!=two[k] for k in ['serial','id','kind','entry','alive']) or not(one['alive'] and two['alive']):
   unstable.append({'index':index,'reason':'serial/class/list-entry/liveness changed or retired'});continue
  off=index*stride;view=ram.decode_model(b2[off:off+0x298]);two.update(view)
  p1=struct.unpack_from('<I',b1,off+0x1d8)[0];p2=int(two['pMotion'],16)
  two['motion_stable_during_pool_read']=p1==p2
  if p2 and p1==p2:
   try:two['motion_header_sha256']=hashlib.sha256(reader.read_pointer(p2,64)).hexdigest()
   except (OSError,ValueError) as exc:two['motion_header_unknown']=str(exc)
  actors.append(two)
 return {'array':hex(a),'count':n,'stride':stride,'bytes_each_read':n*stride,'active_members':len(indices2),'membership_double_read':True,'actors':actors,'unstable_targets':unstable,'target_sample_complete':not unstable,'lifetime_limit':'Stable pool membership and source serial within this sample are observational guards, not a durable owner-generation proof.'}

def common(reader,symbols):
 pg=reader.u32(symbols['pG']);extent(pg,0x51e8)
 player=reader.player(symbols['pPL'])
 sf1=reader.u32(pg+0x5010);frame=reader.u32(pg+0x51e4);room=struct.unpack('<H',reader.read_pointer(pg+0x4f9e,2))[0]
 if reader.u32(symbols['pG'])!=pg or reader.u32(symbols['pPL'])!=int(player['pPL'],16):raise UnknownSample('player/global pointer changed during sample')
 return {'player':player,'pG':hex(pg),'room':f'{room:03x}','SF1':f'{sf1:08x}','event_active':bool(sf1&0x10000000),'Frame_cnt':frame,'sample_monotonic':time.monotonic()}

def r117_summary(rows):
 baseline=False;started=False;last=None
 for row in rows:
  if row.get('unknown') or row.get('room')!='117' or 'room_save' not in row:continue
  rsf=int(row['room_save']['rsf'],16)
  if not started and (rsf&0x60000000)==0 and not row['event_active']:baseline=True
  if baseline and (rsf&0x20000000) and row['event_active']:started=True
  pos=row['player']['pos']
  if baseline and started and (rsf&0x60000000)==0x40000000 and not row['event_active'] and abs(pos[0]+2910)<100 and abs(pos[1]-4000)<100 and abs(pos[2]-6610)<100:last=row
 return {'baseline_unsolved_observed':baseline,'started_in_event_observed':started,'solved_disarmed_event_clear_endpose_observed':last is not None,'source_state_sequence_observed':bool(baseline and started and last),'final_witness':last,'acceptance_pass':False,'overlay_work_phase_claim':'omitted; exact current st1_3 work binding not authenticated','limits':'Root must inspect actual inputs/rendered gate and retain exact target/data binding; no allocation-failure injection or physical-console acceptance.'}

def dam_summary(rows):
 baseline=False;first=None;progress=[];previous={};end=None;seen_entry2=False
 for row in rows:
  if row.get('unknown') or row.get('room')!='10c':continue
  pool=row.get('pool')
  if not pool or not pool.get('target_sample_complete'):continue
  entry2=[a for a in pool['actors'] if a['entry']==2 and a['id']==0x12 and a['kind']==0 and a['alive']]
  if not seen_entry2 and not row['event_active'] and not entry2:baseline=True
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
 meta=json.loads(manifest.read_text());symbols=symbols_from_manifest(meta)
 if digest(BACKEND)!=meta['ram_backend_sha256']:raise RuntimeError('RAM backend digest mismatch')
 if digest(harness)!=meta['source_sha256']['port/dreamcast/tools/d367/fullplay/fp_run.py']:raise RuntimeError('frozen fp_run source mismatch')
 if digest(meta['program_elf_windows'])!=meta['program_elf_sha256']:raise RuntimeError('bound ELF changed')
 base=pathlib.Path(args[args.index('--base')+1]);cap=pathlib.Path(args[args.index('--cap')+1]);base_meta=json.loads((base/'base.json').read_text())
 if base_meta.get('elf')!=meta['program_elf']:raise RuntimeError('base is not bound to this exact programme ELF')
 stop=threading.Event();worker=None;guest=None;rows=[];markers=[];errors=[];t0=time.monotonic()
 receipt={'mode':mode,'source':meta['source'],'program_elf_sha256':meta['program_elf_sha256'],'symbol_manifest_sha256':digest(manifest),'symbol_manifest':str(manifest),'symbols':meta['programme_symbols'],'backend_sha256':digest(BACKEND),'read_only':True,'max_pool_records':MAX_RECORDS,'max_pool_bytes_each_read':MAX_POOL_BYTES,'sample_period_s':.1,'overlay_work_phase_claim':'omitted: no authenticated current overlay binding','acceptance_owner':'root; all acceptance_pass fields remain false'}
 def observe(proc):
  reader=None;onset=False;tail=Tail(cap/'run-output.txt')
  try:
   with (cap/'aud23-event-ram.jsonl').open('x') as out:
    while not stop.is_set() and proc.poll() is None:
     try:
      for line in tail.poll():
       if 'warp: goto 0 at room frame' in line:
        onset=True;markers.append({'host_s':round(time.monotonic()-t0,3),'line':line})
      if reader is None:reader=ram.OwnedRam(cap,proc.pid)
      row=common(reader,symbols);row['host_s']=round(time.monotonic()-t0,3)
      if mode=='r117' and row['room']=='117':row['room_save']=read_room_save(reader,symbols['_RoomData'],0x117)
      if mode=='dam' and row['room']=='10c':
       row['area_onset_marker_observed']=onset;row['room_save']=read_room_save(reader,symbols['_RoomData'],0x10c);row['pool']=read_pool(reader,symbols['_EmMgr'])
      rows.append(row);out.write(json.dumps(row)+'\n');out.flush()
     except (OSError,ValueError) as exc:
      row={'host_s':round(time.monotonic()-t0,3),'unknown':str(exc)};rows.append(row);out.write(json.dumps(row)+'\n');out.flush()
      if len(errors)<20:errors.append(row)
     stop.wait(.1)
  except Exception as exc:errors.append({'fatal':repr(exc)})
  finally:
   if reader:reader.close()
   receipt.update(pid=proc.pid,markers=markers,samples=len(rows),unknown_samples=sum('unknown' in r for r in rows),errors=errors,summary=r117_summary(rows) if mode=='r117' else dam_summary(rows))
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
  if worker:worker.join(timeout=3)
if __name__=='__main__':main()
