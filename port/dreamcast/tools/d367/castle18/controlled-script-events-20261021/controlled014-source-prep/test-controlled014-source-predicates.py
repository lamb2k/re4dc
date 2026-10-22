from pathlib import Path
import ast,json,copy,hashlib,struct
L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18');p=L/'observe-controlled-ch32-drain014.py';s=p.read_text(encoding='utf-8');tree=ast.parse(s);wanted=['lever_ready','prompt_ready','message_identity'];ns={'invoked':True,'exec_seen':True,'held_seen':True,'META':json.loads((L/'controlled-ch32-drain014-room-message0.json').read_text()),'hashlib':hashlib};exec(compile(ast.Module(body=[x for x in tree.body if isinstance(x,ast.FunctionDef)and x.name in wanted],type_ignores=[]),'actual014_predicates','exec'),ns)
r=dict(live_native_code_anchors_verified=True,room='0x205',phase=[3,0],chapter=7,health=[1440],Stop='0x0',status1='0x0',saved_RSF205=0,player_ptr=0x8c700000,native_AEV08_collision_clipped_front_hit=True,areas={'0x8':dict(enabled=True,checkFlag=1,checkType=1,trigger=8,func=0x8c900000,ptr=0x8c800000)},action=dict(active=1,stop_old=0,work=[dict(arg=0x8c800000,d=0x8c700000,type=2,button=1,func=0x8c100000)]));tests=[]
def ck(name,result):assert result,name;tests.append(name)
ck('actualleverpredicate_accepts_nativeclippedhit_registeredaction',bool(ns['lever_ready'](r)))
for key,value in [('native_AEV08_collision_clipped_front_hit',False),('room','0x204'),('saved_RSF205',0x80000000),('Stop','0x1'),('health',[0])]:
 q=copy.deepcopy(r);q[key]=value;ck('lever_reject_'+key,not ns['lever_ready'](q))
q=copy.deepcopy(r);q['action']['work'][0]['arg']=0x8c800001;ck('lever_reject_foreignAEVaction',not ns['lever_ready'](q))
m=dict(vptr=0x8c2ce56c,be_flag=1,flags2=1,attribute=0x1012,button=1,wait=0,table_size=2,selection=0,current=0);q=dict(r,message0=m,message0_source_identity={'source':True});ck('nativeYes_ready',bool(ns['prompt_ready'](q)))
for key,val in [('vptr',0),('attribute',0x01020051),('selection',1),('table_size',0),('wait',1),('current',2)]:
 x=copy.deepcopy(q);x['message0'][key]=val;ck('prompt_reject_'+key,not ns['prompt_ready'](x))
x=copy.deepcopy(q);x['message0_source_identity']=None;ck('prompt_reject_wrong_source_message',not ns['prompt_ready'](x))
# Exercise actual native getAddr/span/hash against the retained staged MDT for every supported language.
b=Path(r'\\wsl.localhost\Ubuntu-24.04\root\probe\castle21-recovered-j-content-20261021\tree\st2\r205.arc').read_bytes();meta=ns['META'];mdt=b[meta['MDT_offset']:meta['MDT_offset']+meta['MDT_size']];table=0x8c800000;pg=0x8c400000
for lang in range(6):
 vals={0x8c3b64c4:lang,0x8c3b64c4+8:table,pg+0x4f20:table}
 def u32(a):return vals[a]if a in vals else struct.unpack_from('<I',mdt,a-table)[0]
 ns.update(u32=u32,read=lambda a,n:mdt[a-table:a-table+n],inram=lambda a,n=1:0x8c000000<=a and a+n<=0x8d000000)
 start=table+meta['languages'][str(lang)]['message0_offset'];ck(f'actualstagedmessage0_language{lang}',bool(ns['message_identity'](pg,{'text':start})));ck(f'reject_wrongmessagespan_language{lang}',not ns['message_identity'](pg,{'text':start+meta['languages'][str(lang)]['message0_bytes']}))
r=dict(scope='Source-extracted actual014 pure predicate/native-table tests only; no DLL, process, Flycast or gameplay execution.',observer_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),PASS=len(tests),tests=tests,no_guest=True)
(L/'controlled-ch32-drain014-focused-source-checks.json').write_text(json.dumps(r,indent=2)+'\n');print('PASS',len(tests),'focused source checks, no guest')
