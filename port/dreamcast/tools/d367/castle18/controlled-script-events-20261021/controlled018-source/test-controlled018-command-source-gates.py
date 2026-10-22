from pathlib import Path
import ast,json,hashlib,struct,copy,ctypes,types
L=Path(__file__).parent;P=L/'observe-controlled-ch32-door018.py';tree=ast.parse(P.read_text());env=dict(struct=struct,math=__import__('math'));names=['WP','COUNT','MAX_ENTRY','GO0_DONE','TARGET1','TARGET2','STAGES','WRITE_ALLOWLIST']
for n in tree.body:
 if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id in names for t in n.targets):exec(compile(ast.Module(body=[n],type_ignores=[]),'actual018constants','exec'),env)
for name in ['freeplay_ready','consumed','setup_ready','pose_matches','door_ready','exact_command_write','publish_existing_goto']:
 n=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name==name);exec(compile(ast.Module(body=[n],type_ignores=[]),'actual018functions','exec'),env)
checks=[]
def ck(n,v):assert v,n;checks.append(n)
base=dict(room='0x204',Part=1,previous_room='0x205',phase=[3,0],health=[1440,1440,600,600],live_native_code_anchors_verified=True,Stop='0x0',status1='0x200',Key_on='0x0',warp=dict(flags=[1,1,0,1,1],name='castle21-CONTROLLED-ch32-drain0',room='0x205',rooms=2,max_entry=1,n_go=1,go0=env['GO0_DONE'].hex(),go1='00'*24,go2='00'*24,n_act=0,n_rsf=0,has_trg=0,has_kill=0))
ck('actual017-ready-current-entry2',env['setup_ready'](base,1));ck('futureentry3-not-prequeued',not env['setup_ready'](base,2))
for key,val in [('Stop','0x10000000'),('status1','0x10000200'),('room','0x209'),('Part',0),('previous_room','0x204'),('live_native_code_anchors_verified',False)]:
 v=copy.deepcopy(base);v[key]=val;ck('stage1-reject-'+key,not env['setup_ready'](v,1))
for key,val in [('rooms',3),('n_go',2),('max_entry',2),('go0','00'*24),('go1','01'+'00'*23),('go2','01'+'00'*23)]:
 v=copy.deepcopy(base);v['warp'][key]=val;ck('stage1-reject-warp-'+key,not env['setup_ready'](v,1))
v=copy.deepcopy(base);v['health'][0]=1000;ck('legitimate-positive-injury-still-ready',env['setup_ready'](v,1))
# Actual publisher functions, fake kernel and typed byte-addressed memory only. No WinDLL/OpenProcess/process.
memory={};calls=[];mode=['success'];frame_room=[base];ram=0x80000000
for a,n in [(env['COUNT'],4),(env['MAX_ENTRY'],1),(env['STAGES'][1]['address'],24),(env['STAGES'][2]['address'],24)]:memory[a]=bytes(n)
memory[env['COUNT']]=struct.pack('<I',1);memory[env['MAX_ENTRY']]=b'\1'
def fakewrite(h,address,buf,n,got):
 a=address-ram+0x8c000000;calls.append((a,n));got._obj.value=n if mode[0]=='success'else n-1;memory[a]=bytes(buf.raw[:n]);return int(mode[0]!='failed')
def row():
 q=copy.deepcopy(frame_room[0]);q['warp'].update(n_go=struct.unpack('<I',memory[env['COUNT']])[0],max_entry=memory[env['MAX_ENTRY']][0],go1=memory[env['STAGES'][1]['address']].hex(),go2=memory[env['STAGES'][2]['address']].hex());return q
read=lambda a,n:memory[a][:n];env.update(memory_ready=True,k=types.SimpleNamespace(WriteProcessMemory=fakewrite),C=ctypes,h=1,ram=ram,events=[],age=lambda:1.,check=lambda:None,shutil=types.SimpleNamespace(disk_usage=lambda d:types.SimpleNamespace(free=100*1024**3)),D=L,read=read,u32=lambda a:struct.unpack('<I',read(a,4))[0],sample=row)
ck('stage1-publisher-success',env['publish_existing_goto'](1));ck('slot24-admission1-count4-last-stage1',calls==[(env['STAGES'][1]['address'],24),(env['MAX_ENTRY'],1),(env['COUNT'],4)]);ck('stage1-no-republish',not env['publish_existing_goto'](1));ck('stage2-refuses-before-actual209',not env['publish_existing_goto'](2))
g1=bytearray(env['STAGES'][1]['descriptor']);g1[21]=1;memory[env['STAGES'][1]['address']]=bytes(g1);frame_room[0]=copy.deepcopy(base);frame_room[0].update(room='0x209',Part=0,previous_room='0x204');frame_room[0]['warp']['rooms']=3
ck('stage2-after-actual209-ready',env['setup_ready'](row(),2));ck('stage2-publisher-success',env['publish_existing_goto'](2));ck('exact58bytes-sixwrites',sum(n for a,n in calls)==58 and calls[-3:]==[(env['STAGES'][2]['address'],24),(env['MAX_ENTRY'],1),(env['COUNT'],4)])
for a,data,stage in [(0x8c000000,b'1',1),(env['STAGES'][2]['address'],env['STAGES'][2]['descriptor'],1),(env['MAX_ENTRY'],b'\3',1),(env['COUNT'],struct.pack('<I',3),1)]:
 try:env['exact_command_write'](a,data,stage);allowed=True
 except AssertionError:allowed=False
 ck('reject-undeclared-'+hex(a)+'-'+str(stage),not allowed)
# Partial/failed actual WPM prevents later admission/count; changed coherent room likewise stops after descriptor only.
for case in ['partial','failed','changed-room']:
 memory[env['COUNT']]=struct.pack('<I',1);memory[env['MAX_ENTRY']]=b'\1';memory[env['STAGES'][1]['address']]=bytes(24);memory[env['STAGES'][2]['address']]=bytes(24);frame_room[0]=copy.deepcopy(base);calls.clear();mode[0]=case if case!='changed-room'else'success';samples=[0]
 def sample():
  q=row();samples[0]+=1
  if case=='changed-room'and samples[0]>1:q['Stop']='0x10000000'
  return q
 env['sample']=sample
 try:env['publish_existing_goto'](1);failed=False
 except AssertionError:failed=True
 ck(case+'-no-count-no-retry',failed and calls==[(env['STAGES'][1]['address'],24)]and memory[env['COUNT']]==struct.pack('<I',1))
mode[0]='success'
# Final native source-shaped gates: physicalDoor1 is type0/d0/slot5; genericAEV door is type2/dplayer.
def doorbase(stage):
 q=copy.deepcopy(base);q.update(room=env['STAGES'][stage]['room'],player_ptr=0x8cabc4c0,player_pos=list(struct.unpack_from('<3f',env['STAGES'][stage]['descriptor'],4)))
 g=bytearray(env['STAGES'][stage]['descriptor']);g[21]=1;q['warp'].update(n_go=stage+1,max_entry=env['STAGES'][stage]['entry'],rooms=env['STAGES'][stage]['entry']);q['warp']['go'+str(stage)]=g.hex();q['action']=dict(active=1,work=[]);return q
q=doorbase(1);q.update(native_AEV04_clipped_hit=True,areas={'0x4':dict(ptr=0x8ca36f80,enabled=True,type=1,func=0,checkFlag=1,trigger=8,checkType=1,door=dict(destination='0x209',Part=0,lockType=0,lockFlag=0,callback='0x0'))});q['action']['work']=[dict(arg=0x8ca36f80,kind=0x10,button=1,func=0x8c14a95c,type=2,d=q['player_ptr'])]
ck('generic-nativeDoor4-ready',env['door_ready'](q,1));v=copy.deepcopy(q);v['native_AEV04_clipped_hit']=False;ck('native-front-not-diagnostic-matrix',not env['door_ready'](v,1))
q=doorbase(2);q.update(areas={'0xa':dict(type=2,func=0x8c910100)},physical_doors1=[dict(ptr='0x8cab1234',id=0x41,Etc_no=1,type=1,hp=1000,flag='0x0',door_work_flags='0x0',key_flag=0x36,position=[-15750.,2000.,12850.])]);q['action']['work']=[dict(arg=0x8cab1234,kind=0x10,slot=5,button=1,func=0x8c0bc300,type=0,d=0,flags=0)]
ck('physical-nativeDoor1-ready',env['door_ready'](q,2))
for key,val in [('slot',4),('type',2),('d',q['player_ptr']),('func',0x8c14a95c),('arg',0x8cab5678),('flags',1)]:
 v=copy.deepcopy(q);v['action']['work'][0][key]=val;ck('physical-reject-action-'+key,not env['door_ready'](v,2))
for key,val in [('flag','0x10000000'),('key_flag',0),('type',2),('hp',0)]:
 v=copy.deepcopy(q);v['physical_doors1'][0][key]=val;ck('physical-reject-door-'+key,not env['door_ready'](v,2))
v=copy.deepcopy(q);v['action']['work'][0]['func']=0x8c0bc384;ck('original-physical-alternate-action2-ready',env['door_ready'](v,2));v=copy.deepcopy(q);v['player_pos'][0]+=1000;ck('actualpose-required-not-done-only',not env['door_ready'](v,2))
r=dict(scope='SOURCE ONLY actual018 extracted predicates/publication with mocked byte memory and WPM; no OS/guest/write/input.',observer_sha256=hashlib.sha256(P.read_bytes()).hexdigest(),passed=len(checks),checks=checks);(L/'controlled018-source-gates.json').write_text(json.dumps(r,indent=2)+'\n');print('PASS',len(checks),r['observer_sha256'])