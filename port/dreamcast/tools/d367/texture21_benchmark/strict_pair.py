#!/usr/bin/env python3
"""Strict B/C same-source-window review; mismatches suppress paired performance arithmetic."""
import argparse,hashlib,json,struct
from pathlib import Path
from observer import vram_pointer

def signature(x):return json.dumps(x,sort_keys=True,separators=(',',':'))
def scene(r):return {'room_id':r['room_id'],'pose':r['pose'],'life_raw':r['life_raw']}
def rows(p):return [json.loads(x) for x in (p/'typed-observer.jsonl').read_text().splitlines()]
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser(description=__doc__)
 for n in ('B','C','B-gate','C-gate','originals','out'):ap.add_argument('--'+n,type=Path,required=True)
 a=ap.parse_args();arms={x:rows(getattr(a,x)) for x in ('B','C')};gates={x:json.loads(getattr(a,x+'_gate').read_text()) for x in ('B','C')};desc={r['key']:r for r in json.loads(a.originals.read_text())['selected']}
 indexed={x:{} for x in arms}
 for arm,rs in arms.items():
  for line,r in enumerate(rs,1):
   if r.get('event')=='sample':indexed[arm].setdefault(r['source_tick'],[]).append((line,r))
 mismatches=[];details=[]
 for tick in range(241,361):
  state={arm:{signature(scene(r)) for _,r in indexed[arm].get(tick,[])} for arm in arms};equal=bool(state['B']) and state['B']==state['C']
  if not equal:
   mismatches.append(tick);components=[]
   for field in ['room_id','life_raw']+list(next(iter(indexed['C'][tick]))[1]['pose']):
    vals={arm:{signature(r['pose'][field] if field in r['pose'] else r[field]) for _,r in indexed[arm].get(tick,[])} for arm in arms}
    if vals['B']!=vals['C']:components.append(field)
   details.append({'tick':tick,'B_lines':[l for l,_ in indexed['B'].get(tick,[])],'C_lines':[l for l,_ in indexed['C'].get(tick,[])],'B_variants':len(state['B']),'C_variants':len(state['C']),'different_components':components})
 control_tables=[];reject=[]
 for line,r in enumerate(arms['B'],1):
  if 'table' not in r:continue
  if r.get('table_end_source_tick')!=r['source_tick']:reject.append({'line':line,'reason':'B table crossed source tick'});continue
  selected=[]
  for entry in r['table']['selected']:
   key=entry['key']
   if key not in desc:continue
   d=desc[key];t=entry.get('texture',{});p=entry.get('package',{});h=entry.get('header',{})
   good=entry['admission']=='sampled_valid_uploaded' and p.get('upload_complete_')==1 and p.get('base_')==d['pack_offset'] and h.get('payload_crc32')==d['header_payload_crc32'] and t.get('material')==d['material'] and all(t.get(k)==d[k] for k in ('width','height','format','flags','payload','data_size')) and vram_pointer(entry.get('pvr_sampled',0)) and vram_pointer(entry.get('pvr_allocation_base',0)) and entry.get('owns_texture')==1
   if not good:reject.append({'line':line,'key':key,'reason':'B descriptor/CRC/material/packoffset/upload/ownership mismatch or torn entry'});continue
   selected.append({'key':key,'slot':entry['slot'],'allocation_base':entry['pvr_allocation_base'],'descriptor':d})
  control_tables.append({'line':line,'source_tick':r['source_tick'],'selected':selected})
 boundaries={}
 for tick in (240,241,300,301,360):
  boundaries[str(tick)]={arm:[{'line':line,'state':scene(r),'drive':r['drive_nonmusic']} for line,r in indexed[arm].get(tick,[])] for arm in arms}
 counters={}
 for arm in arms:
  edges={tick:{signature(r['drive_nonmusic']) for _,r in indexed[arm].get(tick,[])} for tick in (240,360)}
  unambiguous=all(len(v)==1 for v in edges.values());counters[arm]={'source_edge_values':{str(k):[json.loads(v) for v in sorted(vals)] for k,vals in edges.items()},'single_value_at_each_sampled_edge':unambiguous}
  if unambiguous:
   before=json.loads(next(iter(edges[240])));after=json.loads(next(iter(edges[360])));counters[arm]['observed_source_associated_delta']={k:after[k]-before[k] for k in before}
  counters[arm]['limit']='Frame count coherence is not completed-state phase latch; no exact PT-edge attribution inferred'
 report={'scope':'Strict predeclared source241–360 B01/C03 gate. No row selection, tolerance widening, speedup arithmetic or physical Dreamcast claim','strict_scene_gate':'PASS' if not mismatches else 'FAIL','mismatching_ticks':mismatches,'mismatching_tick_count':len(mismatches),'component_differences':details,'boundary_samples':boundaries,'CPU_rows_unpaired':{arm:gates[arm]['postload_windows'] for arm in arms},'performance_comparison':'PENDING; no speedup/delta because strict scene gate fails' if mismatches else 'Requires independent final binding/phase/counter review','counter_review':counters,'B_original_control_admission':{'stable_tables':len(control_tables),'all9_tables':sum(len(t['selected'])==9 for t in control_tables),'largest_valid_original_set':max((len(t['selected']) for t in control_tables),default=0),'distinct_valid_original_keys':sorted({r['key'] for t in control_tables for r in t['selected']}),'tables':control_tables,'rejections':reject,'scope':'Actual frozen base948 pack offset/key/member header CRC/material/descriptor and live known pointer/ownership binding; no total key draw proof or full allocator extent/high water'},'input_hashes':{str(getattr(a,arm)/n):digest(getattr(a,arm)/n) for arm in arms for n in ('typed-observer.jsonl','typed-observer-summary.json','run-output.txt')},'next_gate':'Investigate within-tick update-phase coherence offline; no further guest'}
 with a.out.open('x') as f:json.dump(report,f,indent=2);f.write('\n')
 print(json.dumps({'strict_scene_gate':report['strict_scene_gate'],'mismatching_ticks':len(mismatches),'B_original9':report['B_original_control_admission']['all9_tables'],'B_rejects':len(reject),'counter_deltas':counters}))
if __name__=='__main__':main()
