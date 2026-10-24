"""Metadata-only finite-cohort disposition. No geometry predicate, target or pack build."""
from pathlib import Path
import argparse,collections,hashlib,json,resource,time
LIMIT=256*1024**2

def identity(path):
 path=Path(path)
 if path.is_symlink() or not path.is_file():raise ValueError('Nonregular/aliased input')
 h=hashlib.sha256()
 with path.open('rb') as stream:
  for block in iter(lambda:stream.read(1<<20),b''):h.update(block)
 return {'bytes':path.stat().st_size,'sha256':h.hexdigest()}

def load(pin):
 if identity(pin['path'])!={k:pin[k] for k in ['bytes','sha256']}:raise ValueError('Input identity differs')
 return json.loads(Path(pin['path']).read_bytes())

def domain_rows(report):
 if report['halt'] is not None or len(report['plan'])!=75 or len(report['results'])!=75:raise ValueError('Incomplete finite report')
 grouped=collections.defaultdict(list)
 for plan,result in zip(report['plan'],report['results']):
  case=plan['case'];n=result['complete_originals'];covered=result['covered_originals'];draw=result['unproved_draw_originals']
  if case!=result['case'] or case[7:9]!=['hut',647] or case[9] not in [2000,500,250] or n<=0:raise ValueError('Foreign case/camera/domain')
  if len(set(covered))!=len(covered) or len(set(draw))!=len(draw) or set(covered)&set(draw) or set(covered)|set(draw)!=set(range(n)):raise ValueError('Not complete disjoint original partition')
  if result['runtime_admitted'] is not False or result['actual_removed_transform_corners'] is not None or result['modelled_ms'] is not None:raise ValueError('Foreign acceptance scope')
  grouped[case[9]].append({'rank':case[0],'physical':case[1:7],'original_triangles':n,'nominal_covered_triangles':len(covered),'unproved_draw_triangles':len(draw),'nominal_wholelet':len(covered)==n,'local_exclusive_slots':len(result['exclusively_covered_local_indices']),'dependencies':result['dependencies'],'draw_reasons':dict(collections.Counter(x[1] for x in result['draw_reasons']))})
 out=[]
 for domain in report['domains']:
  size=domain['size_mm'];rows=grouped[size]
  if len(rows)!=25 or sorted(x['rank'] for x in rows)!=list(range(25)) or sum(x['original_triangles'] for x in rows)!=889:raise ValueError('Missing fixed target/original inventory')
  union=set(x for row in rows for x in row['dependencies']);nominal=sum(x['nominal_covered_triangles'] for x in rows);exclusive=sum(x['local_exclusive_slots'] for x in rows)
  admitted_union=len(union)<=16
  if nominal!=domain['nominal_per_let_covered_originals_before_global_union'] or (nominal if admitted_union else 0)!=domain['covered_originals_after_global_union'] or (exclusive if admitted_union else 0)!=domain['sum_per_let_exclusive_local_index_slots']:raise ValueError('Domain/global union count mismatch')
  out.append({'cell_mm':size,'camera':'r10d hut frame647','physical_targets':25,'complete_original_triangles':889,'full_panel_union':len(union),'global_panel_limit':16,'global_union_within_limit':admitted_union,'partial_nominal_triangles':nominal,'after_global_union_nominal_triangles':nominal if admitted_union else 0,'nominal_whole_meshlets':sum(x['nominal_wholelet'] for x in rows),'minimum_unproved_triangles_in_any_target':min(x['unproved_draw_triangles'] for x in rows),'exclusive_local_slots_after_global_union':exclusive if admitted_union else 0,'exclusive_slots_are_actual_transforms':False,'runtime_admitted_cut_meshlets':0,'gross_saving_of_admitted_empty_cut_set_ms':0,'hypothetical_partition_modelled_ms':None,'counterfactual_cycles_per_slot_to_reach1ms_at200MHz_before_any_overhead':str(__import__('fractions').Fraction(200000,exclusive)) if exclusive and admitted_union else None,'rows':rows})
 return out

def portal_rows(report):
 rows=report['rows'];frames=[r['frame'] for r in rows]
 if frames!=list(range(500,795,7)):raise ValueError('Foreign portal camera window')
 if sum(bool(r['all_openings_out']) for r in rows)!=report['all_openings_out_views'] or any(not r['visible_unresolved_openings'] for r in rows):raise ValueError('Inconsistent opening fallback records')
 if report['all_openings_out_views']!=0:raise ValueError('This zero disposition requires separate positive qualification')
 return {'component':report['component'],'views':len(rows),'frames':[frames[0],frames[-1]],'stride':7,'all_openings_out_prerequisite_views':0,'certified_hidden_views':0,'camera_pin':report['camera'],'scope':'conservative unresolved opening prerequisite only; not a continuous closure proof'}

def main():
 resource.setrlimit(resource.RLIMIT_AS,(LIMIT,LIMIT));started=time.monotonic();a=argparse.ArgumentParser();a.add_argument('--inputs',type=Path,required=True);a.add_argument('--out',type=Path,required=True);args=a.parse_args()
 if args.out.exists():raise ValueError('Fresh output only')
 contract=json.loads(args.inputs.read_bytes());reports={n:load(pin) for n,pin in contract['reports'].items()}
 verified=[]
 for pin in contract['hash_only_inputs']:
  got=identity(pin['path'])
  if got!={k:pin[k] for k in ['bytes','sha256']}:raise ValueError('Hash-only raw/camera input differs '+pin['path'])
  verified.append(dict(pin,scope='byte hash only; no geometry/query interpretation'))
 domains=domain_rows(reports['original_chunks']);price=reports['r101_remainder'];seed_groups=[price['groups'][k] for k in ['0:0','1:0']];hypo_rows=[{'frame':frame,'hypothetical_removed_corners':sum(next(x['net_saved_corners'] for x in g['rows'] if x['frame']==frame) for g in seed_groups)} for frame in range(500,795,7)];hypo_mean=sum(x['hypothetical_removed_corners'] for x in hypo_rows)/43
 portals=[portal_rows(reports[n]) for n in ['r101_seed','r101_east']]
 if any(d['nominal_whole_meshlets'] for d in domains):raise ValueError('A wholelet positive needs separate qualification; no zero verdict')
 result={'decision':'NO_GO_REVIEWED_FINITE_COHORT_NO_CERTIFIED_USEFUL_CUT','threshold_MODELLED_ms':1,'admitted_cut_set_empty':True,'gross_cull_saving_from_empty_cut_set_MODELLED_ms':0,'net_runtime_delta_MODELLED_ms':None,'timing_scope':'0 is algebraic gross saving of no admitted removals, not a CPU benchmark, net overhead estimate or hardware timing.','r10d':domains,'r101':{'corpora':portals,'hypothetical_seed_removed_corners_mean':hypo_mean,'hypothetical_seed_benchmark647':next(x for x in hypo_rows if x['frame']==647),'dedicated_remainder_bytes_before_cells_ownership_allocator':sum(g['two_way_variant_geometry_bytes']+g['two_way_variant_SG_bytes'] for g in seed_groups),'hypothetical_seed_is_hidden':False,'existing_281_count_belongs_to':'r10d same25 at500mm, not r101','certified_runtime_cuts':0},'input_contract_pin':identity(args.inputs),'reports':contract['reports'],'hash_only_inputs_verified':verified,'source_pins':contract['source_pins'],'numeric_raster_receipts':'UNQUALIFIED; no static geometry result promoted','other9600_cases':'UNTESTED_UNKNOWN; no global impossibility claim','new_geometry_predicates':0,'new_rays':0,'SDK_media_guest_runtime_data_edits':False,'partial_partition_options':'Not admitted: new lossless target encoding, material/strip/SG/transform/header cost, endpoint/raster/source-prefix proof and complete allLOD identity required before any future >=1ms claim.','limits':{'max_address_bytes':LIMIT,'external_seconds':120,'jobs':1,'seconds':time.monotonic()-started,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}}
 if time.monotonic()-started>115:raise ValueError('Internal deadline')
 raw=(json.dumps(result,indent=2)+'\n').encode()
 if len(raw)>256*1024:raise ValueError('Compact output cap')
 args.out.mkdir();(args.out/'report.json').write_bytes(raw);print(json.dumps({'decision':result['decision'],'report':identity(args.out/'report.json'),'seconds':result['limits']['seconds']}))
if __name__=='__main__':main()
