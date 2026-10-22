#!/usr/bin/env python3
"""Retained cold-pair review only: no process attach, assets writes or image hash."""
import argparse,collections,hashlib,json,struct,zlib
from pathlib import Path

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,obj):p.write_text(json.dumps(obj,indent=2)+'\n')
def descriptor(d):
 names=['width','height','format','data_offset','data_size','flags','payload','reserved_0']
 return {'material':d[:64].split(b'\0')[0].decode('ascii','replace'),**dict(zip(names,struct.unpack('<8I',d[64:])))}
def pack_selected(path,selected):
 """Read only the index and actual exercised Header/Texture metadata, no fullhash."""
 out={}
 with path.open('rb')as f:
  head=f.read(2048);assert head[:8]==b'RE4PAK1\0'
  ver,n,at,data,crc=struct.unpack_from('<5I',head,8);assert ver==1 and at==2048
  index=f.read(data-at);assert zlib.crc32(index)&0xffffffff==crc
  members={'%08x-%08x'%(a,b):(o,s)for a,b,o,s in struct.iter_unpack('<4I',index[:n*16])}
  for row in selected:
   key=row['key'];off,size=members[key];f.seek(off);h=f.read(48);H=struct.unpack('<8s10I',h)
   assert H[0]==b'RE4DCTX\0'and H[3]==96 and H[4]==1
   f.seek(off+H[5]);d=f.read(96);want=descriptor(d);actual=row['texture']
   diffs={k:{'disk':v,'resident':actual.get(k)}for k,v in want.items()if actual.get(k)!=v}
   pal=actual['format']in(4,5);bank=actual['reserved_0'];validbank=1<=bank<=64 and(actual['format']!=5 or(bank-1)%16==0)
   fields_ok=not diffs or(pal and set(diffs)=={'reserved_0'}and want['reserved_0']==0 and validbank)
   out[key]={'pack_offset':off,'member_bytes':size,'disk_descriptor_hex':d.hex(),'stored_header_CRC_equal':row['header']['payload_crc32']==H[8],'named_descriptor_differences':diffs,'named_descriptor_fields_qualified':fields_ok,'runtime_PAL_bank_range_and_alignment_valid':validbank if pal else None,'raw96_padding_proof':'NOT_RETAINED_IN_TABLE; namedfields only, rawexact observer match retained separately'}
 return {'pack_path':str(path),'member_count':n,'index_crc32':crc,'rows':out,'scope':'Selected live metadata only, root full image/pack readback provides wholeidentity. StoredCRC not postupload payload revalidation.'}

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--base',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--M0-pack',type=Path,required=True);ap.add_argument('--M1-pack',type=Path,required=True);a=ap.parse_args();a.out.mkdir(exist_ok=False)
 arms={};pins=[]
 for arm in ['M0','M1']:
  cap=a.base/('cold-functional-canonical1004-'+arm+'-01');inv=cap.with_name(cap.name+'-invocation')
  raw=[json.loads(s)for s in(cap/'phase-observer69f.jsonl').read_text().splitlines()];summary=json.loads((cap/'phase-observer69f-summary.json').read_text())
  samples=[r for r in raw if r['event']=='completed_phase_sample'];tables=[r for r in raw if r['event']=='completed_phase_table'];direct=[r for r in raw if r['event']=='coherent_CPU_direct_packet'];full=[r for r in tables if'selected'in r['body']['table']];assert len(full)==1
  tab=full[0]['body']['table'];selected=tab['selected'];qualification=pack_selected(getattr(a,arm+'_pack'),selected);save(a.out/(arm+'-exercised-pack-metadata.json'),qualification)
  owned={}
  for r in selected:
   q=qualification['rows'][r['key']];t=r['texture']
   if q['stored_header_CRC_equal']and q['named_descriptor_fields_qualified']and r['package']['upload_complete_']==1 and r['vram_pointers_valid']and r['owns_texture']==1 and t['format']==0 and t['payload']==2:
    owned[r['pvr_allocation_base']]=max(owned.get(r['pvr_allocation_base'],0),t['data_size'])
  markers=[]
  for line,text in enumerate((cap/'run-output.txt').read_text(errors='replace').splitlines(),1):
   if any(s in text for s in ['ENEMYVIS r103','PS2DYN room=103','trans: room=103','PS2MESH open bytes=','native UI VRAM: frame=240','native UI VRAM: frame=360','PS2MESH frame=960 pass=','vram room: r=103 at=preload']):markers.append({'line':line,'text':text})
  pictures=[{'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)}for p in sorted((cap/'shots').rglob('*.png'))]
  for p in [cap/'phase-observer69f.jsonl',cap/'phase-observer69f-summary.json',cap/'run-result.json',cap/'run-output.txt',cap/'owned-process.json',inv/'profile.json',inv/'process-supervisor.json']:
   pins.append({'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)})
  arms[arm]={'samples':samples,'summary':summary,'identity':raw[0],'tables':{'frames':[r['scene']['source_tick']for r in tables],'valid_slots':tab['valid_slots'],'selected_count':len(selected),'categories':dict(collections.Counter(r['category']for r in selected)),'original_scoped_pairs':tab['co_resident_world_pairs'],'selected_keys':[r['key']for r in selected],'raw_canonical_match_count':sum(r['canonical_descriptor_match']for r in selected),'actual_arm_storedCRC_namedfields_pass_count':sum(r['stored_header_CRC_equal']and r['named_descriptor_fields_qualified']for r in qualification['rows'].values()),'actual_arm_known_owned_VQ_payload_lowerbound':sum(owned.values()),'actual_arm_known_owned_VQ_rounded_request_lowerbound':sum((n+31)//32*32 for n in owned.values()),'observer_canonical_only_lowerbound':tab['known_owned_VQ_payload_bytes_minimum']},'drive':samples[0]['scene']['drive_nonmusic'],'markers':markers,'direct':{'count':len(direct),'unique_keys':dict(collections.Counter(r['key']for r in direct)),'CPUstaging_only_no_TA_or_chosenLOD':True},'pictures':pictures,'run':json.loads((cap/'run-result.json').read_text()),'profile':json.loads((inv/'profile.json').read_text())}
 by={arm:{r['scene']['source_tick']:r for r in v['samples']}for arm,v in arms.items()};common=sorted(by['M0'].keys()&by['M1'].keys());comparisons=[]
 # Epoch/CPU counters vary across executions; compare source state and phase roles.
 phase_keys=['pg','pl','source_frame','Rno0','system_flags','stop_flags','proc_idx','last_proc','cpu_proc','completed_sequence','completed_frame','completed_present','completed_aborted','frame','source_draws_finished','frame_ready','ui_order','stream_aborted','pace_skip_frame','pace_skipped_frames','direct_open','re4dc_pace_skipping','source_pointers']
 for frame in common:
  left,right=by['M0'][frame],by['M1'][frame]
  diffs={}
  for k in ['room_id','life_raw','pose']:
   if left['scene'][k]!=right['scene'][k]:diffs['scene.'+k]={'M0':left['scene'][k],'M1':right['scene'][k]}
  for k in phase_keys:
   if left['phase'][k]!=right['phase'][k]:diffs['phase.'+k]={'M0':left['phase'][k],'M1':right['phase'][k]}
  comparisons.append({'source_frame':frame,'exact_recorded_state_phase_equal':not diffs,'differences':diffs,'M0_raw_CPU_us':left['cpu_us'],'M1_raw_CPU_us':right['cpu_us'],'CPU_scope':'Retained raw only, no speedup/delta/fullwindow conclusion'})
 save(a.out/'common-completed-source-rows.json',comparisons)
 result={'comparison':'FULL compact/VQ+mipmap+world36+actor20 pipeline; M0original18f retains protectedGanado mips, notgloballymipoff','result':'FUNCTIONAL_MATCH_ON_RETAINED_COMMON_STATES; FULLWINDOW_PERFORMANCE_GATE_OPEN','common_frames':common,'common_count':len(common),'common_240_360':[t for t in common if 240<=t<=360],'all_common_recorded_state_phase_equal':all(r['exact_recorded_state_phase_equal']for r in comparisons),'phase_exclusions':'Host zero_tick epoch,CPU ticks/completedprofilingSHA are independentlycoherent but cannotbevalueequal betweenexecutions. No matchingrow/tolerance/sliding selection.','controls_scope':'Exact same pinned keys/template/settings plus owned menu-only keylogs; ordinaryphase/flags/state recorded. Actual pad/RNG fields notcaptured, no fullcontrol equivalence assertion.','PCL_scope':'r103 notapplicable: sourcePCLpackage r100only170cells/1186portals. No livePCLsuccess claim or ENEMYVIS substitution. Futurewoods mustprove r100 PCCULL adoption.','memory_scope':'Named-field+storedheaderCRC qualified selected ownedVQ lowerbounds. FullnativeUI logged totals separately; not fullallocatorhighwater/peak/net saving.','arms':{},'drive_M1_minus_M0':{k:arms['M1']['drive'][k]-arms['M0']['drive'][k]for k in arms['M0']['drive']},'pins':pins,'screenshot_phase_limit':'Hostt0037 pair, exactsourceframe notlatchedtoPNG; not sameframe pixelacceptance.','remaining_gates':['Both240..360 framecoverage incomplete','Actualpresentation/chosenLOD/all-keydraw unavailable','Exact filteredlook acceptance open','PhysicalDreamcast acceptance open']}
 for arm,v in arms.items():
  result['arms'][arm]={k:v[k]for k in ['tables','drive','markers','direct','pictures']};result['arms'][arm]['coverage']=v['summary']['coverage'];result['arms'][arm]['source_program_binding']=v['identity']['binding'];result['arms'][arm]['pid_start']={k:v['identity'][k]for k in ['pid','start_filetime']}
 # Pure retained image analysis; never rewrite source PNGs.
 from PIL import Image
 paths=[a.base/('cold-functional-canonical1004-'+arm+'-01/shots/t0037/frames/fb0.png')for arm in ['M0','M1']]
 im=[Image.open(p).convert('RGBA')for p in paths];assert im[0].size==im[1].size
 pixels0,pixels1=[p.tobytes()for p in im]
 result['screenshot_pair']={'paths':[str(p)for p in paths],'sha256':[sha(p)for p in paths],'dimensions':im[0].size,'different_RGBA_pixels':sum(pixels0[i:i+4]!=pixels1[i:i+4]for i in range(0,len(pixels0),4))}
 save(a.out/'summary.json',result)
 (a.out/'screenshot-pair.html').write_text('<!doctype html><meta charset="utf-8"><title>Retained host t0037 M0 / M1</title><p>Host timestamps; source frame not latched to PNG. No pixel/look acceptance.</p>'+''.join('<h2>'+arm+'</h2><img src="../cold-functional-canonical1004-'+arm+'-01/shots/t0037/frames/fb0.png">'for arm in ['M0','M1']))
 (a.out/'SHA256SUMS').write_text(''.join(sha(p)+'  '+p.relative_to(a.out).as_posix()+'\n'for p in sorted(a.out.rglob('*'))if p.is_file()))
 print(json.dumps({'common':len(common),'state_phase_all_equal':result['all_common_recorded_state_phase_equal'],'summary_sha256':sha(a.out/'summary.json'),'seal_sha256':sha(a.out/'SHA256SUMS')}))
if __name__=='__main__':main()
