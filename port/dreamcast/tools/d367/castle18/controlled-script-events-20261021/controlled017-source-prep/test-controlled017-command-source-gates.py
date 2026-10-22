from pathlib import Path
import ast,json,hashlib,struct,copy,ctypes,types
L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18');P=L/'observe-controlled-ch32-door017.py';s=P.read_text();tree=ast.parse(s);env=dict(struct=struct);keep=['setup_ready','door_ready','exact_command_write','publish_existing_goto']
for n in tree.body:
 if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id in ['WP','GO','COUNT','TARGET','DESCRIPTOR']for t in n.targets):exec(compile(ast.Module(body=[n],type_ignores=[]),'actualsetupconstants','exec'),env)
for n in keep:exec(compile(ast.Module(body=[next(x for x in tree.body if isinstance(x,ast.FunctionDef)and x.name==n)],type_ignores=[]),'actual016functions','exec'),env)
base=dict(room='0x205',phase=[3,0],health=[1440,1440,600,600],live_native_code_anchors_verified=True,Stop='0x0',status1='0x610',Key_on='0x0',saved_RSF205=0xc2000000,areas={x:dict(enabled=False)for x in ['0x7','0x8','0x15']},warp=dict(flags=[1,1,0,1,1],name='castle21-CONTROLLED-ch32-drain0',room='0x205',rooms=1,max_entry=1,n_go=0,go0='00'*24,n_act=0,n_rsf=0,has_trg=0,has_kill=0))
base['areas'].update({'0x11':dict(enabled=True),'0x1b':dict(func=0x8c910988)})
checks=[]
def check(n,b):assert b,n;checks.append(n)
check('actual015-shaped-ready-unused-slot',env['setup_ready'](base))
for name,key,val in [('eventStop','Stop','0x10000000'),('eventstatus','status1','0x10000610'),('wrongroom','room','0x204'),('dead-no-input','health',[0,1440,600,600]),('unverified-code','live_native_code_anchors_verified',False)]:
 v=copy.deepcopy(base);v[key]=val;check(name,not env['setup_ready'](v))
for key,val in [('n_go',1),('go0','01'+'00'*23),('rooms',2),('flags',[1,0,0,1,1])]:
 v=copy.deepcopy(base);v['warp'][key]=val;check('reject-'+key,not env['setup_ready'](v))
v=copy.deepcopy(base);v['health'][0]=1300;check('ordinary-positive-injury-still-eligible',env['setup_ready'](v))
# Actual WPM function, isolated mock kernel only: no OpenProcess/DLL/OS child.
memory={env['GO']:bytes(24),env['COUNT']:struct.pack('<I',0)};calls=[];ageval=[1.];ram=0x80000000
def fakewrite(h,address,buf,n,got):
 a=address-ram+0x8c000000;memory[a]=bytes(buf.raw[:n]);got._obj.value=n;calls.append((a,n));return 1
def row():
 q=copy.deepcopy(base);q['warp']['go0']=memory[env['GO']].hex();q['warp']['n_go']=struct.unpack('<I',memory[env['COUNT']])[0];return q
env.update(memory_ready=True,k=types.SimpleNamespace(WriteProcessMemory=fakewrite),C=ctypes,h=1,ram=ram,events=[],age=lambda:ageval[0],check=lambda:None,shutil=types.SimpleNamespace(disk_usage=lambda d:types.SimpleNamespace(free=100*1024**3)),D=L,read=lambda a,n:memory[a][:n],u32=lambda a:struct.unpack('<I',memory[a])[0],sample=row)
check('publish-actual-function',env['publish_existing_goto']())
check('descriptor24-before-count4-only',calls==[(env['GO'],24),(env['COUNT'],4)])
check('descriptor-payload-exact',memory[env['GO']]==env['DESCRIPTOR'])
check('no-republish-after-count1',env['publish_existing_goto']()is False)
for a,b in [(0x8c000000,b'\1'),(env['GO'],bytes(24)),(env['COUNT'],struct.pack('<I',2))]:
 try:env['exact_command_write'](a,b);ok=False
 except AssertionError:ok=True
 check('write-allowlist-'+hex(a)+'-'+str(len(b)),ok)
door=copy.deepcopy(base);door.update(player_ptr=0x8cabc4c0,native_AEV00_collision_clipped_front_hit=True);g=bytearray(env['DESCRIPTOR']);g[21]=1;door['warp'].update(n_go=1,go0=g.hex());door['areas']['0x0']=dict(ptr=0x8ca92cd0,enabled=True,type=1,func=0,checkFlag=1,trigger=8,checkType=1,door=dict(destination='0x204',Part=1,lockType=0,lockFlag=0,callback='0x8c910320'));door['action']=dict(active=1,work=[dict(arg=0x8ca92cd0,kind=0x10,button=1,func=0x8c14a95c,type=2,d=door['player_ptr'])])
check('native-source-shaped-door-ready',env['door_ready'](door))
for name,change in [('goto-not-consumed',lambda x:x['warp'].update(go0=env['DESCRIPTOR'].hex())),('no-native-front',lambda x:x.update(native_AEV00_collision_clipped_front_hit=False)),('wrongnativecallback',lambda x:x['action']['work'][0].update(func=0x8c146f3c)),('wrongdest',lambda x:x['areas']['0x0']['door'].update(destination='0x209')),('locked',lambda x:x['areas']['0x0']['door'].update(lockType=1))]:
 v=copy.deepcopy(door);change(v);check(name,not env['door_ready'](v))
r=dict(scope='Actual016 extracted source pure predicates/command-publication function with mock kernel, no OS processes/DLL/guest/native acceptance.',observer_sha256=hashlib.sha256(P.read_bytes()).hexdigest(),checks=checks,passed=len(checks),write_calls=[dict(address=hex(a),bytes=n)for a,n in calls]);(L/'controlled017-source-gates.json').write_text(json.dumps(r,indent=2)+'\n');print('PASS',len(checks),r['observer_sha256'])
