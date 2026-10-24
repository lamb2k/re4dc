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
