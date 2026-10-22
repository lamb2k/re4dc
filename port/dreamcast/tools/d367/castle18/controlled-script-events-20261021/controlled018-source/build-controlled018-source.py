from pathlib import Path
import json,struct,hashlib
L=Path(__file__).parent
p=L/'observe-controlled-ch32-door018.py';s=(L/'observe-controlled-ch32-door017.py').read_text();s=s.replace('door017','door018').replace('DOOR017','DOOR018').replace('allocated017','allocated018')
s=s.replace('CONTROLLED exact016state continuation: existing DBG_WARP Goto command setup, ordinary native Door0 to204Part1; no actor/room/outcome memory writes.','CONTROLLED exact017state: existing Goto slots/current-entry admission only; native204Door4 to209, physicalDoor1 then original leader cut. No actor/room/outcome writes.')
s=s.replace("['0x205','0x204']","['0x204','0x209']").replace('>=1769','>=2604').replace('room not in [0x205,0x204]','room not in [0x204,0x209]')
s=s.replace('0x8c26cf88,0x8c14a95c]','0x8c26cf88,0x8c14a95c,0x8c0bc300,0x8c0bc384]')
s=s.replace('if no in [0,3,4,7,8,0x11,0x15,0x1b]','if no in [0,4,0xa]')
s=s.replace("enabled=bool(q[0x34]&1),type=", "floor=struct.unpack_from('<f',q,8)[0],height=struct.unpack_from('<f',q,12)[0],enabled=bool(q[0x34]&1),type=")
a=s.index(" row['areas']=areas;");b=s.index('\n act=read',a);s=s[:a]+" row['areas']=areas;row['native_AEV04_clipped_hit']=bool(u32(sys+16)&0x08000000);row['native_AEV0A_clipped_hit']=bool(u32(sys+16)&0x00200000);row['native_AEV0A_executed']=bool(u32(sys+48)&0x00200000);row['camera_no']=struct.unpack('<b',read(0x8c3949a4+0x692,1))[0]"+s[b:]
s=s.replace("go0=w[984:1008].hex(),n_act=", "go0=w[984:1008].hex(),go1=w[1008:1032].hex(),go2=w[1032:1056].hex(),n_act=")
a=s.index("  seen.add(p);b=read(p,0x3c8);");b=s.index(" if stamp!=",a)
s=s[:a]+'''  seen.add(p);b=read(p,0x3c8);actor=dict(ptr=hex(p),id=b[0x100],type=b[0x101],source_list=b[0x398],hp=struct.unpack_from('<h',b,0x320)[0],native_status=hex(struct.unpack_from('<I',b,0x3c4)[0]),be_flag=hex(struct.unpack_from('<I',b,4)[0]),routines=list(b[0xfc:0x100]))
  if actor['id']==0x41:
   b=read(p,0x820);actor.update(flag=hex(struct.unpack_from('<I',b,0x3c8)[0]),position=list(struct.unpack_from('<3f',b,0x94)),Etc_no=b[0x81f],door_work_flags=hex(struct.unpack_from('<I',b,0x3e0)[0]),base_dir=struct.unpack_from('<f',b,0x778)[0],base_matrix=list(struct.unpack_from('<12f',b,0x77c)),base_inverse=list(struct.unpack_from('<12f',b,0x7ac)),key_flag=struct.unpack_from('<I',b,0x7dc)[0],open_flag=b[0x81d])
  actors.append(actor);p=struct.unpack_from('<I',b,8)[0]
 row['actors']=actors;row['physical_doors1']=[v for v in actors if v['id']==0x41 and v.get('Etc_no')==1]
'''+s[b:]
a=s.index('WP=0x8c47fb58;');b=s.index('def pulse_door():',a)
s=s[:a]+'''WP=0x8c47fb58;COUNT=WP+1176;MAX_ENTRY=WP+1630
GO0_DONE=bytes.fromhex('00000000a894e4454f331c46025e27470000000001010001')
TARGET1=(-11179.9853515625,6000.99853515625,-28483.38525390625)
TARGET2=(-16150.030113227178,2001.,13499.981467821544)
STAGES={1:dict(room='0x204',entry=2,address=WP+1008,descriptor=struct.pack('<I4f4B',0,*TARGET1,0.,1,0,0,2)),2:dict(room='0x209',entry=3,address=WP+1032,descriptor=struct.pack('<I4f4B',0,*TARGET2,1.5707499980926514,1,0,0,3))}
WRITE_ALLOWLIST=[{'address':hex(STAGES[1]['address']),'bytes':24},{'address':hex(STAGES[2]['address']),'bytes':24},{'address':hex(MAX_ENTRY),'bytes':1},{'address':hex(COUNT),'bytes':4}]

def freeplay_ready(row,room):
 return bool(row and row['room']==room and row['phase']==[3,0]and row['health'][0]>0 and row.get('live_native_code_anchors_verified')is True and row['Stop']=='0x0'and not(int(row['status1'],16)&0x10000000)and not(int(row['Key_on'],16)&0x80080000))

def consumed(w,stage):
 try:g=bytes.fromhex(w.get('go'+str(stage),''));d=STAGES[stage]['descriptor']
 except (ValueError,KeyError):return False
 return len(g)==24 and g[:21]==d[:21]and g[21]==1 and g[22:]==d[22:]

def setup_ready(row,stage,prepared=0):
 c=STAGES[stage];w=row.get('warp',{})if row else {};oldentry=c['entry']-1
 if not freeplay_ready(row,c['room']):return False
 if stage==1 and not(row.get('Part')==1 and row.get('previous_room')=='0x205'):return False
 if stage==2 and not(row.get('Part')==0 and row.get('previous_room')=='0x204'and consumed(w,1)):return False
 return w.get('flags')==[1,1,0,1,1]and w.get('name')=='castle21-CONTROLLED-ch32-drain0'and w.get('room')=='0x205'and w.get('rooms')==c['entry']and w.get('max_entry')==(c['entry']if prepared==2 else oldentry)and w.get('n_go')==stage and w.get('go0')==GO0_DONE.hex()and w.get('go'+str(stage))==('00'*24 if not prepared else c['descriptor'].hex())and(stage!=1 or w.get('go2')=='00'*24)and w.get('n_act')==0 and w.get('n_rsf')==0 and not w.get('has_trg')and not w.get('has_kill')

def exact_command_write(address,data,stage):
 c=STAGES[stage]
 assert (address==c['address']and data==c['descriptor'])or(address==MAX_ENTRY and data==bytes([c['entry']]))or(address==COUNT and data==struct.pack('<I',stage+1)),'Only exact current-stage config writes'
 check();assert memory_ready and age()<29 and shutil.disk_usage(D).free>=18*1024**3+64*1024**2
 before=read(address,len(data));buf=C.create_string_buffer(data);got=C.c_size_t()
 receipt=dict(controlled_existing_rig_command_write=True,stage=stage,address=hex(address),before=before.hex(),after_requested=data.hex(),process_age=age());events.append(receipt)
 ok=bool(k.WriteProcessMemory(h,ram+address-0x8c000000,buf,len(data),C.byref(got)));receipt.update(api_ok=ok,bytes_written=got.value)
 assert ok and got.value==len(data),'Exact config write failed; no retry/rollback'
 receipt['observed_after']=read(address,len(data)).hex()

def publish_existing_goto(stage):
 check();row=sample();c=STAGES[stage]
 if not setup_ready(row,stage):return False
 events.append(dict(immediate_command_recheck=row,stage=stage,write_allowlist=WRITE_ALLOWLIST,no_actor_room_or_outcome_writes=True))
 exact_command_write(c['address'],c['descriptor'],stage)
 assert read(c['address'],24)==c['descriptor']and u32(COUNT)==stage,'Unpublished descriptor verification failed'
 row=sample();assert setup_ready(row,stage,1),'State changed before entry admission; no retry/rollback'
 exact_command_write(MAX_ENTRY,bytes([c['entry']]),stage)
 row=sample();assert setup_ready(row,stage,2),'State changed before count publication; no retry/rollback'
 exact_command_write(COUNT,struct.pack('<I',stage+1),stage)
 assert u32(COUNT)==stage+1,'Command publication not observed'
 events.append(dict(existing_goto_published=True,stage=stage,process_age=age(),entry=c['entry'],sub=False,count_published_last=True,engine_owns_done=True))
 return True

def pose_matches(row,stage):
 target=struct.unpack_from('<3f',STAGES[stage]['descriptor'],4);actual=row.get('player_pos',[])
 return len(actual)==3 and all(math.isfinite(v)for v in actual)and sum((actual[i]-target[i])**2 for i in range(3))<150**2

def door_ready(row,stage):
 if not freeplay_ready(row,STAGES[stage]['room'])or not consumed(row.get('warp',{}),stage)or not pose_matches(row,stage):return False
 act=row.get('action',{});w=row['warp']
 if w.get('n_go')!=stage+1 or w.get('max_entry')!=STAGES[stage]['entry']or w.get('rooms')!=STAGES[stage]['entry']or act.get('active')!=1:return False
 if stage==1:
  a=row.get('areas',{}).get('0x4',{});d=a.get('door',{})
  return row.get('native_AEV04_clipped_hit')is True and a.get('enabled')and a.get('type')==1 and a.get('func')==0 and a.get('checkFlag')==1 and a.get('trigger')==8 and a.get('checkType')==1 and d.get('destination')=='0x209'and d.get('Part')==0 and d.get('lockType')==0 and d.get('lockFlag')==0 and d.get('callback')=='0x0'and any(v.get('arg')==a.get('ptr')and v.get('kind')==0x10 and v.get('button')==1 and v.get('func')==0x8c14a95c and v.get('type')==2 and v.get('d')==row.get('player_ptr')for v in act.get('work',[]))
 doors=row.get('physical_doors1',[]);a=row.get('areas',{}).get('0xa',{})
 if len(doors)!=1 or a.get('type')!=2 or a.get('func',0)==0:return False
 d=doors[0]
 return d.get('type')==1 and d.get('hp',0)>0 and not(int(d['flag'],16)&0x30000000)and int(d['door_work_flags'],16)&1==0 and d.get('key_flag')==0x36 and all(math.isfinite(v)for v in d.get('position',[]))and len(d.get('position',[]))==3 and sum((d['position'][i]-[-15750.,2000.,12850.][i])**2 for i in range(3))<10**2 and any(v.get('arg')==int(d['ptr'],16)and v.get('kind')==0x10 and v.get('slot')==5 and v.get('button')==1 and v.get('func')in[0x8c0bc300,0x8c0bc384]and v.get('type')==0 and v.get('d')==0 and v.get('flags')==0 for v in act.get('work',[]))

'''+s[b:]
s=s.replace('def pulse_door():','def pulse_door(stage):').replace('age()>=28 or not door_ready(row)','age()>=32 or not door_ready(row,stage)').replace('memory_ready and age()<28','memory_ready and age()<32').replace('if not door_ready(row):return False','if not door_ready(row,stage):return False')
s=s.replace("dict(immediate_native_door_A_recheck=row)","dict(immediate_native_door_A_recheck=row,stage=stage)").replace("ordinary_owned_UI_pulse='native-upper-Door0-A'","ordinary_owned_UI_pulse=('native204-Door4-A'if stage==1 else'native209-physicalDoor1-A'),stage=stage")
s=s.replace("scope='CONTROLLED exact015state existingrig goto placement then nativeDoor0/204Part1. Debugcommand setup is separate from originalexit/event outcomes.'","scope='CONTROLLED actual017state; existing config command setup separate from original204Door4/209physicalDoor1/leader-event outputs.'")
# Allocation comparison is exact addresses/sizes; source candidate cannot launch without root consent.
a=s.index(" and allocation['write_allowlist']==[");b=s.index(", 'Exact root-owned debug",a);s=s[:a]+" and allocation['write_allowlist']==WRITE_ALLOWLIST"+s[b:]
s=s.replace('Exact015 fullstate continuation','Exact017 fullstate continuation')
a=s.index(' published=False;');b=s.index(' if k.WaitForSingleObject(h,0)==258:close()',a)
s=s[:a]+''' published={1:False,2:False};sent={1:False,2:False};placed={1:False,2:False};entry=False;door_open=False;cut3=False;cut2=False;returned=False;shots=set();cut2frame=None
 events.append(dict(inherited017_firstcut_return=True,state_sha256='1b1485784a8c796fbaad18573002ae353f75d9b67c0b4b156e1724bf296ac04b',no_replay_015_drain_or_017_firstcut=True,controlled_setup_maximum_successful_bytes=58))
 with(cap/'controlled-door018-observations.jsonl').open('x')as out:
  while k.WaitForSingleObject(h,0)==258 and age()<39:
   check()
   if not mapping_ready:time.sleep(.03);continue
   try:row=sample()
   except MemoryUnavailable:
    previous_readable=None;time.sleep(.03);continue
   if row:
    memory_ready=readable_sequence(row,previous_readable,ram)
    previous_readable=dict(pg=row['pg'],frame=row['frame'],RAM_base=ram)if row.get('live_native_code_anchors_verified')and row['phase']==[3,0]else None
    if memory_ready and not readiness_recorded:
     try:probe=read(0x8c2e91dc,4)
     except MemoryUnavailable:previous_readable=None;time.sleep(.03);continue
     if struct.unpack('<I',probe)[0]!=row['pg']:memory_ready=False;previous_readable=None;continue
     readiness_recorded=True;events.append(dict(initial_readable_native_sequence=row,RAM_base=hex(ram),no_inputs_before_readiness=True,exact_successful_pG_probe=dict(guest_address='0x8c2e91dc',host_address=hex(ram+0x2e91dc),requested_bytes=4,api_ok=True,bytes_read=4,data_hex=probe.hex(),process_identity=owner)))
    last=row;out.write(json.dumps(row)+'\\n');out.flush()
    for stage in [1,2]:
     # Stage2 is not even offered before the actual original209 load has been observed.
     eligible=stage==1 or entry
     if eligible and memory_ready and not action_blocked and not published[stage]and age()<(18 if stage==1 else 28)and setup_ready(row,stage):
      try:published[stage]=publish_existing_goto(stage)
      except MemoryUnavailable as e:action_blocked=True;events.append(dict(command_read_unavailable_no_retry=e.detail,stage=stage))
     if published[stage]and not placed[stage]and row.get('room')==STAGES[stage]['room']and consumed(row.get('warp',{}),stage)and pose_matches(row,stage):
      placed[stage]=True;events.append(dict(native_existing_goto_consumed=row,stage=stage))
     if memory_ready and not action_blocked and placed[stage]and not sent[stage]and age()<32 and door_ready(row,stage):
      try:sent[stage]=pulse_door(stage)
      except MemoryUnavailable as e:action_blocked=True;events.append(dict(input_read_unavailable_no_retry=e.detail,stage=stage))
    if sent[1]and row['phase'][0]==4 and row['next_room']=='0x209'and row['next_point']==0 and'request'not in shots:
     shots.add('request');events.append(dict(original_native_209_door_request=row))
    if sent[1]and row['room']=='0x209'and row['phase']==[3,0]and row['previous_room']=='0x204'and row['Part']==0:
     if not entry:entry=True;events.append(dict(actual_209_entry=row))
     if row.get('native_AEV0A_executed')and'aev0a'not in shots:shots.add('aev0a');events.append(dict(original_AEV0A_execution_observed=row))
     doors=row.get('physical_doors1',[])
     if sent[2]and len(doors)==1 and int(doors[0]['flag'],16)&0x10000000 and not door_open:door_open=True;events.append(dict(original_physicalDoor1_open_flag=row))
     event_active=bool(int(row['status1'],16)&0x10000000)
     if door_open and event_active and row.get('camera_no')==3 and not cut3:cut3=True;events.append(dict(original_leader_cut_camera3=row))
     if cut3 and event_active and row.get('camera_no')==2 and not cut2:cut2=True;cut2frame=row['frame'];events.append(dict(original_leader_cut_camera2=row))
     if cut2 and not returned and not event_active and row['Stop']=='0x0'and row['frame']>cut2frame:returned=True;events.append(dict(original_leader_cut_return=row))
    labels=[]
    if cut3 and not cut2 and age()<35:labels.append('original-leader-cut-camera3')
    if cut2 and not returned and age()<36:labels.append('original-leader-cut-camera2')
    if returned and age()<37:labels.append('original-leader-cut-return')
    if age()>=36 and age()<37:labels.append('deadline-context')
    for label in labels:
     if label not in shots:
      shots.add(label)
      try:capture(row,label)
      except Exception as e:events.append(dict(optional_capture_unavailable=repr(e),label=label))
   time.sleep(.03)
'''+s[b:]
s=s.replace('no_209_command=True','controlled_setup_not_event_completion=True')
compile(s,str(p),'exec');p.write_text(s)
print(p,hashlib.sha256(p.read_bytes()).hexdigest(),len(p.read_bytes()))
