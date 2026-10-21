#!/usr/bin/env python3
"""Review sealed C-only observer rows without reading a live process or inferring timing gains."""
import argparse,hashlib,json,math
from pathlib import Path
from observer import vram_pointer

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def assess(row,selected):
 keymap={r['scoped_key']:r for r in selected};originals={r['original_key'] for r in selected};result={'source_coherent':False,'stable_table':False,'selected':[],'rejected':[]}
 if row.get('event')!='sample':return result
 if not isinstance(row.get('source_tick'),int) or row['source_tick']<=0:result['rejected'].append('invalid source tick');return result
 if not all(isinstance(x,(float,int)) and math.isfinite(x) for vals in row.get('pose',{}).values() for x in vals):result['rejected'].append('nonfinite pose');return result
 result['source_coherent']=True
 table=row.get('table')
 if table:
  if row.get('table_end_source_tick')!=row['source_tick']:result['rejected'].append('table crossed source tick')
  else:
   result['stable_table']=True
   for r in table['selected']:
    if r['key'] in originals:result['selected'].append({'key':r['key'],'arm':'original','slot':r['slot'],'allocation_base':r.get('pvr_allocation_base')});continue
    if r['key'] not in keymap:result['rejected'].append('unknown selected key');continue
    e=keymap[r['key']];t=r.get('texture',{});h=r.get('header',{});p=r.get('package',{})
    good=r.get('admission')=='sampled_valid_uploaded' and p.get('upload_complete_')==1 and h.get('payload_crc32')==e['candidate_crc32'] and [t.get('width'),t.get('height')]==e['physical'] and (t.get('format'),t.get('flags'),t.get('payload'),t.get('data_size'))==(0,4,2,3414) and vram_pointer(r.get('pvr_sampled',0)) and vram_pointer(r.get('pvr_allocation_base',0))
    if not good:result['rejected'].append('candidate descriptor/upload/pointer mismatch: '+r['key']);continue
    result['selected'].append({'key':r['key'],'arm':'candidate','slot':r['slot'],'allocation_base':r['pvr_allocation_base'],'sampled_pointer':r['pvr_sampled'],'owns_texture':r.get('owns_texture'),'payload_bytes':3414,'rounded_request_lower_bound':3424})
 witness=row.get('minimum_header_witness')
 if witness and witness.get('key') in keymap and witness.get('physical_64_square') and witness.get('vq') and witness.get('mipmap'):
  result['minimum_header_witness']={**witness,'clock_limit':'Exact UI frame witness; surrounding source pose sample is not independently synchronized to presented pixels'}
 return result

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--cap',type=Path,required=True);ap.add_argument('--plan',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
 inp=json.loads((a.plan/'inputs-final/plan-inputs.json').read_text());summary=json.loads((a.cap/'typed-observer-summary.json').read_text());assert summary['anchors_verified'];rows=[json.loads(l) for l in (a.cap/'typed-observer.jsonl').read_text().splitlines()];identity=rows[0];assert identity['binding']['elf_sha256']=='e08c9abc8f6bb44bb2a94642fc9a2e664d22039659cea7fcce311cb9989d7433';assert identity['binding']['program_sha256']=='a58579b87da0c45267cb93efe29feea2438da9ddab62d0fe31c47a1c6ff32c71'
 report={'scope':'C-only functional evidence; no B, speedup, full allocator peak or console acceptance','input_hashes':{n:digest(a.cap/n) for n in ['typed-observer-summary.json','typed-observer.jsonl']},'summary':summary,'source_rooms':{},'stable_tables':[],'minimum_header_witnesses':[],'rejections':[],'first_source_pose':None,'last_source_pose':None};seen={};lasttick=None;drive=None
 for line,r in enumerate(rows,1):
  v=assess(r,inp['selected'])
  if not v['source_coherent']:continue
  tick=r['source_tick'];room=str(r['room_id'])
  if lasttick is not None and tick<lasttick:report['rejections'].append({'line':line,'reason':'source tick decreased'});continue
  if drive and any(r['drive_nonmusic'][k]<drive[k] for k in drive):report['rejections'].append({'line':line,'reason':'cumulative nonmusic counter decreased'});continue
  lasttick=tick;drive=r['drive_nonmusic'];report['source_rooms'].setdefault(room,[]).append(tick)
  pose={'line':line,'source_tick':tick,'room_id':r['room_id'],'pose':r['pose'],'camera_scope':r.get('camera_scope','legacy controller camera only; active view/projection unavailable'),'life_raw':r['life_raw']}
  if report['first_source_pose'] is None:report['first_source_pose']=pose
  report['last_source_pose']=pose
  if v['rejected']:report['rejections'].append({'line':line,'reasons':v['rejected']})
  if v['stable_table']:
   selected=v['selected'];c=[x for x in selected if x['arm']=='candidate'];bases={x['allocation_base']&0xffffff for x in c};record={'line':line,'source_tick':tick,'room_id':r['room_id'],'candidate_keys':[x['key'] for x in c],'original_keys':[x['key'] for x in selected if x['arm']=='original'],'unique_candidate_bases':sorted(bases),'minimum_candidate_payload_bytes':3414*len(bases),'minimum_rounded_requests_bytes':3424*len(bases),'selected_rows':selected,'vram_counters':r.get('vram_counters'),'limits':'Coherent sampled selected-cache membership and known allocation bases only; no complete allocation extent/high water/palette/native room census, no final draw proof'};report['stable_tables'].append(record)
   for x in c:seen[x['key']]=True
  if 'minimum_header_witness' in v:report['minimum_header_witnesses'].append({'line':line,**v['minimum_header_witness']})
 report['source_rooms']={r:{'first':min(t),'last':max(t),'samples':len(t)} for r,t in report['source_rooms'].items()};report['distinct_candidates_observed']=sorted(seen);report['largest_coherent_candidate_set']=max((len(x['candidate_keys']) for x in report['stable_tables']),default=0)
 with a.out.open('x') as f:json.dump(report,f,indent=2);f.write('\n')
 print(json.dumps({'distinct_candidate_keys':len(seen),'largest_coherent_set':report['largest_coherent_candidate_set'],'stable_tables':len(report['stable_tables']),'minimum_header_witnesses':len(report['minimum_header_witnesses']),'rejections':len(report['rejections'])}))
if __name__=='__main__':main()
