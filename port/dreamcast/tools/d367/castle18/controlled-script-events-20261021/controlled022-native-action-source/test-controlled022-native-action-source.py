from pathlib import Path
import ast,json,struct,math,hashlib,copy
L=Path(__file__).parent;D=Path(r'C:\Flycast-Evidence\re4-dreamcast\castle18-20261018\Test21\recovered-j-content-20261021');P=L/'observe-controlled-ch32-door022.py';s=P.read_text();T=ast.parse(s);old=ast.parse((L/'observe-controlled-ch32-door021.py').read_text());env=dict(struct=struct,math=math);names=['WP','GO0_DONE','TARGET1','TARGET2','STAGES']
for n in T.body:
 if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id in names for t in n.targets):exec(compile(ast.Module(body=[n],type_ignores=[]),'readonlyconstants','exec'),env)
for name in ['freeplay_ready','consumed','door_ready']:
 n=next(n for n in T.body if isinstance(n,ast.FunctionDef)and n.name==name);exec(compile(ast.Module(body=[n],type_ignores=[]),'actual022placementlogic','exec'),env)
r=json.loads((D/'route-walk-controlled-ch32-door021/controlled-door021-observer-summary.json').read_text())['last'];checks=[]
def ck(n,v):assert v,n;checks.append(n)
ck('actual021-nativeDoor1-admits-disabledAEVwaiter',env['door_ready'](r,2)and not r['areas']['0xa']['enabled'])
target=struct.unpack_from('<3f',bytes.fromhex(r['warp']['go2']),4);ck('actual021-outsideoldradius-stillnativeactionready',math.dist(target,r['player_pos'])>150 and env['door_ready'](r,2))
for case in ['stage1','wrongroom','eventactive','wrongprev','wrongPart','countchanged','notconsumed','lockkey','openflag','wrongconstructor','wrongEtc','wrongpointer','wrongcallback','wrongslot','wrongtype','wrongd','noaction']:
 q=copy.deepcopy(r);stage=2;d=q['physical_doors1'][0];a=q['action']['work'][0]
 if case=='stage1':stage=1
 elif case=='wrongroom':q['room']='0x204'
 elif case=='eventactive':q['status1']='0x10000000'
 elif case=='wrongprev':q['previous_room']='0x205'
 elif case=='wrongPart':q['Part']=1
 elif case=='countchanged':q['warp']['n_go']=4
 elif case=='notconsumed':q['warp']['go2']=bytes.fromhex(q['warp']['go2'])[:21].hex()+'00'+bytes.fromhex(q['warp']['go2'])[22:].hex()
 elif case=='lockkey':d['key_flag']=1
 elif case=='openflag':d['flag']='0x10000000'
 elif case=='wrongconstructor':d['type']=2
 elif case=='wrongEtc':q['physical_doors1']=[]
 elif case=='wrongpointer':a['arg']+=4
 elif case=='wrongcallback':a['func']=0x8c14a95c
 elif case=='wrongslot':a['slot']=2
 elif case=='wrongtype':a['type']=2
 elif case=='wrongd':a['d']=1
 elif case=='noaction':q['action']['active']=0
 ck('reject-'+case,not env['door_ready'](q,stage))
ck('no-WPM-binding-or-calls-or-publicationhelpers','WriteProcessMemory'not in s and 'publish_existing_goto'not in s and 'exact_command_write'not in s and 'pose_matches'not in s)
ck('observer-no-VM-WRITE-or-OPERATION-rights','OpenProcess(0x1000|0x10|0x100000' in s and 'WRITE_ALLOWLIST=[]'in s)
ck('single-stage2-attempt-beforepulse',"attempted[2]=True\n     try:\n      pulse_result=pulse_door(2)"in s and'not attempted[2]'in s and'sent[1]'not in s)
for name in ['async_x_state','send_x_input','pulse_door','native_input_ack','check','sample','window_evidence','ensure_owned_focus','freeplay_ready']:
 a=next(n for n in old.body if isinstance(n,ast.FunctionDef)and n.name==name);b=next(n for n in T.body if isinstance(n,ast.FunctionDef)and n.name==name);ck('unchanged-inherited-'+name,ast.dump(a,include_attributes=False)==ast.dump(b,include_attributes=False))
j=dict(scope='Onlychanged022 nativeaction/zero-WPM/currentstate placement logic and inheritedAST comparison. No34/26/broad rerun, actualinput/guest/build.',observer_sha256=hashlib.sha256(P.read_bytes()).hexdigest(),actual021_fixture_sha256=hashlib.file_digest((D/'route-walk-controlled-ch32-door021/controlled-door021-observer-summary.json').open('rb'),'sha256').hexdigest(),passed=len(checks),checks=checks);(L/'controlled022-native-action-source-cases.json').write_text(json.dumps(j,indent=2)+'\n');print('PASS',len(checks),j['observer_sha256'])
