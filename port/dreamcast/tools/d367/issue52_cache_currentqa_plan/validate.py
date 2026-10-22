"""Read and verify the source-only current-QA plan, never run target tools."""
from pathlib import Path
import gzip,hashlib,json,struct,sys
P=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
def load(n):
 b=(P/n).read_bytes();return json.loads(gzip.decompress(b)if n.endswith('.gz')else b)
def verify(row):
 p=Path(row['p']);assert p.is_file(),p;assert p.stat().st_size==row['b']and sha(p.read_bytes())==row['sha'],p
plan=load('plan.json');assert not any(plan['runs'].values());assert plan['matrix']['current_QA_OFF']['GANADO_ROUTINE_BYTES']==1
qa=load('qa52190.json')
for n in ['programme','elf','recipe','resolved','build_log','owned_build','receipt']:verify(qa[n])
for x in qa['overlays']:verify(x)
assert len(qa['overlays'])==14 and qa['programme']['sha']=='52190ed293d8e62238bcad40fd351d35a965b253ad5b59cda570d0de34187e45'
module=load('module-reconstruction.json.gz');assert len(module['constituents'])==14
assert sum(r['rebuild']for r in module['constituents'])==1
for r in module['constituents']:
 p=Path(module['oldprefix'])/r['r'];assert p.stat().st_size==r['old']['b']and sha(p.read_bytes())==r['old']['sha']
 if not r['rebuild']:assert r['normalized_flags_equal']and not r['source_delta']
 if r['d']:verify(r['d'])
verify(module['state_ld'])
cc=load('cache-object-contract.json')
for r in cc['rows']:
 assert r['flags_exact_after_only_stack_dependency_output_instrumentation_removed'];verify(r['eight_argv_pin']);verify(r['current_header'])
 for obj in r['objects'].values():verify(obj)
for r in cc['generated']:verify(r['qa']);verify(r['old']);assert r['exact']
for r in cc['sourcepins'].values():verify(r)
link=load('link-input-template.json.gz');assert len(link['objects'])==447
for r in link['objects']:
 if 'future'not in r:verify(r)
for r in link['C57_context'].values():verify(r)
for r in load('references.json'):verify(r)
ls=load('link-support.json')
for r in ls['libraries']+ls['C57_context_support']:verify(r)
verify(ls['canonical_structural_ref'])
tc=load('tool-closure-reuse.json')
for r in tc['source_files']+[tc['qualification'],tc['manifest'],tc['tool_closure']]:verify(r)
assert len(ls['overlay_steps'])==14 and len(ls['libraries'])==30
# Read-only object comparison; this does NOT substitute for a fresh exact QA programme gate.
def projection(p):
 b=p.read_bytes();h=struct.unpack_from('<HHIIIIIHHHHHH',b,16);off,esz,n,stri=h[5],h[10],h[11],h[12];ss=[struct.unpack_from('<IIIIIIIIII',b,off+i*esz)for i in range(n)];st=ss[stri];names=b[st[4]:st[4]+st[5]]
 def name(i):return names[i:names.index(0,i)].decode()
 rows=[]
 for s in ss:
  if s[2]&2:rows.append((name(s[0]),s[1],s[2],s[3],s[5],s[8],s[9],None if s[1]==8 else sha(b[s[4]:s[4]+s[5]])))
 # Normalize every relocation to target section, offset, type, symbol identity; ignore debug-only references.
 reloc=[]
 for s in ss:
  if s[1]not in (4,9)or not(ss[s[7]][2]&2):continue
  sym=ss[s[6]];strings=ss[sym[6]];strb=b[strings[4]:strings[4]+strings[5]]
  for at in range(s[4],s[4]+s[5],s[9]):
   ro,ri=struct.unpack_from('<II',b,at);sy=struct.unpack_from('<IIIBBH',b,sym[4]+(ri>>8)*sym[9]);nm=strb[sy[0]:strb.index(0,sy[0])].decode();sn=name(ss[sy[5]][0])if sy[5]<len(ss)else sy[5]
   reloc.append((name(ss[s[7]][0]),ro,ri&255,nm,sy[1],sy[2],sy[3],sy[4],sn,struct.unpack_from('<i',b,at+8)[0]if s[1]==4 else None))
 return sha(json.dumps([sorted(rows),sorted(reloc,key=str)],separators=(',',':')).encode())
obs=[]
oldroot=Path(module['oldprefix'])
for r,old in zip(cc['rows'],[oldroot/'sscrn_bridge.o',oldroot/'src/game/main.o']):
 cur=Path(r['objects']['default']['p']);a=projection(old);c=projection(cur);obs.append({'tu':r['tu'],'old':str(old),'old_projection':a,'qualified_default_projection':c,'allocated_and_normalized_relocations_exact':a==c})
result={'state':'SOURCE_PLAN_VALIDATED_NO_COMPILER_OR_LINK','files_external_pins_checked':True,'objects':447,'constituents':14,'reused':13,'fresh_proposed_TUs':2,'historical_vs_qualified_default_objects_readonly_observation':obs,'not_programme_acceptance':'Fresh raw52190/all14/allocated+loadableELF remains mandatory. No header swap/waiver.'}
if len(sys.argv)>1:Path(sys.argv[1]).write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
