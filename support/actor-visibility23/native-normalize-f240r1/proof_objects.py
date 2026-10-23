"""Read-only retained-object mapping; retired intermediates are never live proof."""
import re
SHARED='/root/probe/codex-actor-visibility23-eligibility-witness-integration/port/dreamcast/game/obj'

def verify_objects(records,mapping,manifest_record,source,arm,link_sha,check):
 if mapping.get('source')!=source or mapping.get('arm')!=arm or mapping.get('original_manifest')!=manifest_record or mapping.get('original_link_receipt_sha256')!=link_sha:raise ValueError('object mapping programme identity differs')
 root=manifest_record['path'].removesuffix('/OBJECTS.json')
 if root==manifest_record['path'] or mapping.get('live_standard_object_root')!=root+'/obj':raise ValueError('exact standard object root required')
 originals={r['path']:r for r in records}
 if len(originals)!=len(records):raise ValueError('duplicate original object path')
 rows=mapping.get('entries');mapped={r['original_path']:r for r in rows}
 if len(mapped)!=len(rows) or not set(mapped)<=set(originals):raise ValueError('duplicate or unknown mapped object')
 expected={p for p in originals if p.startswith(SHARED+'/')}
 if set(mapped)!=expected:raise ValueError('every shared transient input must be explicitly classified')
 counts=dict(live_standard_rehashed=0,retained_mapped_rehashed=0,build_time_transient_not_rehashed=0)
 historical=[]
 for path,record in originals.items():
  if path not in mapped:
   if not path.startswith(root+'/obj/'):raise ValueError('unclassified object outside per-arm live root')
   check(record);counts['live_standard_rehashed']+=1;continue
  row=mapped[path];relative=path[len(SHARED)+1:]
  if (row.get('original_sha256'),row.get('original_bytes'))!=(record['sha256'],record['bytes']):raise ValueError('mapped original digest/extent differs')
  if row.get('status')=='RETAINED_REHASHABLE':
   retained=dict(path=row['retained_path'],sha256=row['retained_sha256'],bytes=row['retained_bytes'])
   kind=row.get('retention_kind'); folder={'ACTUAL_COPIED_FILE':'link-inputs','ACTUAL_RETAINED_OWNED_LINK_SCRATCH':'link-scratch'}.get(kind)
   if folder is None or retained!={'path':root+'/'+folder+'/'+relative,'sha256':record['sha256'],'bytes':record['bytes']}:raise ValueError('retained bytes or exact mapped path differs')
   check(retained);counts['retained_mapped_rehashed']+=1
  elif row.get('status')=='BUILD_TIME_TRANSIENT_NOT_RETAINED':
   raise ValueError('this successor requires every transient retained and rehashable')
  else:raise ValueError('unknown object proof classification')
 return dict(**counts,manifest_entries=len(records),all_original_entries_freshly_rehashed=True,historical_records=historical,scope='Every original standard and exact retained mapped object freshly rehashed; no historical-only entries permitted.')
