"""Focused source-only AEV16 admission/publication regression cases; never imports observer."""
from pathlib import Path
import ast,copy,json,struct,hashlib
L=Path(__file__).parent;s=(L/'observe-controlled-ch32-escape023.py').read_text();tree=ast.parse(s)
old=ast.parse((L/'observe-controlled-ch32-door022.py').read_text());func={n.name:n for n in tree.body if isinstance(n,ast.FunctionDef)};oldfunc={n.name:n for n in old.body if isinstance(n,ast.FunctionDef)}
ns=dict(struct=struct)
names=['WP','COUNT','SLOT3','TARGET','DESCRIPTOR','WRITE_ALLOWLIST','QUALIFIED_AREA','INHERITED_GOTOS','CALLBACK_BYTES']
for n in tree.body:
 if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id in names for t in n.targets):exec(compile(ast.Module(body=[n],type_ignores=[]),'source_constants','exec'),ns)
for name in ['native_neutral','original_area_ready','setup_ready','consumed_escape','publish_existing_goto']:
 exec(compile(ast.Module(body=[func[name]],type_ignores=[]),'source_predicate','exec'),ns)
cases=[]
def test(name,value):assert value,name;cases.append(dict(name=name,passed=True))
row=dict(live_native_code_anchors_verified=True,room='0x209',Part=0,previous_room='0x204',phase=[3,0],Stop='0x0',health=[1040,1440,600,600],status1='0x0',native_idle=True,native_Key64=[0,0,0],AEV16_callback_code_exact=True,areas={'0x16':copy.deepcopy(ns['QUALIFIED_AREA'])},warp=dict(flags=[1,1,0,1,1],name='castle21-CONTROLLED-ch32-drain0',room='0x205',rooms=3,max_entry=3,n_go=3,go3='00'*24,n_act=0,n_rsf=0,has_trg=0,has_kill=0,**{'go'+str(i):g for i,g in enumerate(ns['INHERITED_GOTOS'])}))
test('qualifiedoriginalareaandneutralallowsunpublishedslot3',ns['setup_ready'](row))
for label,key,value in [('roomchanged','room','0x20a'),('eventactive','status1','0x10000000'),('nativeplayerbusy','native_idle',False),('stopactive','Stop','0x100'),('deadplayer','health',[0,1440,600,600]),('callbackmismatch','AEV16_callback_code_exact',False)]:
 r=copy.deepcopy(row);r[key]=value;test(label,not ns['setup_ready'](r))
for i in range(3):
 r=copy.deepcopy(row);r['native_Key64'][i]=0x80080000;test('native64oldontrgmustallneutral'+str(i),not ns['setup_ready'](r))
for key in [1,0x400,0x100000000]:
 r=copy.deepcopy(row);r['native_Key64']=[key,0,0];test('native64ALLbitsmustbeneutral_'+hex(key),not ns['setup_ready'](r))
for key,value in [('max_entry',4),('n_go',4),('rooms',4),('go3','01'*24),('go2','00'*24)]:
 r=copy.deepcopy(row);r['warp'][key]=value;test('inheritedrigidentity_'+key,not ns['setup_ready'](r))
r=copy.deepcopy(row);r['areas']['0x16']['enabled']=False;test('consumedoriginalAEVnotrearmed',not ns['setup_ready'](r))
r=copy.deepcopy(row);r['areas']['0x16']['func']+=4;test('originalcallbackpointerrequired',not ns['setup_ready'](r))
r=copy.deepcopy(row);r['warp']['go3']=ns['DESCRIPTOR'].hex();test('preparedslotacceptsonlybeforecount',ns['setup_ready'](r,True)and not ns['setup_ready'](r))
g=bytearray(ns['DESCRIPTOR']);g[21]=1;r['warp']['go3']=g.hex();test('engineownsdonebit',ns['consumed_escape'](r))
def publication_scenario(change_after_descriptor=False):
 working=copy.deepcopy(row);writes=[];state={'count':3}
 def fakewrite(address,data):
  writes.append((address,bytes(data)))
  if address==ns['SLOT3']:
   working['warp']['go3']=data.hex()
   if change_after_descriptor:working['native_Key64'][1]=0x80080000
  elif address==ns['COUNT']:state['count']=struct.unpack('<I',data)[0]
  else:raise AssertionError('Unexpectedwrite')
 ns.update(check=lambda:None,sample=lambda:copy.deepcopy(working),events=[],exact_command_write=fakewrite,u32=lambda a:state['count'])
 try:out=ns['publish_existing_goto']()
 except AssertionError:out=False
 return out,writes
out,writes=publication_scenario();test('descriptor24thencount4lastonly',out and writes==[(ns['SLOT3'],ns['DESCRIPTOR']),(ns['COUNT'],struct.pack('<I',4))]and sum(len(b)for a,b in writes)==28)
out,writes=publication_scenario(True);test('freshneutralfailureafterdescriptorpreventspublication',not out and len(writes)==1)
for name in ['close','read','wait_startup_mapping']:
 test('inheritedreviewedhelperAST_'+name,ast.dump(func[name],include_attributes=False)==ast.dump(oldfunc[name],include_attributes=False))
# Search calls outside function definitions: dormant helpers cannot inject input.
top=ast.Module(body=[n for n in tree.body if not isinstance(n,(ast.FunctionDef,ast.ClassDef))],type_ignores=[])
test('mainnevercallsinputorfocushelper',not any(isinstance(n,ast.Call)and isinstance(n.func,ast.Name)and n.func.id in ['pulse_door','send_x_input','ensure_owned_focus','native_input_ack']for n in ast.walk(top)))
test('noactiveinputorfocusAPIbindingsorcalls',all(token not in s for token in ['u.SendInput','u.SetForegroundWindow','u.GetAsyncKeyState','u.GetForegroundWindow','u.GetGUIThreadInfo']))
test('noMAX_ENTRYwriteinpublisher','MAX_ENTRY'not in ast.unparse(func['publish_existing_goto']))
test('positiononlynoangleorsubplacement',ns['DESCRIPTOR'][20:24]==bytes([0,0,0,3]))
test('shellrootentryexact023', '--execute-allocated023' in (L/'run-controlled-ch32-escape023.sh').read_text() and '--execute-allocated022'not in (L/'run-controlled-ch32-escape023.sh').read_text())
test('nativefreshneutralgatebeforeonepublication','neutral_previous' in s and "row['frame']>neutral_previous['frame']"in s and 'attempted_publication=True'in s)
wrapper=ast.parse((L/'run-controlled-ch32-escape023.py').read_text());test('inheritedfinallystartupcleanupunchanged',ast.dump(wrapper.body[-2],include_attributes=False)==ast.dump(ast.parse((L/'run-controlled-ch32-door022.py').read_text()).body[-2],include_attributes=False))
receipt=dict(scope=__doc__,source_sha256=hashlib.sha256(s.encode()).hexdigest(),case_count=len(cases),cases=cases,no_observer_import=True,no_API_or_guest=True,no_old_broad_suite_rerun=True)
p=L/'controlled023-focused-source-cases.json';p.write_text(json.dumps(receipt,indent=2)+'\n',newline='\n');print(json.dumps(dict(cases=len(cases),receipt_sha256=hashlib.sha256(p.read_bytes()).hexdigest())))
