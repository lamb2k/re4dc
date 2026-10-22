#!/usr/bin/env python3
"""Allocated exact-base16 output plus proposed142 behavior-equivalent source policy."""
from pathlib import Path
import copy,hashlib,json,shutil,struct,subprocess,sys,time,zlib
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE));import repeat_alpha_plan as virtual
H=lambda b:hashlib.sha256(b).hexdigest()
O=Path('/root/re4data/private/texture-rect21-alpha-repeat16-20261022-v1')
A=Path('/root/re4data/private/texture-rect21-next142-alpha-20261022-v1')
P=Path('/root/re4data/private/texture-rect21-alpha-repeat-unknown-plan-20261022')
E=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/texture-rect21-20261021/alpha-repeat16-batch-01')
CAP=6291456;FLOOR=19394461696
size=lambda p:sum(x.stat().st_size for x in p.rglob('*')if x.is_file())if p.exists()else 0

def guard(extra=0):
 assert shutil.disk_usage('/mnt/c').free>=FLOOR
 assert 2*(size(O)+extra)+131072<CAP,('budget',size(O),extra)
def write(p,b):
 guard(len(b));p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb')as f:f.write(b)
def emitjson(p,j):write(p,(json.dumps(j,indent=2)+'\n').encode())
def run(cmd,timeout=30):
 guard();r=subprocess.run(cmd,capture_output=True,timeout=timeout);assert len(r.stdout)+len(r.stderr)<65536
 return r

def main():
 alloc=Path('/mnt/c/Game Dev/Emulators/codex-lanes/texture-rect21/ALPHA-REPEAT16-ROOT-ALLOCATION.json');assert H(alloc.read_bytes())=='e4d31562251cbf98cb580e7beef8268c278d01370f6d054e7eb54184bfbb52bb';assert shutil.disk_usage('/mnt/c').free>=FLOOR+CAP+67108864;assert not O.exists()and not E.exists();O.mkdir();E.mkdir();write(O/'ROOT-ALLOCATION.json',alloc.read_bytes());plan=json.loads((P/'virtual-repeat16.json').read_text());expected={x['original_key']:x for x in plan['records']};original=json.loads((A/'conversion-receipt.json').read_text());new={};start=time.monotonic();V=O/'virtual-proof';V.mkdir()
 def receive(row,b,key):
  q=expected[row['original_key']];assert H(b)==q['virtual_package_sha256']and len(b)==q['virtual_package_bytes']and '%08x-%08x'%key==q['virtual_candidate_key']and struct.unpack_from('<I',b,36)[0]==q['virtual_payload_crc32'];p=O/'textures'/(q['virtual_candidate_key']+'.re4tex');write(p,b);x=copy.deepcopy(row);x.update(scoped_key=q['virtual_candidate_key'],relative_path=str(p.relative_to(O)),physical=q['physical'],uv_scale=q['uv_scale'],candidate_sha256=H(b),candidate_crc32=q['virtual_payload_crc32'],candidate_payload=q['repeat_payload_bytes'],candidate_request_rounded=q['repeat_request_rounded'],package_bytes=len(b),candidate_texture_class=q['source_texture_class'],base_exact=True,policy_qualified=True,representation='EXACT_BASE_REPEAT_SHORT_AXIS_MIPS');new[x['original_key']]=x
 sys.argv=['repeat_alpha_plan.py','--out',str(V)];virtual.main(emit=receive);assert len(new)==16 and sum((O/x['relative_path']).stat().st_size for x in new.values())==1064600;assert json.loads((V/'virtual-repeat16.json').read_text())==plan
 # Existing compact126 are referenced, never copied/rewritten; nine unlisted keys follow the approved original behavior rule.
 selected=[];checks=json.loads((A/'policy-classification.json').read_text());bykey={x['original_key']:x for x in checks['checks']};count=missing=0;policyrefs=[]
 for row in original['selected']:
  x=copy.deepcopy(new.get(row['original_key'],row));x['policy_qualified']=True
  if row['original_key']not in new:x['relative_path']=str(A/row['relative_path'])
  refs=[]
  for ref in bykey[row['original_key']]['refs']:
   y=dict(ref);candidate_class=ref['source_class']if row['original_key']in new else ref['candidate_class'];assert candidate_class==ref['source_class']
   if ref['shipped_class']is None:
    assert ref['room']in('r10c','r10d','r10e');y['acceptance']='INTENTIONAL_UNLISTED_BEHAVIOR_EQUIVALENT';missing+=1
   else:assert candidate_class==ref['shipped_class'];y['acceptance']='SOURCE_AND_CANDIDATE_EQUAL_SHIPPED_R4TC';count+=1
   y['selected_candidate_class']=candidate_class;refs.append(y)
  x['policy_acceptance']='INTENTIONAL_UNLISTED_BEHAVIOR_EQUIVALENT_AND_ANY_PRESENT_PROFILE_MATCH'if any(y['shipped_class']is None for y in refs)else'SOURCE_AND_CANDIDATE_EQUAL_SHIPPED_R4TC';selected.append(x);policyrefs.append(dict(original_key=row['original_key'],scoped_key=x['scoped_key'],refs=refs))
 assert len(selected)==142 and count==468 and missing==40
 final=copy.deepcopy(original);final.update(status='PRIVATE142_SOURCE_BEHAVIOR_EQUIVALENT_PROPOSAL',converted_keys=142,held=[],selected=selected,policy_gate_source_and_candidate_equal_shipped_R4TC=False,policy_gate_original_behavior_equivalent=True,policy_qualified_keys=142,strict_shipped_refs=468,intentional_unlisted_refs=40,unlisted_index_sha256='0de3651c279fb698178f980afe3db10e73df1b2702dc690cc91b5e4dcaa45804');emitjson(O/'policy-qualified-receipt.json',final);emitjson(O/'policy-alias-proof.json',dict(records=policyrefs,shipped_class_refs=468,intentional_unlisted_refs=40,not_shipped_class_match_for_unlisted=True));emitjson(O/'conversion-receipt.json',dict(selected=list(new.values()),new_package_versions=16,new_unique_source_assets=0,seconds=time.monotonic()-start,input_plan_sha256=H((P/'PLAN.json').read_bytes())))
 # Source-pinned immutable real Package readers: strict body CRC1 and both adopt/stream paths.
 T=Path('/root/re4data/private/texture-rect21-next18-twiddled-20261022-v1');Q=Path('/root/re4data/private/texture-rect21-next177-20261022-v2');tr=json.loads((T/'host-gate.json').read_text());qr=json.loads((Q/'host-gate.json').read_text());readers={'on':T/'host/reader-on','cast-off':Q/'host/reader-off','twiddled-off':Q/'host/reader-on'};assert H(readers['on'].read_bytes())==tr['binaries'][str(readers['on'])];assert H(readers['cast-off'].read_bytes())==qr['outputs']['off']['exe_sha256'];assert H(readers['twiddled-off'].read_bytes())==qr['outputs']['on']['exe_sha256']
 for p,h in tr['source_pins'].items():assert H(Path(p).read_bytes())==h
 results={}
 for mode,exe in readers.items():
  rows=list(new.values())if mode!='twiddled-off'else[x for x in new.values()if x['payload_type']==1];r=run([str(exe),*[str(O/x['relative_path'])for x in rows]]);write(O/'host'/('output-'+mode+'.txt'),r.stdout+r.stderr);assert r.returncode==0 and not r.stderr;lines=r.stdout.decode().splitlines()
  if mode=='on':
   assert len(lines)==2*len(rows)
   for i,x in enumerate(rows):assert lines[2*i]=='ok|ok'and int(lines[2*i+1].split(':')[1],16)==(0x90000000|(0x40000000 if x['payload_type']==2 else 0))
  else:assert len(lines)==len(rows)and all(x!='ok|ok'for x in lines)
  results[mode]=dict(exe=str(exe),sha256=H(exe.read_bytes()),cases=len(rows),PASS=True)
 neg=[]
 for layout in(1,2):
  row=next(x for x in new.values()if x['payload_type']==layout);b=(O/row['relative_path']).read_bytes()
  for kind in('legacy_texel_only_crc','payload_bit','truncated'):
   bad=bytearray(b)
   if kind=='legacy_texel_only_crc':struct.pack_into('<I',bad,36,zlib.crc32(bad[144:])&0xffffffff)
   elif kind=='payload_bit':bad[-1]^=1
   else:bad=bad[:-1]
   p=O/'host'/('negative-%d-%s.re4tex'%(layout,kind));write(p,bad);neg.append(str(p))
 r=run([str(readers['on']),*neg]);write(O/'host/output-negative.txt',r.stdout+r.stderr);assert not r.returncode and not r.stderr and len(r.stdout.decode().splitlines())==6 and all(x!='ok|ok'for x in r.stdout.decode().splitlines());emitjson(O/'host-gate.json',dict(status='PASS_ACTUAL_PACKAGE_REUSED_IMMUTABLE_READERS',outputs=results,corrupt_rejections=6,strict_adopt_and_stream_CRC1=True,source_pins=tr['source_pins'],limits=['Host PVR stub; no native draw/look/netVRAM/performance/Dreamcast acceptance.','16 new package versions, no additional unique source assets.']))
 p=run([sys.executable,str(HERE/'batch_propose.py'),str(O),str(T)],timeout=40);write(O/'world-propose-output.txt',p.stdout+p.stderr);assert not p.returncode
 guard();print(json.dumps(dict(new_packages=16,final_alpha_policy=142,shipped_refs=count,unlisted_refs=missing,seconds=time.monotonic()-start,bytes=size(O))))
if __name__=='__main__':
 try:main()
 except Exception as exc:
  if O.exists()and not(O/'FAILURE.json').exists():emitjson(O/'FAILURE.json',dict(error=repr(exc),preserve_no_retry=True))
  raise