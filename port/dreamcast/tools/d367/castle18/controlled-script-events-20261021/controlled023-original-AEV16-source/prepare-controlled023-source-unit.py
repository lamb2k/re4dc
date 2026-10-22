from pathlib import Path
import ast,hashlib,json,struct
L=Path(__file__).parent
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
old=L/'observe-controlled-ch32-door022.py'
assert sha(old)=='8ebb0f5d32620dcf7edfebc45ac7cda83d397116cb8d869da63ccfdece95b48d'
# This generator prepares source only. Exact target/native bindings are independently
# qualified from retained actual022 and selected assets before this unit is sealed.
q=json.loads((L/'controlled023-retained-AEV16-qualification.json').read_text())
assert q['state_sha256']=='b63e07f2ebb8be87be27e051d4580d28c878a0495348c5f99792ff2dcab4f16a'
assert q['AEV16']['enabled'] and q['AEV16']['type']==0 and q['AEV16']['trigger']==129 and q['AEV16']['checkFlag']==0
s=old.read_text().replace('door022','escape023').replace('DOOR022','ESCAPE023').replace('allocated022','allocated023').replace('>=5508','>=6612').replace('93fa4f5243a3c2ffbbaa45617ca046294b56274b17eaf62e1f3ab2ecb604339d',q['state_sha256'])
s=s.replace('k.OpenProcess.argtypes=', 'k.WriteProcessMemory.argtypes=[W.HANDLE,C.c_void_p,C.c_void_p,C.c_size_t,C.POINTER(C.c_size_t)];k.WriteProcessMemory.restype=W.BOOL\nk.OpenProcess.argtypes=',1)
s=s.replace("if no in [0,4,0xa]", "if no in [0,4,0xa,0x16,0x19,0x1a,0x1c,0x1d]")
s=s.replace("row['areas']=areas;", "row['areas']=areas;row['native_AEV16_hit']=bool(u32(sys+16)&(1<<9));row['native_AEV16_executed']=bool(u32(sys+48)&(1<<9));")
# Areas are numbered by original no; hit/exec arrays use no >> 5 with MSB first.
s=s.replace("bool(u32(sys+16)&(1<<9))", "bool(u32(sys+16)&0x200)").replace("bool(u32(sys+48)&(1<<9))", "bool(u32(sys+48)&0x200)")
s=s.replace("go2=w[1032:1056].hex(),", "go2=w[1032:1056].hex(),go3=w[1056:1080].hex(),")
s=s.replace("row['saved_RSF204']=next", "row['saved_RSF209']=next((struct.unpack_from('<I',tb,i*0xd8+4)[0]for i in range(nr)if tb[i*0xd8:i*0xd8+2]==b'\\x02\\x09'),None);row['saved_RSF204']=next")
s=s.replace("row.update(player_ptr=pl,", "row.update(native_Key64=list(struct.unpack('<3Q',read(0x8c3a948c+8,24))),native_idle=(read(pl+0xfc,2)==b'\\0\\0'and not(u32(pl+0x420)&2)),door_flags51cc=hex(u32(pg+0x51cc)),room_flag0=hex(u32(pg+0x503c)),player_ptr=pl,")
s=s.replace("row['actors']=actors;", "row['leader_actor_observations']=[a for a in actors if a['source_list']==0x7d];row['actors']=actors;")
# Native recipes in the qualification are pinned proofs, not offset guesses.
s=s.replace("row['actors']=actors;", "row['actors']=actors;lift_table=u32(0x8c3bdd64);lift_ptr=u32(lift_table+0xac*4)if inram(lift_table,250*4)else 0;row['liftAC']=dict(ptr=lift_ptr,position=list(struct.unpack('<3f',read(lift_ptr+0x94,12))),be_flag=hex(u32(lift_ptr+4)))if inram(lift_ptr,0x3d4)else None;")
a=s.index('WP=0x8c47fb58;');b=s.index('\ndef window_evidence(hwnd):',a)
logic='''WP=0x8c47fb58;COUNT=WP+1176;SLOT3=WP+1056
TARGET=TARGET_LITERAL
DESCRIPTOR=struct.pack('<I4f4B',0,*TARGET,0.,0,0,0,3)
WRITE_ALLOWLIST=[dict(address=hex(SLOT3),bytes=24),dict(address=hex(COUNT),bytes=4)]
QUALIFIED_AREA=AREA_LITERAL
INHERITED_GOTOS=GOTOS_LITERAL
CALLBACK_BYTES=bytes.fromhex(CALLBACK_LITERAL)

def native_neutral(row):
 keys=row.get('native_Key64')if row else None
 return isinstance(keys,list)and len(keys)==3 and all(isinstance(v,int)and v&0x80080000==0 for v in keys)

def original_area_ready(row):
 a=row.get('areas',{}).get('0x16',{})if row else {}
 return all(a.get(k)==QUALIFIED_AREA[k]for k in ['type','checkFlag','trigger','checkType','func','floor','height','quad'])and a.get('enabled')is True and row.get('AEV16_callback_code_exact')is True

def setup_ready(row,prepared=False):
 if not(row and row.get('live_native_code_anchors_verified')is True and row.get('room')=='0x209'and row.get('Part')==0 and row.get('previous_room')=='0x204'and row.get('phase')==[3,0]and row.get('Stop')=='0x0'and row.get('health',[0])[0]>0 and not(int(row.get('status1','0'),16)&0x10000000)and row.get('native_idle')is True and native_neutral(row)and original_area_ready(row)):return False
 w=row.get('warp',{})
 return w.get('flags')==[1,1,0,1,1]and w.get('name')=='castle21-CONTROLLED-ch32-drain0'and w.get('room')=='0x205'and w.get('rooms')==3 and w.get('max_entry')==3 and w.get('n_go')==3 and all(w.get('go'+str(i))==g for i,g in enumerate(INHERITED_GOTOS))and w.get('go3')==(DESCRIPTOR.hex()if prepared else '00'*24)and w.get('n_act')==0 and w.get('n_rsf')==0 and not w.get('has_trg')and not w.get('has_kill')

def exact_command_write(address,data):
 assert(address==SLOT3 and data==DESCRIPTOR)or(address==COUNT and data==struct.pack('<I',4)),'Only exact slot3 descriptor and count4 publication'
 check();assert memory_ready and age()<28 and shutil.disk_usage(D).free>=19394461696
 before=read(address,len(data));buf=C.create_string_buffer(data);got=C.c_size_t()
 receipt=dict(controlled_existing_rig_command_write=True,address=hex(address),before=before.hex(),after_requested=data.hex(),process_age=age());events.append(receipt)
 ok=bool(k.WriteProcessMemory(h,ram+address-0x8c000000,buf,len(data),C.byref(got)));receipt.update(api_ok=ok,bytes_written=got.value)
 assert ok and got.value==len(data),'Exact config write failed; no retry/rollback'
 receipt['observed_after']=read(address,len(data)).hex();assert receipt['observed_after']==data.hex()

def publish_existing_goto():
 check();row=sample()
 if not setup_ready(row):return False
 events.append(dict(immediate_command_recheck=row,write_allowlist=WRITE_ALLOWLIST,no_actor_room_or_outcome_writes=True))
 exact_command_write(SLOT3,DESCRIPTOR)
 row=sample();assert setup_ready(row,True)and u32(COUNT)==3,'Native admission changed before count; no retry/rollback'
 exact_command_write(COUNT,struct.pack('<I',4))
 assert u32(COUNT)==4
 events.append(dict(existing_goto_published=True,entry=3,count_published_last=True,sub=False,engine_owns_done=True,maximum_successful_bytes=28,no_max_entry_write=True))
 return True

def consumed_escape(row):
 try:g=bytes.fromhex(row.get('warp',{}).get('go3',''))
 except ValueError:return False
 return len(g)==24 and g[:21]==DESCRIPTOR[:21]and g[21]==1 and g[22:]==DESCRIPTOR[22:]
'''.replace('TARGET_LITERAL',repr(tuple(q['target']))).replace('AREA_LITERAL',repr(q['AEV16'])).replace('GOTOS_LITERAL',repr(q['inherited_gotos'])).replace('CALLBACK_LITERAL',repr(q['callback_bytes_hex']))
s=s[:a]+logic+s[b:]
s=s.replace("row['areas']=areas;", "row['AEV16_callback_code_exact']=read(QUALIFIED_AREA['func'],len(CALLBACK_BYTES))==CALLBACK_BYTES;row['areas']=areas;")
# Keep previously reviewed native input/focus/release helpers byte-for-byte. This
# automatic area trigger never invokes them; source unit injects zero key events.
s=s.replace("allocation['allow_debug_goto_command_writes']is False", "allocation['allow_debug_goto_command_writes']is True").replace("allocation['allow_owned_window_focus']is True", "allocation['allow_owned_window_focus']is False").replace("allocation['allow_scan_code_SendInput']is True", "allocation['allow_scan_code_SendInput']is False").replace("allocation['maximum_successful_command_bytes']==0", "allocation['maximum_successful_command_bytes']==28")
s=s.replace("allocation['exclusive_gui_input']is True", "allocation['exclusive_gui_input']is False")
s=s.replace("h=k.OpenProcess(0x1000|0x10|0x100000,", "h=k.OpenProcess(0x1000|0x10|0x20|0x8|0x100000,")
s=s.replace("previous_readable=None;readiness_recorded=False;action_blocked=False", "previous_readable=None;readiness_recorded=False;action_blocked=False;neutral_previous=None;neutral_ready=False;published=False;attempted_publication=False;cutC=False;cutD=False;returned=False;cutDframe=None;lift_initial=None;lift_peak=None")
a=s.index(" sent={2:False};");b=s.index(" with(cap/'controlled-escape023-observations.jsonl')",a)
s=s[:a]+" shots=set()\n events.append(dict(inherited_actual022=True,state_sha256='"+q['state_sha256']+"',preserve_injury=True,consolidated_AEV16=True,maximum_command_bytes=28,no_input=True))\n"+s[b:]
a=s.index('    stage=2\n');b=s.index('    labels=[]\n',a)
s=s[:a]+'''    neutral_ready=bool(memory_ready and native_neutral(row)and neutral_previous and row['frame']>neutral_previous['frame']and row['pg']==neutral_previous['pg'])
    neutral_previous=dict(frame=row['frame'],pg=row['pg'])if memory_ready and native_neutral(row)else None
    if neutral_ready and not attempted_publication and not published and age()<27 and setup_ready(row):
     attempted_publication=True
     events.append(dict(fresh_advancing_native64_neutral=row,no_key_forcing=True))
     if row.get('liftAC'):lift_initial=row['liftAC']['position'][1];lift_peak=lift_initial
     try:published=publish_existing_goto()
     except MemoryUnavailable as e:action_blocked=True;events.append(dict(publication_read_unavailable_no_retry=e.detail))
    if published and row['room']=='0x209'and row['phase']==[3,0]and row['previous_room']=='0x204'and row['Part']==0:
     if consumed_escape(row)and'placement'not in shots:shots.add('placement');events.append(dict(original_engine_goto_consumed=row))
     lift=row.get('liftAC')
     if lift:
      y=lift['position'][1]
      if lift_initial is None:lift_initial=y
      lift_peak=y if lift_peak is None else max(y,lift_peak)
     event_active=bool(int(row['status1'],16)&0x10000000)
     if event_active and row.get('camera_no')==0xc and not cutC:cutC=True;events.append(dict(original_escape_cameraC=row))
     if cutC and event_active and row.get('camera_no')==0xd and not cutD:cutD=True;cutDframe=row['frame'];events.append(dict(original_escape_cameraD=row,lift_initial=lift_initial,lift_peak=lift_peak))
     if cutD and not returned and not event_active and row['Stop']=='0x0'and row['frame']>cutDframe:returned=True;events.append(dict(original_escape_event_return=row,lift_initial=lift_initial,lift_peak=lift_peak,original_RSF1=bool((row.get('saved_RSF209')or 0)&0x40000000),original_door51cc=bool(int(row['door_flags51cc'],16)&0x80000),source_sequence_observed=True))
''' +s[b:]
a=s.index('    if cut3 and not cut2');b=s.index('    if age()>=36',a)
s=s[:a]+"    if cutC and not cutD and age()<35:labels.append('original-escape-cameraC')\n    if cutD and not returned and age()<36:labels.append('original-escape-cameraD')\n    if returned and age()<37:labels.append('original-escape-event-return')\n"+s[b:]
s=s.replace('"""CONTROLLED exact021state already209/nativephysicalDoor1ready: ordinarySendInputA thenoriginalleadercut. Zero game-memory writes/goto/replay; nativeaction replaces hostradius."""','"""SOURCE023 actual022 originalAEV16 consolidated escape. Existing position-only Goto slot3/count4 =28B; no input/outcome edits."""')
# Source fields intentionally removed rather than guessed; room_flag0 is not required.
s=s.replace("room_flag0=hex(u32(pg+0x503c)),",'')
compile(s,'observe-controlled-ch32-escape023.py','exec')
p=L/'observe-controlled-ch32-escape023.py';assert not p.exists();p.write_text(s,newline='\n')
print(json.dumps(dict(observer=str(p),sha256=sha(p),bytes=p.stat().st_size)))
