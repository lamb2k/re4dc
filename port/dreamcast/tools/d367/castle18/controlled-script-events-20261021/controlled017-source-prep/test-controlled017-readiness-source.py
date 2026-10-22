from pathlib import Path
import ast,re,ctypes as C,ctypes.wintypes as W,struct,json,hashlib,types
L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18');P=L/'observe-controlled-ch32-door017.py';t=ast.parse(P.read_text());env=dict(C=C,W=W,Exception=Exception,json=json,struct=struct,re=re)
for name in ['MemoryUnavailable','MemoryBasicInformation','startup_log_mapping','readable_sequence','region_query','read']:
 n=next(x for x in t.body if isinstance(x,(ast.ClassDef,ast.FunctionDef))and x.name==name);exec(compile(ast.Module(body=[n],type_ignores=[]),'actual017readiness','exec'),env)
checks=[]
def ck(n,b):assert b,n;checks.append(n)
expected=Path(r'C:\cap017\data\disc.state');log='00:00:613 VMEM RAM(16 MB) 00007FF4CD790000 VRAM64\n';ck('mapping-alone-no-read-admission',env['startup_log_mapping'](log,expected)is None)
wrong=log+r'00:00:730 Loaded state ver 854 from C:\other\data\disc.state size 28152878';ck('wrong-state-path-not-ready',env['startup_log_mapping'](wrong,expected)is None)
full=log+'00:00:730 Loaded state ver 854 from '+str(expected)+' size 28152878\n';m=env['startup_log_mapping'](full,expected);ck('exact-state-plus-mapping-ready',m['RAM']==0x7ff4cd790000 and m['mapping_precedes_load'])
ck('later-remapping-not-admitted',not env['startup_log_mapping'](full+log,expected)['mapping_precedes_load'])
row=dict(pg=0x8c3aa71c,frame=1770,phase=[3,0],room='0x205',live_native_code_anchors_verified=True);prev=dict(pg=row['pg'],frame=1769,RAM_base=m['RAM'])
ck('first-readable-sample-not-enough',not env['readable_sequence'](row,None,m['RAM']));ck('advancing-native-pair-ready',env['readable_sequence'](row,prev,m['RAM']));ck('same-source-frame-not-ready',not env['readable_sequence'](dict(row,frame=1769),prev,m['RAM']));ck('other-RAM-not-ready',not env['readable_sequence'](row,prev,0x12340000));ck('unverified-code-not-ready',not env['readable_sequence'](dict(row,live_native_code_anchors_verified=False),prev,m['RAM']))
MB=env['MemoryBasicInformation'];ck('native64-MBI-size48',C.sizeof(MB)==48);ram=m['RAM'];mode=['success'];qmode=['success']
def vqe(h,address,out,n):
 if qmode[0]=='fail':C.set_last_error(487);return 0
 q=out._obj;q.BaseAddress=ram;q.AllocationBase=ram;q.RegionSize=16*1024**2;q.State=0x1000;q.Protect=4;q.Type=0x40000;C.set_last_error(5);return 48
payload=struct.pack('<I',row['pg'])
def rpm(h,address,buf,n,got):
 if mode[0]=='partial':C.memmove(buf,payload,2);got._obj.value=2;C.set_last_error(299);return 0
 C.memmove(buf,payload,n);got._obj.value=n;C.set_last_error(0);return 1
env.update(k=types.SimpleNamespace(ReadProcessMemory=rpm,VirtualQueryEx=vqe),h=1,ram=ram,memory_ready=True,read_failure_count=0,read_diagnostics=[],age=lambda:.75,owner=dict(pid=999,start_filetime=123))
q=env['region_query'](ram+0x2e91dc,4);ck('VQE-committed-accessible-covers',q['committed']and q['accessible']and q['covers']);ck('exact-four-byte-read-success',env['read'](0x8c2e91dc,4)==payload)
mode[0]='partial'
try:env['read'](0x8c2e91dc,4);ck('partial-read-raises',False)
except env['MemoryUnavailable']as e:
 ck('exact-request-addresses',e.detail['guest_address']=='0x8c2e91dc'and e.detail['host_address']=='0x7ff4cda791dc');ck('exact-error-and-bytes-preserved-before-VQE',e.detail['win32_error']==299 and e.detail['bytes_read']==2 and e.detail['requested_bytes']==4 and e.detail['api_ok']is False);ck('unavailable-clears-input-readiness',env['memory_ready']is False);ck('partial-bytes-recorded',e.detail['partial_data_hex']==payload[:2].hex())
qmode[0]='fail';q=env['region_query'](ram+0x2e91dc,4);ck('VQE-failure-reported-not-ready',q['error']==487 and not q['covers']and not q['committed'])
# Diagnostics are mocked; ERROR_PARTIAL_COPY299 is NOT attributed to the actual016 failure.
r=dict(scope='Extracted017 functions; fake WinAPI only, no DLL/OpenProcess/guest. Mock299 doesNOTclassifyactual016error, which is unrecorded.',observer_sha256=hashlib.sha256(P.read_bytes()).hexdigest(),checks=checks,passed=len(checks),mock_read_error=env['read_diagnostics'][0]);(L/'controlled017-readiness-source-cases.json').write_text(json.dumps(r,indent=2)+'\n');print('PASS',len(checks),r['observer_sha256'])
