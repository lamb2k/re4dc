"""Pure fixed ABI decoding; host observation never proves physical cache/presentation."""
import struct
FIELDS='seq abi_flags setter_generation callback_generation controller record head observed_owner setter_frame callback_frame queue_frame event_frame rooms event_reason state_flags particle_count alpha_ids native_requested native_accepted accepted_total'.split()
COUNTERS='SET BOUND DESTRUCT ROOM ALLOC TRANS ZERO INDOOR STOP CALLBACK CANDIDATE PROFILE ALPHA QUEUE CANCEL_SET CANCEL_ROOM CANCEL_CALLBACK STALE STATE CONSUMED STOP_FLUSH RETURN_ZERO RETURN_POSITIVE BIND_REJECT'.split()
def decode(raw):
 if len(raw)!=128:raise ValueError('exact128 bytes required')
 v=struct.unpack('<20I24H',raw);d=dict(zip(FIELDS,v[:20]));d['counts']=dict(zip(COUNTERS,v[20:]));return d
def stable(a,b):
 if a!=b:return {'stable':False,'reason':'changed-double-read','raw_first':a.hex(),'raw_second':b.hex()}
 d=decode(a);bad=[]
 if d['abi_flags']!=1:bad.append('ABI-or-fault')
 if d['seq']&1 or d['seq']>=0xfffffffe:bad.append('odd-or-terminal-sequence')
 if any(n>=0xfffe for n in d['counts'].values()):bad.append('counter-terminal')
 d.update(stable=not bad,refusals=bad,raw=a.hex())
 flags=1|2|4|8192|16384
 d['source_join_candidate']=bool(not bad and d['state_flags']&flags==flags and d['rooms']==0x010c010c and d['event_reason']==8 and d['setter_generation']>0 and d['setter_generation']==d['callback_generation'] and d['callback_frame']==d['queue_frame']==d['event_frame'] and d['native_accepted']<=d['native_requested'])
 d['native_api_report_only']=True;d['archive_owner_authenticated']=False;d['physical_cache_or_presentation_proven']=False
 return d


def judge_file(path,expected_pid=None):
 """Fail-closed ON evidence gate, separate from capture/process completion."""
 from pathlib import Path
 import hashlib,json
 path=Path(path);result={'status':'UNKNOWN','diagnostic_accepted':False,'stable_samples':0,'unknown_samples':0,'source_join_candidates':0,'errors':[],'max_counters':{},'positive_native_api_report_observed':False,'physical_cache_or_presentation_proven':False}
 if not path.exists():result['errors']=['missing observer log'];return result
 if path.stat().st_size>4*1024**2:result.update(status='FAILED',errors=['observer byte cap']);return result
 try:raw=path.read_bytes()
 except OSError as e:result.update(status='FAILED',errors=[repr(e)]);return result
 if len(raw)>4*1024**2:result.update(status='FAILED',errors=['observer byte cap changed']);return result
 result['log_sha256']=hashlib.sha256(raw).hexdigest();result['log_bytes']=len(raw)
 pid=None;last_seq=None
 try:
  for line in raw.splitlines():
   if not line.strip():continue
   row=__import__('json').loads(line)
   if not isinstance(row,dict):raise ValueError('nonobject observer row')
   if 'status' in row:
    if row['status'] in ['OBSERVER_FAILED','OBSERVER_DEADLINE_NO_QUALIFICATION']:result['errors'].append(row);result['status']='FAILED';continue
    if row['status']!='HOST_RAM_BASE':raise ValueError('unknown observer status')
    if pid is not None or type(row.get('pid')) is not int or row['pid']<=0 or row.get('offset')!='0x36c740' or row.get('host_alias_only') is not True:raise ValueError('host RAM identity')
    pid=row['pid']
    if expected_pid is not None and pid!=expected_pid:raise ValueError('PID differs from capture')
    continue
   if pid is None or row.get('pid')!=pid:raise ValueError('sample PID/base binding')
   record=row['record']
   if not isinstance(record,dict):raise ValueError('nonobject record')
   if record.get('reason')=='changed-double-read':
    a=bytes.fromhex(record['raw_first']);b=bytes.fromhex(record['raw_second'])
    if len(a)!=128 or len(b)!=128 or stable(a,b)!=record:raise ValueError('changed sample representation')
    result['unknown_samples']+=1;continue
   b=bytes.fromhex(record['raw'])
   if len(b)!=128 or stable(b,b)!=record:raise ValueError('record differs from canonical raw decoding')
   d=stable(b,b)
   if not d['stable']:result['unknown_samples']+=1;continue
   if last_seq is not None and d['seq']<last_seq:raise ValueError('sequence decreased; reset/provenance unknown')
   last_seq=d['seq'];result['stable_samples']+=1
   for n,v in d['counts'].items():result['max_counters'][n]=max(result['max_counters'].get(n,0),v)
   if d['source_join_candidate']:
    result['source_join_candidates']+=1
    if d['native_accepted']>0:result['positive_native_api_report_observed']=True
  if result['status']=='FAILED':return result
  if pid is None or expected_pid is None:result['errors'].append('missing capture-bound host PID')
  if result['unknown_samples']:result['errors'].append('invalid/unstable samples retained UNKNOWN')
  if not result['stable_samples']:result['errors'].append('no stable valid ABI samples')
  if not result['source_join_candidates']:result['errors'].append('no valid source-join sample')
  if not all(result['max_counters'].get(n,0)>0 for n in ['SET','BOUND','CALLBACK','QUEUE','CONSUMED']):result['errors'].append('callback/queue/consumed counter closure UNKNOWN')
  if not (result['max_counters'].get('RETURN_ZERO',0)>0 or result['max_counters'].get('RETURN_POSITIVE',0)>0):result['errors'].append('native API return counter closure UNKNOWN')
  if not result['errors']:result.update(status='SOURCE_JOIN_OBSERVED_API_REPORT_ONLY',diagnostic_accepted=True)
  return result
 except (ValueError,KeyError,TypeError,UnicodeError) as e:
  result.update(status='FAILED',diagnostic_accepted=False);result['errors'].append(str(e));return result
