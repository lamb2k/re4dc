"""Independent narrow ELF name-binding repair controls; no build/stage/guest."""
from pathlib import Path
import ast,collections,datetime,difflib,gc,hashlib,importlib.util,json,resource,signal,struct,time
resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,)*2)
resource.setrlimit(resource.RLIMIT_CPU,(120,120))
signal.signal(signal.SIGALRM,lambda *args:(_ for _ in()).throw(TimeoutError('120-second review process ceiling')));signal.alarm(120)
T0=time.monotonic();HERE=Path(__file__).resolve().parent;P=HERE.parent
OLD=P/'kos-census-preparation-v1/graph.py';NEW=P/'kos-census-root-graph-fix-v1/graph.py'
ELF_PATH=Path('/dev/shm/gc-motion24-kos-census-v1-2g7teq3g/off/out/re4dc-game.elf');LOG=ELF_PATH.parent.parent/'build.log'
PIN='a3bd56cfff18a83f26a6a5e491ed4cab254753c4aec99efd1bf940812bd37b6b'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(path,name):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
assert sha(NEW)==PIN
seal=P/'kos-census-preparation-v1/TOOLCHAIN-SEAL.json';assert sha(seal)=='c30f2f90564882fa6e179f0895a4e82dbb771722befa79844b853ccb73108209'
assert sha(OLD)==json.loads(seal.read_text())['members']['graph.py']['sha256']=='f7c13930d98642f70bcbc95881f6d38bf001cbb7e20c59bcc3f8d81b0f7d6adf'
original=load(OLD,'original_graph_independent');fixed=load(NEW,'fixed_graph_independent')
oldtext=OLD.read_text();newtext=NEW.read_text();addition="""                    binding = info >> 4
                    assert binding in (0, 1, 2), ('Unsupported function binding', name, binding)
                    # Local functions from different translation units may share a name.
                    # Allocator route targets must resolve to one global/weak definition.
                    if binding == 0: continue
"""
assert newtext.replace(addition,'',1)==oldtext
oldtree=ast.parse(oldtext);newtree=ast.parse(newtext)
def without_init(tree):
 for n in ast.walk(tree):
  if isinstance(n,ast.ClassDef)and n.name=='ELF':n.body=[m for m in n.body if not(isinstance(m,ast.FunctionDef)and m.name=='__init__')]
 return ast.dump(tree,include_attributes=False)
assert without_init(oldtree)==without_init(newtree)
checks=[]
def check(name,fn,exception=None):
 try:value=fn()
 except (AssertionError,KeyError)as e:
  if exception is None:raise
  checks.append(dict(name=name,status='EXPECTED_REFUSAL',exception=type(e).__name__,reason=str(e)[:300]));return
 if exception is not None:raise AssertionError('mutant unexpectedly accepted: '+name)
 if value is False:raise AssertionError('positive control returned false: '+name)
 checks.append(dict(name=name,status='PASS',result=value))
BASE=0x8c010000
# Self-contained ELF32 LE SH fixture: source literal-load+jmp+delay slot, bounded pool,
# distinct target rts+nop. Symbol rows are independent ELF records, not a mocked map.
def fixture(rows=None,patch=None):
 text=bytearray(128);struct.pack_into('<HHHHI',text,0,0xd001,0x402b,0x0009,0x0009,BASE+32);struct.pack_into('<HH',text,32,0x000b,0x0009)
 if patch:patch(text)
 rows=rows if rows is not None else [('_route',BASE,12,1,1),('_target',BASE+32,4,1,1)]
 strings=bytearray(b'\0');names={}
 for name,*_ in rows:
  if name not in names:names[name]=len(strings);strings+=name.encode()+b'\0'
 syms=bytearray(16)
 for name,value,size,binding,index in rows:syms+=struct.pack('<IIIBBH',names[name],value,size,(binding<<4)|2,0,index)
 stroff=0x180;symoff=(stroff+len(strings)+15)&~15;shoff=(symoff+len(syms)+3)&~3;data=bytearray(shoff+160)
 ident=b'\x7fELF\x01\x01\x01'+bytes(9);struct.pack_into('<16sHHIIIIIHHHHHH',data,0,ident,2,42,1,BASE,0,shoff,0,52,0,0,40,4,0)
 data[0x100:0x180]=text;data[stroff:stroff+len(strings)]=strings;data[symoff:symoff+len(syms)]=syms
 for i,row in enumerate([(0,0,0,0,0,0,0,0,0,0),(0,1,6,BASE,0x100,128,0,0,2,0),(0,3,0,0,stroff,len(strings),0,0,1,0),(0,2,0,0,symoff,len(syms),2,0,4,16)]):struct.pack_into('<10I',data,shoff+40*i,*row)
 return bytes(data)
def route(rows=None,patch=None):return fixed.ELF(fixture(rows,patch)).tail_route('_route','_target')
def table(rows):return fixed.ELF(fixture(rows)).symbols
basic=[('_route',BASE,12,1,1),('_target',BASE+32,4,1,1)]
check('synthetic real SH4 route passes',lambda:route())
check('two distinct same-name LOCAL definitions do not collide globally',lambda:table(basic+[('_local',BASE+48,4,0,1),('_local',BASE+52,4,0,1)])and'_local'not in table(basic+[('_local',BASE+48,4,0,1),('_local',BASE+52,4,0,1)]))
for bind,label in[(1,'GLOBAL'),(2,'WEAK')]:
 for order in(0,1):
  loc=('_target',BASE+48,8,0,1);glob=('_target',BASE+32,4,bind,1);rows=[basic[0]]+([loc,glob]if order==0 else[glob,loc])
  check(label+' wins over unrelated LOCAL in order'+str(order),lambda rows=rows:route(rows))
check('sole WEAK route definition is valid',lambda:route([basic[0],('_target',BASE+32,4,2,1)]))
check('identical GLOBAL and WEAK duplicate definition remains accepted',lambda:route(basic+[('_target',BASE+32,4,2,1)]))
for a,b in[(1,1),(2,2),(1,2),(2,1)]:
 check('conflicting bindings'+str((a,b)),lambda a=a,b=b:table([basic[0],('_target',BASE+32,4,a,1),('_target',BASE+36,4,b,1)]),exception=True)
check('conflicting GLOBAL size is refused',lambda:table(basic+[('_target',BASE+32,8,1,1)]),exception=True)
check('LOCAL-only required target cannot satisfy route',lambda:route([basic[0],('_target',BASE+32,4,0,1)]),exception=True)
check('undefined GLOBAL plus LOCAL cannot satisfy required target',lambda:route([basic[0],('_target',0,0,1,0),('_target',BASE+32,4,0,1)]),exception=True)
for binding in(3,10,15):check('unsupported defined function binding'+str(binding),lambda binding=binding:table(basic+[('_unsupported',BASE+48,4,binding,1)]),exception=True)
check('LOCAL destination cannot disguise wrong GLOBAL reference',lambda:route([basic[0],('_target',BASE+48,4,1,1),('_target',BASE+32,4,0,1)]),exception=True)
check('GLOBAL source/target alias does not prove a route',lambda:route([basic[0],('_target',BASE,12,1,1)]),exception=True)
check('wrong branch-register opcode still refuses',lambda:route(patch=lambda b:struct.pack_into('<H',b,2,0x412b)),exception=True)
check('wrong target literal still refuses',lambda:route(patch=lambda b:struct.pack_into('<I',b,8,BASE+36)),exception=True)
check('non-whitelisted opcode before branch still refuses',lambda:route(patch=lambda b:struct.pack_into('<HHH',b,2,0xe001,0x402b,0x0009)),exception=True)
# Independent raw symbol extraction uses indexed NUL search, not repaired name-map logic.
raw=ELF_PATH.read_bytes();assert len(raw)==28765828 and hashlib.sha256(raw).hexdigest()=='5edbbdda44eba9da38b7ada8db0543f9d2d2cdd7eeb158182fc2cae5f8422ea2'
e=struct.unpack_from('<16sHHIIIIIHHHHHH',raw);sections=[struct.unpack_from('<10I',raw,e[6]+40*i)for i in range(e[12])];groups=collections.defaultdict(list)
for section in sections:
 if section[1]!=2:continue
 strings=sections[section[6]];lo=strings[4];hi=lo+strings[5]
 for pos in range(section[4],section[4]+section[5],16):
  name,value,size,info,other,index=struct.unpack_from('<IIIBBH',raw,pos)
  if not index or not name or(info&15)!=2:continue
  end=raw.find(b'\0',lo+name,hi);assert end>=lo+name;key=raw[lo+name:end].decode();groups[key].append(dict(value=value,size=size,index=index,bind=info>>4,position=pos))
ambiguous={k:v for k,v in groups.items()if len({(r['value'],r['size'],r['index'])for r in v})>1}
assert len(ambiguous)==40 and all(any(r['bind']==0 for r in v)for v in ambiguous.values())
mixed={k:v for k,v in ambiguous.items()if any(r['bind']in(1,2)for r in v)};assert len(mixed)==17
conflicts={k:v for k,v in groups.items()if len({(r['value'],r['size'],r['index'])for r in v if r['bind']in(1,2)})>1};assert not conflicts
check('original reader actually refuses retained ELF',lambda:original.ELF(raw),exception=True)
plan=json.loads((P/'kos-census-preparation-v1/PREPARATION.json').read_text())
actual=fixed.verify(ELF_PATH,LOG,'off',plan['baseline_wraps']['off']);assert len(actual['routes'])==13
rootreceipt=P/'kos-census-root-graph-fix-v1/OFF-GRAPH-READBACK.json';assert actual==json.loads(rootreceipt.read_text())
checks.append(dict(name='independent actual OFF ELF +build-log verification',status='PASS',routes=len(actual['routes']),ELF_sha256=actual['ELF_sha256']))
# Real ELF in-memory reference-alias mutant; no mutated binary is written anywhere.
source='___wrap_malloc';target='_malloc';src=[r for r in groups[source]if r['bind']in(1,2)];dst=[r for r in groups[target]if r['bind']in(1,2)];assert len(src)==len(dst)==1
mutation=bytearray(raw);struct.pack_into('<II',mutation,dst[0]['position']+4,src[0]['value'],src[0]['size'])
mutated=bytes(mutation);del mutation
check('actual ELF provider aliased to wrapper refuses opcode route',lambda:fixed.ELF(mutated).tail_route(source,target),exception=True)
del mutated;gc.collect()
assert sha(NEW)==PIN and sha(OLD)=='f7c13930d98642f70bcbc95881f6d38bf001cbb7e20c59bcc3f8d81b0f7d6adf'
assert sha(ELF_PATH)==actual['ELF_sha256']
report=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),decision='CLEAR_TINY_DEFINED_FUNCTION_BINDING_REPAIR_ONLY',scope='Narrow ELF reader repair independent review; no original whole-unit reaudit or live allocation coverage.',original_graph=dict(path=str(OLD),sha256=sha(OLD)),original_tool_seal=dict(path=str(seal),sha256=sha(seal)),fixed_graph=dict(path=str(NEW),sha256=PIN),exact_executable_delta='5 added lines: supported binding assertion, two comments and LOCAL skip',all_other_AST_including_opcode_predicates_unchanged=True,actual_ELF=dict(path=str(ELF_PATH),bytes=len(raw),sha256=actual['ELF_sha256']),build_log=dict(path=str(LOG),sha256=sha(LOG)),root_graph_receipt=dict(path=str(rootreceipt),sha256=sha(rootreceipt)),actual_collisions=dict(distinct_local_name_collision_groups=len(ambiguous),with_valid_global_or_weak=len(mixed),conflicting_global_weak_names=0,names=sorted(ambiguous)),actual_routes=actual['routes'],checks=checks,limits=dict(process_wall_seconds=120,address_space_bytes=256*1024**2,actual_wall_seconds=time.monotonic()-T0,self_peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),runtime_coverage='UNKNOWN: this review does not qualify live census rows/lost/overflow/mallinfo reconciliation, memory or performance.',SDK=0,Make=0,stage=0,guests=0,original_or_fixed_source_writes=0)
assert not(HERE/'REVIEW.json').exists();(HERE/'REVIEW.json').write_text(json.dumps(report,indent=2)+'\n')
(HERE/'EXACT-DIFF.txt').write_text(''.join(difflib.unified_diff(oldtext.splitlines(True),newtext.splitlines(True),fromfile=str(OLD),tofile=str(NEW))))
signal.alarm(0);print(json.dumps(dict(decision=report['decision'],checks=len(checks),actual_edges=13,ambiguous_local_groups=40,mixed_groups=17,limits=report['limits'],review_sha256=sha(HERE/'REVIEW.json'))))
