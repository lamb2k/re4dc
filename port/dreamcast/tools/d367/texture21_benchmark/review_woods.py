#!/usr/bin/env python3
"""Independent retained r100 HOUSE AFTERS20 functional evidence review, never a benchmark comparison."""
import argparse,hashlib,json
from pathlib import Path
from observer import vram_pointer
from active_gate import camera_valid,phases

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 for name in ('cap','originals','candidates','out'):ap.add_argument('--'+name,type=Path,required=True)
 a=ap.parse_args();originals={r['key']:r for r in json.loads(a.originals.read_text())['selected']};candidates={r['key']:r for r in json.loads(a.candidates.read_text())['selected']};raw=[json.loads(s) for s in (a.cap/'typed-observer.jsonl').read_text().splitlines()];tables=[];rejected=[];camera=[];witness=[]
 for line,r in enumerate(raw,1):
  if r.get('event')!='sample' or r.get('room_id')!=0x100:continue
  ok,reason=camera_valid(r)
  if ok:camera.append({'line':line,'tick':r['source_tick']})
  else:rejected.append({'line':line,'reason':reason,'kind':'camera'})
  if 'table' in r:
   if r['table_end_source_tick']!=r['source_tick']:rejected.append({'line':line,'reason':'table crossed source tick'});continue
   selected=[]
   for entry in r['table']['selected']:
    k=entry['key'];d=candidates.get(k,originals.get(k))
    if d is None:continue
    t=entry.get('texture',{});p=entry.get('package',{});h=entry.get('header',{})
    good=entry['admission']=='sampled_valid_uploaded' and h.get('payload_crc32')==d['header_payload_crc32'] and p.get('base_')==d['pack_offset'] and p.get('upload_complete_')==1 and entry.get('owns_texture')==1 and vram_pointer(entry.get('pvr_sampled',0)) and vram_pointer(entry.get('pvr_allocation_base',0)) and all(t.get(name)==d[name] for name in ('material','width','height','format','data_offset','data_size','flags','payload','reserved_0'))
    if not good:rejected.append({'line':line,'key':k,'reason':entry.get('reason','descriptor/CRC/material/currentCpackoffset/upload/ownership mismatch')});continue
    selected.append({'key':k,'arm':'candidate' if k in candidates else 'original','slot':entry['slot'],'allocation_base':entry['pvr_allocation_base'],'sampled_pointer':entry['pvr_sampled'],'payload_bytes':d['data_size'],'rounded_request':d['rounded_request']})
   bases={x['allocation_base']&0xffffff for x in selected};tables.append({'line':line,'source_tick':r['source_tick'],'selected':selected,'unique_bases':sorted(bases),'payload_minimum':sum(max(x['payload_bytes'] for x in selected if x['allocation_base']&0xffffff==b) for b in bases),'rounded_request_lower_bound':sum(max(x['rounded_request'] for x in selected if x['allocation_base']&0xffffff==b) for b in bases)})
  if 'minimum_header_witness' in r:
   w=r['minimum_header_witness'];witness.append({'line':line,'source_tick':r['source_tick'],**w})
 livekeys={x['key'] for t in tables for x in t['selected']};bases_by_key={k:{x['sampled_pointer']&0xffffff for t in tables for x in t['selected'] if x['key']==k} for k in livekeys}
 for w in witness:
  w['decoded_TCW_pointer_offset']=(w['tcw']&0x1fffff)<<3;w['matches_single_stable_observed_base']=bases_by_key.get(w['key'])=={w['decoded_TCW_pointer_offset']};w['shape_flags_valid']=w['physical_64_square'] and w['vq'] and w['mipmap'];w['qualified_minimum_header']=w['matches_single_stable_observed_base'] and w['shape_flags_valid'];w['limit']='Stable tuple reread in frozen observer; one sampled minimum header only, no vertices/pixels/all-key totals or completed-state/presentation latch'
 full=[t for t in tables if sum(x['arm']=='candidate' for x in t['selected'])==8 and sum(x['arm']=='original' for x in t['selected'])==4];pt=[w for w in phases((a.cap/'run-output.txt').read_text(errors='replace')) if w['source_window'][0]>=241 and w['freeplay_loop_complete']]
 report={'scope':'Current C13c/a585/e08 r100 existing QA0 HOUSE AFTERS20 cold functional only; distinct from original natural woods and no Bwoods/control timing comparison','raw_observer_identity':raw[0],'tables':tables,'all8_plus4_tables':len(full),'full_cohort_first_last':[full[0]['source_tick'],full[-1]['source_tick']] if full else None,'original_keys':sorted(livekeys&set(originals)),'candidate_keys':sorted(livekeys&set(candidates)),'minimum_unique_bases':12 if full and all(len(t['unique_bases'])==12 for t in full) else None,'minimum_payload_bytes':full[0]['payload_minimum'] if full else None,'rounded_request_lower_bound':full[0]['rounded_request_lower_bound'] if full else None,'net_VRAM_or_highwater':'UNAVAILABLE; originals co-resident, full allocator/category/peak not observed','active_camera_samples':{'all':len(camera),'post241':sum(x['tick']>=241 for x in camera),'first_last':[min(x['tick'] for x in camera),max(x['tick'] for x in camera)]},'exclusive_freeplay_PT_windows':pt,'minimum_header_witnesses':witness,'unique_minimum_header_keys':sorted({w['key'] for w in witness if w['qualified_minimum_header']}),'rejections':rejected,'phase_limit':'Frame-coherent runtime03 observations; new PhaseLatch not used/runtime-qualified, so no completed-state B/C equivalence or exact displayed-frame claim','input_sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (a.originals,a.candidates,a.cap/'typed-observer.jsonl',a.cap/'typed-observer-summary.json',a.cap/'run-output.txt')}}
 with a.out.open('x') as f:json.dump(report,f,indent=2);f.write('\n')
 print(json.dumps({'all8plus4tables':len(full),'originals':report['original_keys'],'candidates':len(report['candidate_keys']),'minimum_payload':report['minimum_payload_bytes'],'rounded_lower_bound':report['rounded_request_lower_bound'],'header_events':len(witness),'header_unique_keys':len(report['unique_minimum_header_keys']),'camera_post241':report['active_camera_samples']['post241'],'rejects':len(rejected)}))
if __name__=='__main__':main()
