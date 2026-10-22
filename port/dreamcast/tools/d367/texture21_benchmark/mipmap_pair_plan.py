#!/usr/bin/env python3
"""Read-only virtual M0/original vs corrected965 full texture pipeline plan."""
import argparse,contextlib,hashlib,json,os,struct
from pathlib import Path
SECTOR=2048;LBA0=45000
ORIGINAL='18fcee11491f2c1f212863d6d6b572b3997f691b2e990217e1c2518f134021ef'
C965='bbcef25f0090fa4004e03331a33c84f8f89fd3582704e4a08945a8f6a15d5026'
OLD_C='13c998136f24212e39a86bc82a0dc54eb14bb8bacca38ca14cb855e2897309fd'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  while b:=f.read(1048576):h.update(b)
 return h.hexdigest()
def local(p):
 s=str(p)
 if os.name=='nt':
  if s.startswith('/mnt/c/'):return Path('C:/'+s[7:])
  if s.startswith('/root/'):return Path('//wsl.localhost/Ubuntu-24.04'+s)
 return Path(s)
def raw_read(f,offset,n):
 first,skip=divmod(offset,2048);count=(skip+n+2047)//2048;f.seek(first*2352);raw=f.read(count*2352)
 if len(raw)!=count*2352:raise ValueError('original raw sector read truncated')
 cooked=b''.join(raw[i+16:i+2064] for i in range(0,len(raw),2352));return cooked[skip:skip+n]
def both32(n):return struct.pack('<I',n)+struct.pack('>I',n)
def record_patch(selected,newbytes):
 out=[]
 if selected['after_bytes']!=newbytes:
  for r in selected['directory_records']:out.append({'start':(r['record_lba']-LBA0)*2048+r['record_offset']+10,'before':both32(selected['after_bytes']).hex(),'after':both32(newbytes).hex(),'kind':'directory_size','tree':r['tree']})
 return out
def programme_rows(manifest,selected,trackbytes):
 expected={p for p in selected if p=='/1ST_READ.BIN' or p.endswith('.ovl')}
 if set(manifest['files'])!=expected or len(expected)!=15:raise ValueError('exact boot plus all14 programme members required')
 if not manifest.get('source') or not manifest.get('elf_sha256') or not manifest.get('resolved_flags_sha256') or not manifest.get('compile_inputs_sha256'):raise ValueError('new source/ELF/flags/compile input binding required')
 out=[]
 for path,r in manifest['files'].items():
  s=selected[path];start=(s['after_extent']-LBA0)*2048;newsize=r['bytes'];source=local(r['source_path']);capacity=((s['before']['bytes']+2047)//2048)*2048
  if path=='/1ST_READ.BIN':capacity=trackbytes-start
  if not 0<newsize<=capacity:raise ValueError('new programme exceeds existing extent/verified tail: '+path)
  if source.stat().st_size!=newsize or sha(source)!=r['sha256']:raise ValueError('new programme source bytes changed: '+path)
  oldcap=((s['after_bytes']+2047)//2048)*2048;newcap=((newsize+2047)//2048)*2048
  out.append({'path':path,'start':start,'end':start+max(oldcap,newcap),'bytes':newsize,'sha256':r['sha256'],'kind':'file','source_path':str(source),'before_bytes':s['after_bytes'],'after_extent':s['after_extent']})
 return out
def virtual_hashes(base,rawpath,assets,common,patches):
 """Hash in bounded RAM; no image output handle ever exists."""
 hs=[hashlib.sha256(),hashlib.sha256()];basehash=hashlib.sha256();sourcehash={r['path']:hashlib.sha256() for r in assets};pos=0
 allranges=sorted(assets+common,key=lambda r:r['start'])
 if any(x['end']>y['start'] for x,y in zip(allranges,allranges[1:])):raise ValueError('payload ranges overlap')
 applied=[0,0]
 with Path(base).open('rb') as src,(Path(rawpath).open('rb') if rawpath else contextlib.nullcontext()) as original:
  while block:=src.read(1048576):
   basehash.update(block);end=pos+len(block);arms=[bytearray(block),bytearray(block)]
   for r in allranges:
    lo=max(pos,r['start']);hi=min(end,r['end'])
    if lo>=hi:continue
    off=lo-r['start'];n=hi-lo;used=max(0,min(n,r['bytes']-off))
    if r['kind']=='original_raw':
     data=raw_read(original,r['source_offset']+off,used);sourcehash[r['path']].update(data)
    else:
     with Path(r['source_path']).open('rb') as f:f.seek(off);data=f.read(used)
     if len(data)!=used:raise ValueError('new programme source truncated')
     if r['kind']=='original_file':sourcehash[r['path']].update(data)
    data+=bytes(n-used)
    for i in ([0] if r['kind'].startswith('original_') else [0,1]):arms[i][lo-pos:hi-pos]=data
    # Any expansion into old programme tail must consume verified zero bytes.
    if r['path']=='/1ST_READ.BIN':
     oldend=r['start']+((r['before_bytes']+2047)//2048)*2048
     if hi>max(lo,oldend) and any(block[max(lo,oldend)-pos:hi-pos]):raise ValueError('programme growth would overwrite nonzero tail')
   for i,changes in enumerate(patches):
    for r in changes:
     p=r['start'];old=bytes.fromhex(r['before']);new=bytes.fromhex(r['after'])
     if pos<=p<end:
      if p+len(old)>end or bytes(arms[i][p-pos:p-pos+len(old)])!=old:raise ValueError('metadata precondition differs')
      arms[i][p-pos:p-pos+len(new)]=new;applied[i]+=1
    hs[i].update(arms[i])
   pos=end
 if basehash.hexdigest()!=OLD_C:raise ValueError('historical C whole-track identity changed')
 for r in assets:
  if sourcehash[r['path']].hexdigest()!=r['sha256']:raise ValueError('original selected payload differs '+r['path'])
 if applied!=[len(p) for p in patches]:raise ValueError('metadata field not applied exactly once')
 return {'base_C_sha256':basehash.hexdigest(),'track_bytes':pos,'M0_sha256':hs[0].hexdigest(),'M1_sha256':hs[1].hexdigest(),'metadata_fields_applied':applied,'original_selected_payloads_verified':{r['path']:sourcehash[r['path']].hexdigest() for r in assets},'image_bytes_written':0,'maximum_base_chunk_bytes':1048576}
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--historical-plan',type=Path,required=True);ap.add_argument('--base-c',type=Path,required=True);ap.add_argument('--original-raw',type=Path);ap.add_argument('--original-pack',type=Path);ap.add_argument('--original-world-root',type=Path);ap.add_argument('--provenance',type=Path,required=True);ap.add_argument('--actor-composition',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--programme',type=Path);ap.add_argument('--virtual-hash',action='store_true');a=ap.parse_args()
 if not a.original_raw and not (a.original_pack and a.original_world_root):raise ValueError('exact original raw or recovered pack+two original world files required')
 a.out.mkdir(exist_ok=False);hp=json.loads((a.historical_plan/'image-plan.json').read_text());sp=json.loads((a.historical_plan/'scoped17-file-plan.json').read_text());sel=sp['selected_paths'];prov=json.loads(a.provenance.read_text());actor=json.loads(a.actor_composition.read_text());assert sel['/dc/tex.pak']['before']['sha256']==ORIGINAL and sel['/dc/tex.pak']['after_sha256']==C965 and prov['source']=='b9201d0452e9090c05781f489be2e47f4650ef97'
 assets=[];m0=[];m1=[]
 for path in ('/dc/tex.pak','/dc/native/r100/ps2-world.r4pw','/dc/native/r103/ps2-world.r4pw'):
  s=sel[path];b=s['before'];capacity=((b['bytes']+2047)//2048)*2048;assert b['bytes']<=capacity and s['after_extent']==b['extent'];source=a.original_raw if a.original_raw else (a.original_pack if path=='/dc/tex.pak' else a.original_world_root/path.lstrip('/'));assets.append({'path':path,'kind':'original_raw' if a.original_raw else 'original_file','source_path':str(source),'source_offset':(b['extent']-LBA0)*2048 if a.original_raw else 0,'start':(b['extent']-LBA0)*2048,'end':(b['extent']-LBA0)*2048+capacity,'bytes':b['bytes'],'sha256':b['sha256']});m0+=record_patch(s,b['bytes'])
 programme=json.loads(a.programme.read_text()) if a.programme else None;common=programme_rows(programme,sel,sp['cooked_track_bytes']) if programme else []
 if programme:
  for r in common:
   changes=record_patch(sel[r['path']],r['bytes']);m0+=changes;m1+=changes
  boot=next(r for r in common if r['path']=='/1ST_READ.BIN');newvol=max(504000,sel['/1ST_READ.BIN']['after_extent']-LBA0+(boot['bytes']+2047)//2048)
  if newvol>504150:raise ValueError('new programme requires unallocated longer track')
  for d in hp['descriptors']:
   old=d['new_counts']['scoped17']
   if old!=newvol:
    change={'start':(d['lba']-LBA0)*2048+d['field_offset'],'before':both32(old).hex(),'after':both32(newvol).hex(),'kind':'PVD_volume_space'};m0.append(change);m1.append(change)
 plan={'schema':'full-texture-pipeline-matched-plan-1','status':'NEW_PROGRAMME_VIRTUAL_ONLY_NOT_STAGED' if programme else 'ASSET_TEMPLATE_ONLY_NEW_PROGRAMME_PENDING_NOT_BOOT_ELIGIBLE','comparison_label':'FULL texture pipeline: compact/VQ+mips+17 representation; not isolated mip-only causal attribution','historical_reference':{'source':hp['runtime_source'],'programme':hp['program_sha256'],'ELF':hp['elf_sha256'],'C_track':OLD_C,'old_B948_track':'e9efca156ff9b11005af57688accc085c9e568ceef32c2085e8a2d8f789db434','scope':'Historical admission/evidence only; no old programme/state transfer'},'new_programme':programme or {'source':'PENDING main combined freeze; must include certified rectangle provenance b920 or reviewed descendant','programme':'UNBUILT/PENDING','ELF':'UNBUILT/PENDING','files':'same exact new boot+all14 overlays in both arms','flags':'same actual preprocessing/objects/ELF/linked constraints; labels not proof'},'M0':{'pack_sha256':ORIGINAL,'pack_bytes':156254208,'pack_members':6501,'world_sidecars':'original r100/r103 R4PW, original unchanged metadata','payload_replacements_from_old_C':assets,'metadata_patches':m0},'M1':{'pack_sha256':C965,'pack_bytes':155856896,'pack_members':6518,'content':'existing selected948 +17 scoped world, full policy reused','world_sidecars':'frozen remapped r100/r103 R4PW; unchanged original metadata; corrected programme provenance','asset_replacements_from_old_C':[],'metadata_patches':m1},'common_programme_ranges':common,'CRC_behavior_gate':{'source':prov['source'],'source_host_cases':prov['source_host_cases'],'qualification_sha256':sha(a.provenance),'method':'Physical R4PW full extent/CRC/FNV/mesh validated first; certified policySourceCrc consumed consistently by IDs/TC/PC/enemyVis and optional PVS/SG. No physical CRC/profile/movie identity forged. Ordinary M0 uses actual original metadata lineage. Unknown tuples keep ordinary mismatch fallback.','target_gate':'New SH4/fullprogram/actual macro binding then functional IDs placements, classes/partition counts, PC/OCCL/optional metadata and movie/lifecycle logs match. Host47 is not target equivalence.'},'optional_M2_actor985':{'status':'HELD, separate after reviewed consumer closure; do not stall965 primarypair','virtual_pack':actor['virtual_pack'],'composition_sha256':sha(a.actor_composition),'same6518_members_6498_exact_20_replacements':True,'limits':'No atlas2. No animals enablement or fake LVQ/GVQ boot assignment. Dynamic hand/headless/LOD/atlas sampling, current programme flags, live key/selected mip, combined resources and look must qualify; residency alone not draw/all20 coverage.'},'layout':{'files':1743,'preserve_all_LBAs':True,'Joliet_present':False,'primary_RockRidge':'patch every matching size record LE+BE, exact preconditions; do not invent a tree','source_track_bytes':sp['cooked_track_bytes'],'programme_zero_tail_max_bytes':(549150-sel['/1ST_READ.BIN']['after_extent'])*2048,'growth_rule':'Only existing verified zero programme-tail capacity, all payload ranges disjoint. Fail closed if any overlay exceeds original slot or programme exceeds fulltail; main must review any other layout.','track01_02_IP_path_tables':'preserve exactly','base_pair_bound':2*sp['cooked_track_bytes']+2*(1058400+1237152+87),'metadata_reserve':16777216,'allocation':'NO materialization/guest by this plan. Main admission required before any new track or pack output.'},'runtime_gate':{'namespace':'NEW actual combined-ELF namespace, e08 runtime04 source reused only after every CU/DIE/path/width/duplicate/anchor re-audit; never reuse e08 addresses','phase':'same pre/post even current completedSeq/UIFrame/Frame_cnt+actual skips/Rno0+flags/SndWatcher/CPU+zeroTick/all pointers; all body dependencies stable reread; retain all rejections/variants','coverage':'every source state240..360 including predecessor240, complete raw, zero differing variants; no tolerance, matching-row selection or sliding','scenes':['r103f QAindex5 farm, frozen menu-only controls then neutral','r100 QAindex0 HOUSE AFTERS20 woods, distinct historical natural-woods lineage'],'controls':'new same-programme fresh independent cold userdata and exact matched input/VMU/RNG lineage; sameanimalsOff1/cap4, camera/player/life/room/flags/counter frame windows; no foreign states/state edits','sampling':'Preserve certified source/base RGBA equality per cohort separately from actual filtered output. Capture exact framebuffers/cameras and count all pixel differences; no silent visual tolerance or automatic look acceptance.','key_binding':'all948 uses existing source-policy receipts, actual relevant scene keys/descriptor/CRC/live ownership and sampled selected mip/physical binding; explicit original co-residency, no bytes-to-FPS inference','memory':'full available RAM/VRAM/largest/contiguous/transition footprints plus actual co-resident originals and candidate allocations; partial census not peak/net saving','performance':'Host Flycast CPU/drive/window counters separately from MODELLED GPU/CPU proxy and actual physical Dreamcast acceptance; mipmap PVR bandwidth/fill benefit cannot be certified by host CPU/no traffic delta alone','execution':'root/rectangle allocation only;41s inner47.5s absolute60MB capture, disk/global peer guards current; no extensions/extra probes/release/recipe/SD'},'input_sha256':{str(p):sha(p) for p in (a.historical_plan/'image-plan.json',a.historical_plan/'scoped17-file-plan.json',a.historical_plan/'directory-records.json',a.provenance,a.actor_composition)}}
 if a.virtual_hash:plan['virtual_hash']=virtual_hashes(a.base_c,a.original_raw,assets,common,[m0,m1]);plan['virtual_hash']['warning']='NEW programme result' if programme else 'Historical a585 asset template only; not a newly qualified target image. M1 matches retained old C and remains unqualified until corrected programme.'
 with (a.out/'pair-plan.json').open('x') as f:json.dump(plan,f,indent=2);f.write('\n')
 print(json.dumps({'plan_sha256':sha(a.out/'pair-plan.json'),'status':plan['status'],'virtual_hash':plan.get('virtual_hash'),'image_bytes_written':0}))
if __name__=='__main__':main()
