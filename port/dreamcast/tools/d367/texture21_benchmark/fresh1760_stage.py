#!/usr/bin/env python3
"""Private fresh1760 bind/write adapter. Programme must be qualified; default writes no image."""
import os,sys
if not sys.dont_write_bytecode:raise RuntimeError('disable bytecode before local imports')
import argparse,ast,contextlib,ctypes,hashlib,json,struct,time
from pathlib import Path
from file_charge import WinPin,safe_path
from native_c_source_binding21 import proof,check_handle
from immutable_append1760_native_c_writer import Budget,write_one,copy_blocks,sha,json_new,FLOOR,PEER,file_charge
from plan_fresh1760_disc import SOURCE,BASE_SHA,M1_SHA,PROGRAMME_PATHS,rounded,require,directory
from mipmap_pair_plan import local,both32
from fresh1760_readback import verify_image
PLAN_ROOT=r'C:\Flycast-Evidence\re4-dreamcast\texture21-benchmark-20261021\fresh1760-disc-plan-01'
PLAN_SEAL='2e0d2afc61ae64ac1175e67bbcab223b6ad7cb2a45661f5d255b58cc5c72c917'
PAIR_ROOT=r'C:\Flycast-Evidence\re4-dreamcast\texture21-benchmark-20261021\fresh1760-pair-01'
ALLOCATION_ROOT=r'C:\Game Dev\Emulators\codex-lanes\texture21-benchmark'
CONTROLLER=r'C:\Game Dev\Emulators\codex-lanes\castle-controls21\owned-windows-fresh1760-image-job.py'
CAP=1342177280;META_CAP=16*1024**2;PROGRAMME_CAP=64*1024**2;CHUNK=1048576
ALPHA_MIRROR=r'C:\Flycast-Evidence\re4-dreamcast\texture-rect21-20261021\alpha-repeat16-batch-01'
ALPHA_SEAL='b35ac6c50694eea276d5e537de8fbf20c985a7470f19d4b32444227d77d5898f'

def source_pins(root=None):
 """Exact recursive local import sources, including conditional module imports."""
 root=Path(root or __file__).parent if root is None else Path(root);todo=['fresh1760_stage','fresh1760_readback'];found={}
 while todo:
  name=todo.pop();p=root/(name+'.py')
  if name in found:continue
  require(p.is_file()and not p.is_symlink(),'local source missing/alias');found[name]=sha(p)
  for node in ast.walk(ast.parse(p.read_text())):
   names=[a.name.split('.')[0]for a in node.names]if isinstance(node,ast.Import)else[node.module.split('.')[0]]if isinstance(node,ast.ImportFrom)and node.module else[]
   todo.extend(n for n in names if(root/(n+'.py')).is_file()and n not in found)
 return {n+'.py':h for n,h in sorted(found.items())}

class StageBudget(Budget):
 """Inherited aggregate guards plus independently bounded non-disc metadata."""
 def check(self,path=None,upcoming=0,force=False):
  charge=super().check(path,upcoming,force);now=self.clock()
  if force or not hasattr(self,'meta_last')or now-self.meta_last>=.2 or(path is not None and not Path(path).is_relative_to(self.roots[0]/'gdemu')):
   total=0
   for p in self.roots[0].rglob('*'):
    if p.is_file()and not p.is_relative_to(self.roots[0]/'gdemu'):safe_path(p,self.roots[0]);total+=file_charge(p,p.stat().st_size)
   if path is not None and not Path(path).is_relative_to(self.roots[0]/'gdemu'):total+=(upcoming+4095)//4096*4096
   require(total+self.reserve<=META_CAP,'metadata prospective quota');self.meta_last=now
  require(self.clock()-self.start<self.seconds,'inner deadline after metadata query');return charge

def hash_spec(spec):
 p=local(spec['path']);require(sha(p)==spec['sha256'],'receipt/input changed '+str(p));return json.loads(p.read_text())
def qualified_programme(admission):
 """Explicit new-source admission plus underlying source/independent/consumer/tool proofs."""
 require(admission['schema']=='qualified792-programme-stage-admission-v1'and admission['qualified']is True and admission['source']==SOURCE,'qualified792 root admission required')
 q=hash_spec(admission['qualification']);ind=hash_spec(admission['independent']);consumer=hash_spec(admission['consumer']);tool=hash_spec(admission['tool_closure']);manifest=hash_spec(admission['manifest'])
 require(q.get('runtime_source',q.get('source'))==SOURCE and q.get('full_source_programme_gate')is True and q.get('source_inputs_immutable')is True,'actual full source programme qualification')
 require(ind.get('canonical_runtime_source',ind.get('source'))==SOURCE and ind.get('fullprogram_source_gate')is True and ind.get('source_or_external_inputs_changed_during_unit')is False,'actual independent programme qualification')
 require(consumer.get('source')==SOURCE and consumer.get('new_programme_qualified')is True and consumer.get('all_consumer_gates_qualified')is True,'qualified linked792 consumer receipt required')
 require(tool.get('source')==SOURCE and tool.get('qualified')is True and tool.get('complete_actual_exec_plugin_tool_closure')is True and tool.get('new_unit_pre_post')is True,'new actual exec/plugin pre/post closure required')
 require(manifest['runtime_source']==SOURCE and manifest['qualification_sha256']==admission['qualification']['sha256'],'manifest new-source qualification binding')
 require(q['ELF_sha256']==ind['ELF_sha256']==manifest['ELF']['sha256']and q['programme_sha256']==ind['programme_sha256']==manifest['programme_sha256'],'programme/ELF proof join')
 require(q['all14_new_ELF_bound']is True and ind['all14_header_payload_relocation_CRC_and_newprogramme_binding_pass']is True and q['independent_qualification_sha256']==admission['independent']['sha256'],'all14 new programme/header binding')
 require(admission['actual_texture_crc_policy']==dict(resident=1,payload_crc=0),'preserve qualified original legacy stream route')
 need=('CAST_MIPMAP','TEX_TWIDDLED_MIPMAP','TEX_PAL4_ALPHA','TEX_PAL4_MIPMAP','TEX_PAL8_ALPHA','TEX_PAL8_MIPMAP');require(all(q['mip_PAL_flags_ON'].get(k)is True for k in need),'all actual six format flags ON')
 files={('/1ST_READ.BIN'if r['name']=='program.bin'else'/dc/'+r['name']):r for r in manifest['files15']};require(set(files)==set(PROGRAMME_PATHS)and len(manifest['files15'])==15,'exact15 programme outputs')
 for path,r in files.items():
  p=Path(r['Windows_path']);proof.canonical_c(p);require(p.stat().st_size==r['bytes']and sha(p)==r['sha256'],'actual programme bytes')
  if path=='/1ST_READ.BIN':require(r['sha256']==manifest['programme_sha256'],'boot raw hash')
  else:
   h=struct.unpack('<16I',p.read_bytes()[:64]);require(list(h)==r['header']and list(h[14:16])==manifest['image_id'],'actual overlay header/new imageID')
 elf=Path(manifest['ELF']['Windows_path']);proof.canonical_c(elf);require(elf.stat().st_size==manifest['ELF']['bytes']and sha(elf)==manifest['ELF']['sha256'],'actual new ELF')
 require(sum(rounded(r['bytes'])for r in files.values())<=PROGRAMME_CAP,'programme15 proposal cap; replan rather than silently grow');return manifest,files

class NativePins:
 """Read locks/fullSHA/current native identities; one checked Python reader per source."""
 def __init__(self,entries,record=False):self.entries=entries;self.record=record;self.stack=contextlib.ExitStack();self.files={};self.proofs={}
 def __enter__(self):
  try:
   seen=set()
   for e in self.entries:
    p=Path(e['path']);proof.canonical_c(p);safe_path(p,p.parent);held=self.stack.enter_context(WinPin(p,e['sha256']));final=proof.final_name(held);proof.require_same_path(p,final);info=held.INFO();require(held.k.GetFileInformationByHandle(held.h,ctypes.byref(info)),'native source info');now=dict(c_source_path=str(p),native_identity=held.initial,last_write_filetime=info.written.lo+(info.written.hi<<32),native_final_path=final);identity=(held.initial['volume_serial'],held.initial['file_index']);require(identity not in seen and held.initial['logical_bytes']==e['bytes'],'source native alias/size');seen.add(identity)
    if not self.record:require(now==e['native'],'source FileID/mtime/link/finalpath changed since bind')
    f=self.stack.enter_context(p.open('rb'));check_handle(f,now);self.files[str(p)]=f;self.proofs[str(p)]=now
   return self
  except BaseException:self.stack.close();raise
 def __exit__(self,*args):
  try:
   for p,f in self.files.items():check_handle(f,self.proofs[p])
  finally:self.stack.close()
 def read(self,path,offset,n):
  f=self.files[str(Path(path))];f.seek(offset);b=f.read(n);require(len(b)==n,'source truncated');return b

class ReadBudget:
 def __init__(self,seconds=60):self.start=time.perf_counter();self.seconds=seconds;self.last=0
 def check(self,*args,**kw):
  require(time.perf_counter()-self.start<self.seconds,'source bind deadline')
  if os.name=='nt'and time.perf_counter()-self.last>=.2:
   import shutil
   require(shutil.disk_usage('C:\\').free>=FLOOR+PEER,'source peer floor');self.last=time.perf_counter()
  require(time.perf_counter()-self.start<self.seconds,'source deadline after native query')

def stream_image(plan,arm,pins,guard):
 """Patch only prefix metadata; append selected bodies with exact source SHA/padding."""
 patches=plan['arms'][arm]['patches'];seen=[0]*len(patches);last=-1
 for p in sorted(patches,key=lambda x:x['start']):require(p['start']>=last and len(bytes.fromhex(p['before']))==len(bytes.fromhex(p['after'])),'patch overlap/length');last=p['start']+len(bytes.fromhex(p['before']))
 h=hashlib.sha256();n=plan['base']['bytes'];base=plan['base']['path']
 for pos in range(0,n,CHUNK):
  guard.check();raw=pins.read(base,pos,min(CHUNK,n-pos));h.update(raw);buf=bytearray(raw)
  for i,p in enumerate(patches):
   old=bytes.fromhex(p['before']);new=bytes.fromhex(p['after']);lo=max(pos,p['start']);hi=min(pos+len(buf),p['start']+len(old))
   if lo<hi:
    a=lo-p['start'];b=hi-p['start'];require(buf[lo-pos:hi-pos]==old[a:b],'metadata before bytes differ');buf[lo-pos:hi-pos]=new[a:b];seen[i]+=hi-lo
  yield bytes(buf)
 require(h.hexdigest()==plan['base']['sha256']and all(seen[i]==len(bytes.fromhex(p['before']))for i,p in enumerate(patches)),'base SHA/patch coverage')
 cursor=n
 for r in plan['arms'][arm]['append']:
  require(r['start']==cursor and r['reserved_bytes']>=r['bytes']and r['reserved_bytes']%2048==0,'append contiguous/exact reservation');member=hashlib.sha256()
  for off in range(0,r['bytes'],CHUNK):guard.check();b=pins.read(r['source_path'],r['source_offset']+off,min(CHUNK,r['bytes']-off));member.update(b);yield b
  require(member.hexdigest()==r['sha256'],'append source member SHA');pad=r['reserved_bytes']-r['bytes']
  while pad:guard.check();k=min(CHUNK,pad);yield bytes(k);pad-=k
  cursor+=r['reserved_bytes']
 require(cursor==plan['image_bytes'],'final image size')

def fixed_source_plan():
 root=Path(PLAN_ROOT);require(sha(root/'UNIT-SHA256SUMS')==PLAN_SEAL,'fixed fresh data unit seal')
 for line in(root/'UNIT-SHA256SUMS').read_text().splitlines():
  h,n=line.split('  ',1);rel=Path(n);require(not rel.is_absolute()and'..'not in rel.parts and sha(root/rel)==h,'fixed data input drift')
 return root,json.loads((root/'PLAN.json').read_text()),json.loads((root/'ASSET-APPEND-LAYOUT.json').read_text()),json.loads((root/'DIRECTORY-PATCH-CONTRACT.json').read_text())

def bind(admission_path,admission_sha,out):
 require(os.name=='nt'and not out.exists(),'native bind/fresh metadata path required');require(sha(admission_path)==admission_sha,'root programme admission hash');admission=json.loads(admission_path.read_text());manifest,programmes=qualified_programme(admission);root,data,layout,dc=fixed_source_plan();base=local(data['base']['path']);candidate=local(data['M1_pack']['path']);basefile=json.loads(local(data['base']['all1743readback_path']).read_text())['files'];small={n:dict(path=str(base.parent/n),bytes=(base.parent/n).stat().st_size,sha256=sha(base.parent/n))for n in('track01.bin','track02.raw','disc.gdi')}
 mirror_root=Path(ALPHA_MIRROR);require(sha(mirror_root/'SHA256SUMS.txt')==ALPHA_SEAL,'explicit candidate world C mirror provenance');mirror_manifest={n.replace('\\','/'):h for h,n in(line.split('  ',1)for line in(mirror_root/'SHA256SUMS.txt').read_text().splitlines())}
 app={'M0':[],'M1':[]};cursor=layout['assetprefix_end_bytes'];common=[]
 for path in PROGRAMME_PATHS:
  r=programmes[path];common.append(dict(path=path,start=cursor,source_path=str(Path(r['Windows_path'])),source_offset=0,bytes=r['bytes'],reserved_bytes=rounded(r['bytes']),sha256=r['sha256']));cursor+=rounded(r['bytes'])
 for arm in app:
  for r in layout['assets']:
   x=r[arm];source=str(base)if arm=='M0'else str(candidate)if r['path']=='/dc/tex.pak'else str(mirror_root/'proposed-worlds'/r['path'].lstrip('/'))
   if arm=='M1'and r['path']!='/dc/tex.pak':require(mirror_manifest.get('proposed-worlds/'+r['path'].lstrip('/'))==x['sha256']and sha(Path(source))==x['sha256'],'explicit candidate world mirror bytes')
   app[arm].append(dict(path=r['path'],start=(r['new_extent']-45000)*2048,source_path=source,source_offset=x.get('source_offset',0),bytes=x['bytes'],reserved_bytes=r['reserved_bytes'],sha256=x['sha256']))
  app[arm]+=common
 plan=dict(schema='fresh1760-paired-image-plan-v1',status='BOUND_STATIC_PREDICTIONS_ONLY_UNALLOCATED',source=SOURCE,source_sha256=source_pins(),programme=manifest,programme_admission=dict(path=str(admission_path),sha256=admission_sha),data_unit=dict(path=str(root/'UNIT-SHA256SUMS'),sha256=PLAN_SEAL),baseline=dict(path=str(local(data['base']['all1743readback_path'])),sha256=data['base']['all1743readback_sha256']),base=dict(path=str(base),bytes=data['base']['bytes'],sha256=data['base']['sha256']),image_bytes=cursor,smalltracks=small,file_count=1743,record_count=1874,held=['r11f','r200'],arms={},native_sources=[],proposal=dict(cap_bytes=CAP,metadata_cap=META_CAP,programme_cap=PROGRAMME_CAP,inner_seconds=120,outer_seconds=130,runtime_floor=FLOOR,peer=PEER,allocated=False),guest_scope='FirstcoldM1functional only after root allocation/readback/freshABI; no all1760draw or121frame condition for boot')
 for arm,rows in app.items():
  by={r['path']:r for r in rows};patches=[dict(start=16*2048+80,before=both32(dc['PVD_before']).hex(),after=both32(cursor//2048).hex())]
  for r in dc['records']:
   new=by[r['path']];before=bytes.fromhex(r['original_record_hex']);patches.append(dict(start=r['extent_LE_BE_offset'],before=before[2:10].hex(),after=both32(45000+new['start']//2048).hex()));patches.append(dict(start=r['size_LE_BE_offset'],before=before[10:18].hex(),after=both32(new['bytes']).hex()))
  plan['arms'][arm]=dict(append=rows,patches=patches)
 inputs={str(base):dict(path=str(base),bytes=plan['base']['bytes'],sha256=plan['base']['sha256'])}
 for arm in app.values():
  for r in arm:
   p=r['source_path']
   if p==str(base):continue
   entry=dict(path=p,bytes=Path(p).stat().st_size,sha256=sha(Path(p)))
   if p in inputs:require(inputs[p]==entry,'shared source conflict')
   inputs[p]=entry
 for r in small.values():inputs[r['path']]=r
 plan['native_sources']=list(inputs.values())
 with NativePins(plan['native_sources'],record=True)as pins:
  for e in plan['native_sources']:e['native']=pins.proofs[str(Path(e['path']))]
  guard=ReadBudget(60)
  for arm in plan['arms']:
   h=hashlib.sha256();n=0
   for b in stream_image(plan,arm,pins,guard):h.update(b);n+=len(b)
   require(n==cursor,'predicted byte count');plan['arms'][arm]['predicted']=dict(bytes=n,sha256=h.hexdigest())
 exact=(cursor+4095)//4096*4096+sum((r['bytes']+4095)//4096*4096 for r in small.values())+META_CAP;require(exact<=CAP,'concrete firstimage proposal exceeds1.25GiB; root replan required');plan['proposal']['exact_uncompressed_forecast_bytes']=exact;json_new(out,plan);return plan

def root_allocation(plan,plan_path,plan_sha,path,digest,arm):
 require(sha(path)==digest and sha(plan_path)==plan_sha,'root plan/allocation bytes');a=json.loads(path.read_text());root=Path(PAIR_ROOT)/arm;expected=dict(stage_authorized=True,candidate_contract_valid=True,source=SOURCE,arm=arm,plan_sha256=plan_sha,writer_source_sha256=sha(__file__),allocation_cap_bytes=CAP,metadata_cap_bytes=META_CAP,peer_reserved_bytes=PEER,runtime_floor_bytes=FLOOR,inner_seconds=120,approved_output_root=str(root),controller_path=CONTROLLER)
 require(all(a.get(k)==v for k,v in expected.items()),'exact root stage allocation');require(a.get('allocation_id')and a.get('controller_source_sha256')==sha(Path(CONTROLLER)),'actual owned controller source pin');require(Path(path).parent==Path(ALLOCATION_ROOT)and not Path(path).is_relative_to(root),'childA outside output root');require(not a.get('compression_credits'),'no compression credits in fresh one-arm allocation');require(arm=='M1'or a.get('candidate_M1_closed_readback_sha256'),'candidate-first before M0');return root,a

def write_json_owned(path,value,guard):
 raw=(json.dumps(value,indent=2)+'\n').encode();require(len(raw)<=2*1024**2,'bounded stage metadata');guard.claim(path);guard.check(path,len(raw))
 with Path(path).open('xb')as f:f.write(raw);f.flush();os.fsync(f.fileno())
 guard.commit(path,len(raw))

def execute(plan_path,plan_sha,allocation_path,allocation_sha,arm):
 require(os.name=='nt','native owned-job execution only');require(sha(plan_path)==plan_sha,'bound plan bytes');plan=json.loads(plan_path.read_text());require(plan['source_sha256']==source_pins(),'entire local source dependency binding');require(plan['schema']=='fresh1760-paired-image-plan-v1'and plan['source']==SOURCE and plan['programme']['runtime_source']==SOURCE,'new qualified source only');root,a=root_allocation(plan,plan_path,plan_sha,allocation_path,allocation_sha,arm);prefix=str(root/'pycache');require(sys.dont_write_bytecode and os.environ.get('PYTHONDONTWRITEBYTECODE')=='1'and sys.pycache_prefix==prefix and os.environ.get('PYTHONPYCACHEPREFIX')==prefix and not Path(prefix).exists(),'both startup bytecode gates/fresh prefix');require(root.is_dir()and not(root/'gdemu').exists(),'root preparedmetadata only/fresh gdemu');require(sha(local(plan['programme_admission']['path']))==plan['programme_admission']['sha256'],'programme admission unchanged');qualified_programme(json.loads(local(plan['programme_admission']['path']).read_text()));fixed_source_plan()
 require(plan['proposal']['exact_uncompressed_forecast_bytes']<=CAP and plan['image_bytes']<=CAP-META_CAP,'bounded exact output proposal');guard=StageBudget([root],CAP,FLOOR+PEER,120);guard.check(force=True)
 import shutil
 require(shutil.disk_usage('C:\\').free>=FLOOR+PEER+plan['proposal']['exact_uncompressed_forecast_bytes'],'fresh complete oneimage headroom')
 result=dict(status='FAILED',arm=arm,allocation_id=a['allocation_id'],plan_sha256=plan_sha,writer_sha256=sha(__file__),images_written=0,no_target_or_performance_acceptance=True)
 try:
  with NativePins(plan['native_sources'])as pins:
   gdemu=root/'gdemu';gdemu.mkdir()
   for name,r in plan['smalltracks'].items():
    def source_small(r=r):
     for off in range(0,r['bytes'],CHUNK):guard.check();yield pins.read(r['path'],off,min(CHUNK,r['bytes']-off))
    verify=lambda p,r=r:dict(sha256=sha(p))if sha(p)==r['sha256']else(_ for _ in()).throw(ValueError('smalltrack SHA'))
    write_one(gdemu/name,source_small(),r['bytes'],r['sha256'],verify,guard)
   image=gdemu/'track03.iso';inspect=lambda p:verify_image(p,plan,arm,guard);proof=write_one(image,stream_image(plan,arm,pins,guard),plan['image_bytes'],plan['arms'][arm]['predicted']['sha256'],inspect,guard);proof['track_path']=str(image);write_json_owned(root/'full-readback.json',proof,guard);guard.check(force=True);result.update(status='PASS_STATIC_IMAGE_ONLY',images_written=1,image_path=str(image),image_sha256=proof['sha256'],image_bytes=proof['bytes'],all1743_readback=True,explicit43_relocations=True,all15_newprogramme_bound=True,job_closure='Root external retainedJob controller must independently certify wholejob empty/handlesclosed')
 except BaseException as e:
  result['error']=type(e).__name__+': '+str(e)
  try:write_json_owned(root/'child-result.json',result,guard)
  finally:raise
 else:write_json_owned(root/'child-result.json',result,guard)
 return result

def main():
 ap=argparse.ArgumentParser(description=__doc__);sub=ap.add_subparsers(dest='action',required=True);b=sub.add_parser('bind');b.add_argument('--admission',type=Path,required=True);b.add_argument('--admission-sha256',required=True);b.add_argument('--out',type=Path,required=True);w=sub.add_parser('write')
 for n in('plan','allocation'):w.add_argument('--'+n,type=Path,required=True)
 for n in('plan-sha256','allocation-sha256'):w.add_argument('--'+n,required=True)
 w.add_argument('--arm',choices=['M0','M1'],required=True);a=ap.parse_args();r=bind(a.admission,a.admission_sha256,a.out)if a.action=='bind'else execute(a.plan,a.plan_sha256,a.allocation,a.allocation_sha256,a.arm);print(json.dumps({k:v for k,v in r.items()if k not in('arms','native_sources','programme')}))
if __name__=='__main__':main()
