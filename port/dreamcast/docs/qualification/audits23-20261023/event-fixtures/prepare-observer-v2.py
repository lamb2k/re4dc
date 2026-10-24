from pathlib import Path
import json,hashlib
lane=Path(r'C:\Game Dev\Emulators\codex-lanes\audits23');source=(lane/'aud23-event-observer.py').read_text();source=source.replace('import hashlib,importlib.util,json,math,os,pathlib,re,runpy,struct,subprocess,sys,threading,time','import hashlib,importlib.util,json,math,os,pathlib,queue,re,runpy,struct,subprocess,sys,threading,time')
source=source.replace('class UnknownSample(ValueError):pass', '''class UnknownSample(ValueError):
 def __init__(self,message,diagnostics=None):
  super().__init__(message);self.diagnostics=diagnostics or {}
''')
pos=source.index('\ndef read_room_save(')
source=source[:pos]+'''
def validate_abi(meta):
 if meta.get('schema')!=2:raise UnknownSample('v2 compiler ABI manifest required; no v1 fallback')
 path=pathlib.Path(meta['target_abi_receipt']);raw=path.read_bytes()
 if hashlib.sha256(raw).hexdigest()!=meta['target_abi_receipt_sha256']:raise UnknownSample('target ABI receipt digest mismatch')
 proof=json.loads(raw);abi=proof['layout']
 if proof.get('schema')!=2 or proof.get('derivation')!='actual compiler builtin_offsetof/sizeof constant section, never source comments or synthetic host layout':raise UnknownSample('ABI derivation missing')
 if proof.get('elf_sha256')!=meta['program_elf_sha256'] or proof.get('source')!=meta['source']:raise UnknownSample('ABI receipt belongs to another exact programme')
 if abi!=meta.get('target_layout'):raise UnknownSample('manifest/compiler constant disagreement')
 if abi.get('magic')!=0x32494241 or abi.get('schema')!=2 or abi.get('pointer_bytes')!=4 or abi.get('u32_bytes')!=4:raise UnknownSample('unsupported target words')
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
 return abi
''' +source[pos:]
start=source.index('\ndef read_room_save(');end=source.index('\ndef pool_header(',start)
source=source[:start]+'''
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
''' +source[end:]
start=source.index('\ndef pool_header(');end=source.index('\ndef common(',start)
source=source[:start]+'''
def raw_pool_fields(raw,abi):
 return {name:(hex(struct.unpack_from('<I',raw,abi['manager.'+name])[0]) if name in ['pArray','pAlive'] else struct.unpack_from('<I',raw,abi['manager.'+name])[0]) for name in ['pArray','nArray','stride','pAlive','Guid']}
def pool_header(raw,abi):
 fields=raw_pool_fields(raw,abi);array=int(fields['pArray'],16);count=fields['nArray'];stride=fields['stride'];head=int(fields['pAlive'],16)
 if not 0<count<=MAX_RECORDS or stride!=abi['actor.sizeof'] or stride%4:raise UnknownSample('pool count/stride outside exact compiler ABI bound')
 if count*stride>MAX_POOL_BYTES:raise UnknownSample('whole pool exceeds read cap')
 extent(array,count*stride);return array,count,stride,head

def chain_indices(header,data,abi):
 array,count,stride,head=header;array_off=extent(array,count*stride);seen=set();order=[];p=head
 while p:
  physical=ram.ram_offset(p)
  if physical<array_off or physical>=array_off+count*stride or (physical-array_off)%stride:raise UnknownSample('alive link not a current whole pool element')
  index=(physical-array_off)//stride
  if index in seen or len(order)>=count:raise UnknownSample('alive list cycle/overrun')
  seen.add(index);order.append(index);p=struct.unpack_from('<I',data,index*stride+abi['actor.pNext'])[0]
 return order

def actor_at(data,index,stride,array,abi):
 off=index*stride;flags=struct.unpack_from('<I',data,off+abi['actor.be_flag'])[0];serial=struct.unpack_from('<I',data,off+abi['actor.serial'])[0]
 return {'address':hex(array+off),'index':index,'serial':serial,'be_flag':f'{flags:08x}','alive':(flags&0x201)==1,'id':data[off+abi['actor.id']],'kind':data[off+abi['actor.kindid']],'entry':data[off+abi['actor.emset_no']]}

def read_pool(reader,manager,abi):
 raw={};parsed={}
 try:
  h1=reader.read_pointer(manager,abi['manager.sizeof']);raw['before']=h1.hex();parsed['before']=raw_pool_fields(h1,abi)
  header=pool_header(h1,abi);a,n,stride,head=header
  b1=reader.read_pointer(a,n*stride);h2=reader.read_pointer(manager,abi['manager.sizeof']);raw['between']=h2.hex();parsed['between']=raw_pool_fields(h2,abi)
  b2=reader.read_pointer(a,n*stride);h3=reader.read_pointer(manager,abi['manager.sizeof']);raw['after']=h3.hex();parsed['after']=raw_pool_fields(h3,abi)
  if pool_header(h2,abi)!=header or pool_header(h3,abi)!=header:raise UnknownSample('pool allocation/head changed across two reads')
  indices1=chain_indices(header,b1,abi);indices2=chain_indices(header,b2,abi)
  if set(indices1)!=set(indices2):raise UnknownSample('alive membership changed across two reads')
  actors=[];unstable=[]
  for index in indices2:
   one=actor_at(b1,index,stride,a,abi);two=actor_at(b2,index,stride,a,abi)
   target=lambda x:x['kind']==0 and 0x10<=x['id']<=0x20 and x['entry'] in [2,3,4]
   if not(target(one) or target(two)):continue
   if any(one[k]!=two[k] for k in ['serial','id','kind','entry','alive']) or not(one['alive'] and two['alive']):
    unstable.append({'index':index,'reason':'serial/class/list-entry/liveness changed or retired'});continue
   off=index*stride;two.update(ram.decode_model(b2[off:off+0x298]));p1=struct.unpack_from('<I',b1,off+abi['actor.pMotion'])[0];p2=int(two['pMotion'],16);two['motion_stable_during_pool_read']=p1==p2
   if p2 and p1==p2:
    try:two['motion_header_sha256']=hashlib.sha256(reader.read_pointer(p2,64)).hexdigest()
    except (OSError,ValueError) as exc:two['motion_header_unknown']=str(exc)
   actors.append(two)
  return {'array':hex(a),'count':n,'stride':stride,'bytes_each_read':n*stride,'active_members':len(indices2),'membership_double_read':True,'actors':actors,'unstable_targets':unstable,'target_sample_complete':not unstable,'raw_pool_headers':raw,'parsed_pool_headers':parsed,'compiler_layout_used':True,'lifetime_limit':'Within-sample pool association and serial guards are not a durable owner-generation proof.'}
 except (OSError,ValueError) as exc:
  raise UnknownSample(str(exc),{'manager_address':hex(manager),'raw_pool_headers':raw,'parsed_pool_headers':parsed,'compiler_manager_offsets':{k:v for k,v in abi.items() if k.startswith('manager.')}}) from exc
''' +source[end:]
source=source.replace('def common(reader,symbols):','def common(reader,symbols,abi):').replace("reader.u32(pg+0x5010)","reader.u32(pg+abi['global.SF1'])").replace("reader.u32(pg+0x51e4)","reader.u32(pg+abi['global.Frame_cnt'])").replace("reader.read_pointer(pg+0x4f9e,2)","reader.read_pointer(pg+abi['global.room_id'],2)")
source=source.replace("if meta.get('schema')!=1:raise UnknownSample('unsupported symbol schema')","if meta.get('schema')!=2:raise UnknownSample('v2 symbol and compiler ABI schema required')")
source=source.replace("meta=json.loads(manifest.read_text());symbols=symbols_from_manifest(meta)","meta=json.loads(manifest.read_text());symbols=symbols_from_manifest(meta);abi=validate_abi(meta)")
source=source.replace("row=common(reader,symbols);", "row=common(reader,symbols,abi);").replace("read_room_save(reader,symbols['_RoomData'],0x117)","read_room_save(reader,symbols['_RoomData'],0x117,abi)").replace("read_room_save(reader,symbols['_RoomData'],0x10c)","read_room_save(reader,symbols['_RoomData'],0x10c,abi)").replace("read_pool(reader,symbols['_EmMgr'])","read_pool(reader,symbols['_EmMgr'],abi)")
source=source.replace("row={'host_s':round(time.monotonic()-t0,3),'unknown':str(exc)}", "row={'host_s':round(time.monotonic()-t0,3),'unknown':str(exc),'diagnostics':getattr(exc,'diagnostics',{})}")
source=source.replace("'max_pool_records':MAX_RECORDS", "'observer_version':2,'target_abi_receipt_sha256':meta['target_abi_receipt_sha256'],'target_layout':abi,'max_pool_records':MAX_RECORDS")
# Optional bounded asynchronous stills. Fresh state is revalidated immediately before VRAM read.
source=source.replace("stop=threading.Event();worker=None;guest=None;rows=[];markers=[];errors=[];t0=time.monotonic()", "stop=threading.Event();worker=None;guest=None;rows=[];markers=[];errors=[];t0=time.monotonic();still_enabled=os.environ.get('AUD23_CAPTURE_STILLS')=='1';still_queue=queue.Queue(maxsize=2);still_phases=set();stills=[];still_worker=None")
needle=' def observe(proc):\n'
insert=''' def phase(row):
  if row.get('room')!='117' or 'room_save' not in row or row.get('unknown'):return None
  rsf=int(row['room_save']['rsf'],16)
  if (rsf&0x60000000)==0 and not row['event_active']:return 'unsolved-baseline'
  pos=row['player']['pos']
  if (rsf&0x60000000)==0x40000000 and not row['event_active'] and abs(pos[0]+2910)<100 and abs(pos[1]-4000)<100 and abs(pos[2]-6610)<100:return 'solved-disarmed-event-clear'
  return None
 def capture_worker(proc):
  reader=None
  try:
   while not stop.is_set() or not still_queue.empty():
    try:wanted,requested=still_queue.get(timeout=.05)
    except queue.Empty:continue
    record={'phase':wanted,'requested_state':requested}
    if proc.poll() is not None:record['skipped']='owned guest exited before capture';stills.append(record);continue
    try:
     if reader is None:reader=ram.OwnedRam(cap,proc.pid)
     actual=common(reader,symbols,abi);actual['room_save']=read_room_save(reader,symbols['_RoomData'],0x117,abi);record['capture_start_state']=actual
     if phase(actual)!=wanted:record['skipped']='target source phase changed before VRAM read';stills.append(record);continue
     dest=cap/'event-stills'/wanted
     ram.capture_frames(cap,dest,actual);record.update(path=str(dest.relative_to(cap)),capture_end_monotonic=time.monotonic())
     (dest/'capture-binding.json').write_text(json.dumps(record,indent=2)+'\\n')
    except Exception as exc:record['capture_error']=repr(exc)
    stills.append(record)
  finally:
   if reader:reader.close()
'''
source=source.replace(needle,insert+needle)
source=source.replace("  reader=None;onset=False;tail=Tail(cap/'run-output.txt')", "  nonlocal still_worker\n  reader=None;onset=False;tail=Tail(cap/'run-output.txt')\n  if still_enabled and mode=='r117':still_worker=threading.Thread(target=capture_worker,args=(proc,),daemon=True);still_worker.start()")
source=source.replace("      rows.append(row);out.write(json.dumps(row)+'\\n');out.flush()", "      rows.append(row);out.write(json.dumps(row)+'\\n');out.flush()\n      wanted=phase(row) if still_enabled and mode=='r117' else None\n      if wanted and wanted not in still_phases and len(still_phases)<2:\n       still_phases.add(wanted);still_queue.put_nowait((wanted,row.copy()))")
source=source.replace("   receipt.update(pid=proc.pid", "   if still_worker:still_worker.join(timeout=.5)\n   receipt.update(stills_requested=still_enabled,maximum_stills=2,stills=stills,capture_worker_still_running=bool(still_worker and still_worker.is_alive()),pid=proc.pid")
source=source.replace("if worker:worker.join(timeout=3)","if worker:worker.join(timeout=1)")
source=source.replace('Bounded read-only aud23 event observer.','V2 compiler-ABI-bound read-only aud23 event observer.')
out=lane/'aud23-event-observer-v2.py';assert not out.exists();out.write_text(source)
for arm,old,abi_name,new in [('on','on-5e4d-symbols.json','target-abi-on-v2.json','on-5e4d-symbols-v2.json'),('off','off-control-2a-symbols.json','target-abi-off-v2.json','off-control-2a-symbols-v2.json')]:
 p=lane/'event-fixtures'/abi_name;proof=json.loads(p.read_text());meta=json.loads((lane/'event-fixtures'/old).read_text());meta.update(schema=2,target_abi_receipt=str(p),target_abi_receipt_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),target_layout=proof['layout'],observer_version=2)
 dest=lane/'event-fixtures'/new;assert not dest.exists();dest.write_text(json.dumps(meta,indent=2)+'\n')
print('Prepared new v2 observer + appended compiler-bound symbol manifests; v1 untouched.')
