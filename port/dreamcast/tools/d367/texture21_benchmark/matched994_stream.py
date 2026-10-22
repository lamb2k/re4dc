#!/usr/bin/env python3
"""Frozen994 pair: virtual hashes by default; explicitly allocated one-arm writer.

No pack composition, image mounting, game build, guest or state operation.
"""
import argparse,hashlib,json,os,shutil,struct,time,zlib
from pathlib import Path
from mipmap_pair_plan import sha,local,record_patch,both32,programme_rows,OLD_C
TRACK=1032499200;FLOOR=18*1024**3
def check_sources(rows):
 for r in rows:
  p=local(r['source_path'])
  if p.stat().st_size!=r['bytes']or sha(p)!=r['sha256']:raise ValueError('source changed: '+str(p))
def blocks(plan,arm):
 """Every source range read bounded; whole historical C rehashed each pass."""
 rows=plan['common_ranges']+plan['arms'][arm]['ranges'];patches=plan['arms'][arm]['patches'];ranges=sorted(rows,key=lambda r:r['start'])
 if any(x['end']>y['start']for x,y in zip(ranges,ranges[1:])):raise ValueError('payload overlap')
 base=hashlib.sha256();done=0;pos=0
 with local(plan['base_path']).open('rb')as f:
  while data:=f.read(1048576):
   base.update(data);b=bytearray(data);end=pos+len(b)
   for r in ranges:
    lo=max(pos,r['start']);hi=min(end,r['end'])
    if lo>=hi:continue
    off=lo-r['start'];n=hi-lo;take=max(0,min(n,r['bytes']-off))
    with local(r['source_path']).open('rb')as src:src.seek(off);s=src.read(take)
    if len(s)!=take:raise ValueError('source truncated')
    if r['path']=='/1ST_READ.BIN':
     oldend=r['start']+((r['before_bytes']+2047)//2048)*2048
     if hi>max(lo,oldend)and any(data[max(lo,oldend)-pos:hi-pos]):raise ValueError('nonzero tail growth')
    b[lo-pos:hi-pos]=s+bytes(n-take)
   for p in patches:
    start=p['start'];old=bytes.fromhex(p['before']);new=bytes.fromhex(p['after'])
    if pos<=start<end:
     if start+len(old)>end or b[start-pos:start-pos+len(old)]!=old:raise ValueError('directory/PVD precondition')
     b[start-pos:start-pos+len(old)]=new;done+=1
   pos=end;yield bytes(b)
 if pos!=TRACK or base.hexdigest()!=OLD_C or done!=len(patches):raise ValueError('base identity/metadata coverage')
def predicted(plan,arm,gzip=False):
 h=hashlib.sha256();c=hashlib.sha256();n=cn=0;co=zlib.compressobj(1,zlib.DEFLATED,31)
 for b in blocks(plan,arm):
  h.update(b);n+=len(b)
  if gzip:s=co.compress(b);c.update(s);cn+=len(s)
 result=dict(bytes=n,sha256=h.hexdigest())
 if gzip:
  s=co.flush();c.update(s);cn+=len(s);result.update(gzip_level1_bytes=cn,gzip_level1_sha256=c.hexdigest(),gzip_zlib_version=zlib.ZLIB_VERSION,gzip_runtime_version=zlib.ZLIB_RUNTIME_VERSION)
 return result
def create(a):
 a.out.mkdir(exist_ok=False);sp=json.loads(a.layout.read_text());selected=sp['selected_paths'];prog=json.loads(a.programme.read_text());assert prog['source']==a.source
 common=programme_rows(prog,selected,TRACK);patches=[]
 for r in common:patches+=record_patch(selected[r['path']],r['bytes'])
 boot=next(r for r in common if r['path']=='/1ST_READ.BIN');newvol=max(504000,547365-45000+(boot['bytes']+2047)//2048);assert newvol<=504150
 if newvol!=504002:patches.append({'start':16*2048+80,'before':both32(504002).hex(),'after':both32(newvol).hex(),'kind':'PVD_volume_space'})
 baseline=json.loads(a.baseline.read_text())['files'];manifest=json.loads(a.combined.read_text());assert sha(a.combined)==a.combined_sha256
 def row(path,source,size,digest):
  b=selected[path]['before']if path in selected else baseline[path];start=(b['extent']-45000)*2048;cap=(b['bytes']+2047)//2048*2048;assert size<=cap
  return dict(path=path,source_path=str(source),bytes=size,sha256=digest,start=start,end=start+cap)
 original=local(a.original_pack);candidate=local(a.candidate_pack);assert sha(original)=='18fcee11491f2c1f212863d6d6b572b3997f691b2e990217e1c2518f134021ef' and sha(candidate)==manifest['virtual']['pack_sha256'] and candidate.stat().st_size==manifest['virtual']['pack_bytes']
 m0=[row('/dc/tex.pak',original,156254208,sha(original))];m1=[row('/dc/tex.pak',candidate,candidate.stat().st_size,sha(candidate))]
 for room in ['r100','r103']:
  path='/dc/native/'+room+'/ps2-world.r4pw';s=selected[path];p=a.original_worlds/path.lstrip('/');m0.append(row(path,p,s['before']['bytes'],s['before']['sha256']))
 # Repaired aliases may change every candidate sidecar. Never silently reuse
 # historical C r100/r103 when a new CRC/rekey manifest has been selected.
 source_map=json.loads(a.candidate_worlds.read_text());assert set(source_map)=={'/dc/native/'+r+'/ps2-world.r4pw'for r in ['r100','r103','r101']}
 for item in manifest['sidecars']:
  path='/'+item['path'];new=source_map[path];expected=item.get('candidate',{}).get('sha256',item.get('output_sha256'));assert new['sha256']==expected
  m1.append(row(path,local(new['source_path']),new['bytes'],new['sha256']))
 arms={}
 for name,rows in [('M0',m0),('M1',m1)]:
  pp=list(patches)
  pp+=record_patch(selected['/dc/tex.pak'],rows[0]['bytes'])
  for r in rows:
   if r['path']in selected and r['path']!='/dc/tex.pak':pp+=record_patch(selected[r['path']],r['bytes'])
  arms[name]={'ranges':rows,'patches':pp}
 plan={'schema':'matched994-stream-plan1','status':'PREDICTED_ONLY_NO_STAGE_ALLOCATION','source':a.source,'base_path':str(a.base),'base_sha256':OLD_C,'track_bytes':TRACK,'programme_binding_path':str(a.programme),'programme_binding_sha256':sha(a.programme),'elf_sha256':prog['elf_sha256'],'common_exact15':prog['files'],'common_ranges':common,'arms':arms,'asset_differences_between_arms':['/dc/tex.pak','/dc/native/r100/ps2-world.r4pw','/dc/native/r103/ps2-world.r4pw','/dc/native/r101/ps2-world.r4pw'],'comparison':'FULL texture pipeline, original6501 versus combined994. Original control retains protected existing mipmaps; not globally mip-off, not isolated mip-only causal claim.','no_e08_namespace_or_state_transfer':True,'runtime_new_ELF_binding':'PENDING fresh f42 CU/DIE/path/pointer/duplicate/anchor namespace; no boot/performance acceptance','layout':{'files':1743,'all_LBAs_preserved':True,'Joliet':False,'PVD_blocks':504002,'fulltrack_blocks':504150,'programme_tail_remaining_sectors':148},'resource':{'floor_bytes':FLOOR,'runtime_margin':67108864,'smalltracks_and_GDI_per_arm':2295639,'metadata_cap':16777216,'failed_outputs':'Preserve and count all prior failed/closed output bytes plus peer reservations; no automatic retry/cleanup.'}}
 check_sources(common+m0+m1)
 plan['source']=a.source;plan['layout']['PVD_blocks']=newvol;plan['layout']['programme_tail_remaining_sectors']=504150-newvol
 plan['runtime_new_ELF_binding']='PENDING actual '+prog['elf_sha256']+' CU/DIE/path/pointer/duplicate/anchor namespace; no boot/performance acceptance'
 plan['input_refs']={str(p):sha(p)for p in [a.programme,a.layout,a.baseline,a.combined,a.candidate_worlds]}
 plan['materialization']='Root allocation only. ONE candidate arm FIRST, full1743 file/directory readback; main applies NTFS lossless compression to that closed owned file, rehashes same logical bytes and records actual allocation/free bytes. Fresh guard before original arm SECOND; preserve and count failed/closed outputs. No automatic deletion/retry.'
 plan['compression']='NTFS is root-owned external operation after fullreadback; ntfs_image_readback.py records same logical identity and actual Windows allocation. Gzip is not part of this stage plan.'
 for arm in arms:arms[arm]['predicted']=predicted(plan,arm)
 with(a.out/'stream-plan.json').open('x')as f:json.dump(plan,f,indent=2);f.write('\n')
 print(json.dumps({'plan_sha256':sha(a.out/'stream-plan.json'),'predicted':{k:v['predicted']for k,v in arms.items()},'images_written':0}))
def guard(a,plan,remaining):
 # Global peer reservation is supplied fresh by main, never inferred as zero.
 free=shutil.disk_usage(a.output.parent).free
 if free<FLOOR+67108864+a.peer_reserved+remaining:raise ValueError('fresh disk/reservation guard')
 allocated=sum(p.stat().st_size for p in a.allocation_root.rglob('*')if p.is_file()and not p.is_symlink())
 if allocated+remaining>a.allocation_cap:raise ValueError('cumulative failed/closed allocation cap')
 return free,allocated
class WriterGuard:
 """Prospective-byte accounting each chunk, expensive probes at most5Hz."""
 def __init__(self,a,plan,total):
  self.a=a;self.plan=plan;self.total=total;self.start=time.monotonic();self.last=self.start;self.written=0;self.free,self.allocated=guard(a,plan,total);self.checkpoint=0
 def advance(self,n):
  prospective=self.written+n
  if prospective>self.total:raise ValueError('prospective allocation exceeded')
  if self.allocated+(prospective-self.checkpoint)>self.a.allocation_cap:raise ValueError('allocation cap')
  if self.free-(prospective-self.checkpoint)<FLOOR+67108864+self.a.peer_reserved:raise ValueError('runtime reserve')
  now=time.monotonic()
  if now-self.start>120:raise TimeoutError('writer120s hard deadline; preserve partial')
  if now-self.last>=0.2:
   self.free,self.allocated=guard(self.a,self.plan,self.total-self.written);self.checkpoint=self.written;self.last=now
  self.written=prospective
def write(a):
 plan=json.loads(a.plan.read_text());assert sha(a.plan)==a.plan_sha256
 admission=json.loads(a.allocation_receipt.read_text());assert admission['plan_sha256']==a.plan_sha256 and admission['arm']==a.arm and admission['stage_authorized']is True and admission['candidate_contract_valid']is True
 assert a.arm in plan['arms']and not a.output.exists()and a.output.parent.exists();prediction=plan['arms'][a.arm]['predicted'];check_sources(plan['common_ranges']+plan['arms'][a.arm]['ranges']);guard(a,plan,TRACK)
 assert a.output.resolve().is_relative_to(a.allocation_root.resolve())
 small={name:a.smalltracks/name for name in ['track01.bin','track02.raw','disc.gdi']};small_hashes={name:sha(p)for name,p in small.items()};total=TRACK+sum(p.stat().st_size for p in small.values())
 assert a.smalltracks.resolve()==local(plan['base_path']).parent.resolve()
 partial=a.output.with_name(a.output.name+'.partial');assert not partial.exists();h=hashlib.sha256();n=0;wg=WriterGuard(a,plan,total)
 with partial.open('xb')as f:
  for b in blocks(plan,a.arm):
   wg.advance(len(b));f.write(b);h.update(b);n+=len(b)
  f.flush();os.fsync(f.fileno())
 if n!=prediction['bytes']or h.hexdigest()!=prediction['sha256']:raise ValueError('closed image differs; preserve partial')
 partial.rename(a.output)
 for name,p in small.items():
  with p.open('rb')as src,(a.output.parent/name).open('xb')as dst:
   while b:=src.read(1048576):wg.advance(len(b));dst.write(b)
   dst.flush();os.fsync(dst.fileno())
  assert sha(a.output.parent/name)==small_hashes[name]==sha(p)
 receipt={'arm':a.arm,'plan_sha256':sha(a.plan),'path':str(a.output),'bytes':n,'sha256':h.hexdigest(),'scope':'Writer closed wholeimage identity only; independent1743 directory/file readback remains mandatory before guest.'}
 with a.output.with_suffix('.writer.json').open('x')as f:json.dump(receipt,f,indent=2)
 print(json.dumps(receipt))
def main():
 ap=argparse.ArgumentParser(description=__doc__);sub=ap.add_subparsers(dest='action',required=True);p=sub.add_parser('plan')
 for n in ['layout','baseline','programme','combined','base','original-pack','candidate-pack','original-worlds','candidate-worlds','out']:p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--source',required=True);p.add_argument('--combined-sha256',required=True)
 for cmd in ['write']:
  p=sub.add_parser(cmd)
  for n in ['plan','output','allocation-root']:p.add_argument('--'+n,type=Path,required=True)
  for n in ['allocation-cap','peer-reserved']:p.add_argument('--'+n,type=int,required=True)
  p.add_argument('--plan-sha256',required=True);p.add_argument('--arm',choices=['M0','M1'],required=True)
  p.add_argument('--allocation-receipt',type=Path,required=True)
  p.add_argument('--smalltracks',type=Path,required=True)
 a=ap.parse_args();{'plan':create,'write':write}[a.action](a)
if __name__=='__main__':main()
