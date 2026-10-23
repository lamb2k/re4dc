"""Exact actor mode1 census admission; no process queries at import."""
from pathlib import Path
import datetime,json,os,re,sys
FINAL_SOURCE='f2405bb06ebaff6e2a7681479d5308ec5d3b988a'
ACTOR_SOURCE='7997bc3312e02e4c6c6849a8b7c7f8a5fd928ac5'
INTEGRATION='0b4beb704902a1dc6b2aace056be344863b4a0c1'
CONTAIN_SHA='11a9f613212a4a72f5e18f2d22e5b8afb2e7a3517be531442bd0cd6e9af454c7'
FLOOR=20468203520
STOCK_SHA='646bd4eb42ff2063d4e07dc3754ab0c0d61e3b75348b934a48e7f63a25a07747'
READER_SHA='6c43705318caa4c63fddd2995c04bdc9c3730abfe66400192be89f4d1e845059'
CAPTURE_SHA='14a3561e730df57e29d271e6fb7cdbf44b8fea2d1b7b2be076a5cb4590856d57'
STOP=r'(?!)' # Observation ends at literal54; no fabricated completion marker.

FIXTURE_SHA='6b28db8cdec172110720ab105fd9c3ce68b15f10d4607eb207dc19829d43cbe3'
PAD_SHA='073552789fad65c4057fa83303f10ac18ff9bc00ae48f195762be982c3222ff9'
OUTPUT_NAME='actor23-'+FINAL_SOURCE+'-r119-census-01'

def fixed_stock_contract(p):
 if (p.get('source'),p.get('integration'),p.get('case'),p.get('arm'))!=(FINAL_SOURCE,INTEGRATION,'r119-census','on'):raise ValueError('exact enabled mode1 census only')
 if p.get('runtime_mode')!=1 or p.get('observation_only')is not True or p.get('active_window_claim')is not True:raise ValueError('census mode1 only; actual cuts remain unqualified')
 if (p.get('programme_receipt_sha256'),p.get('elf_sha256'),p.get('raw_sha256'))!=('41beee7f50af4ff50c49b03a7cfa53d794086646322c5ebe7a85ffc7805a883d','a004425be1b24f45c809464232df95ff8a8c2e2d74621566185556c93f5728bd','d42aca673badeba89afb6acb27552fd9fdc2f740d3c9809026525f01d6db0c9a'):raise ValueError('exact current census programme and images required')
 if (p.get('fixture_sha256'),p.get('pad_sha256'))!=(FIXTURE_SHA,PAD_SHA)or p.get('passive_sampling')is not False or p.get('late_global_tick')!=539 or p.get('census_workspace_binds')!=600 or p.get('completion_flush_required')is not True:raise ValueError('exact no-hold census fixture/mode1/600+flush only')
 args=p['stock_argv']
 if len(args)!=20 or args[::2]!=['--base','--cap','--syms','--warp','--pad','--seconds','--period','--stop','--grace','--name']:raise ValueError('literal stock options required')
 if args[1::2]!=[p['base'],p['capture'],p['syms'],p['fixture'],p['pad'],'54','4',STOP,'2','actor23-r119-census']:raise ValueError('literal54/period4/no stopgoal/grace2 census required')
 return p

def root_review_contract(p):
 r=p.get('root_review')
 if not isinstance(r,dict):raise ValueError('separate main exact-image/stage review required')
 for key in ('source','integration','case','programme_receipt_sha256','stage_receipt_sha256','elf_sha256','raw_sha256','resolved_sha256','source_seal_sha256','module_roster_sha256','kos_receipt_sha256','private_inputs_sha256','ownership_audit_sha256','fixture_sha256','pad_sha256','normalization_seal_sha256','assets_manifest_sha256','disc_manifest_sha256'):
  if p.get(key)is None or r.get(key)!=p[key]:raise ValueError('main exact binding absent/differs: '+key)
  if key.endswith('_sha256')and not re.fullmatch('[0-9a-f]{64}',p[key]):raise ValueError('malformed main digest: '+key)
 for key in ('final_EXEC_ELF_reviewed','all14_modules_reviewed','actual_KOS_and_inline_memory_owners_reviewed','compile_preprocess_objects_link_reviewed','private_certificate_SDK_and_room_metadata_reviewed','programme_assets_ISO_readback_reviewed','native_controller_reviewed','source_literal_clean','trace_lock_held','census_mode1_only_acknowledged','census600_completion_and_flush_required','actual_cuts_pixels_and_hardware_pending'):
  if r.get(key)is not True:raise ValueError('main clearance absent: '+key)
 lane=r.get('lane_live_guests');count=r.get('global_live_guests')
 if type(lane)is not int or lane not in(0,1)or type(count)is not int or not lane<=count<16:raise ValueError('lane2/global16 admission required')
 age=(datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat(r['capacity_reviewed_utc'])).total_seconds()
 if not 0<=age<=60:raise ValueError('fresh main capacity review required')
 return r

def validate_profile(argv,output,authority,P,sha,HELPER,API,COUNTER):
 if not authority:raise ValueError('separate main allocation required')
 profile_path,profile_pin,allocation_path,allocation_pin=authority
 if sha(profile_path)!=profile_pin or sha(allocation_path)!=allocation_pin:raise ValueError('profile/allocation changed')
 p=json.loads(Path(profile_path).read_text());allocation=json.loads(Path(allocation_path).read_text())
 if allocation!=dict(allocated=True,profile_sha256=profile_pin,controller_sha256=sha(P/'contain.py'),attempt_limit=1,guard_seconds=59,closure_seconds=59.5):raise ValueError('exact one-attempt allocation required')
 if sha(P/'contain.py')!=CONTAIN_SHA:raise ValueError('immutable containment changed')
 fixed_stock_contract(p);root_review_contract(p)
 if argv!=[sys.executable,'-B',str(P/'stock_child.py'),str(profile_path)]or argv!=p['controller_child_argv']or str(Path(output))!=p['output']or Path(p['capture']).parent!=Path(output):raise ValueError('exact child/output differs')
 if Path(output).name!=OUTPUT_NAME:raise ValueError('fixed distinct census output required; no retry')
 from bindings import verify_bound
 bound_inputs={};binding=verify_bound(bound_inputs)
 if any(p['inputs'].get(k)!=v for k,v in bound_inputs.items()):raise ValueError('bound programme/source adapter input missing')
 for field,record in [('ownership_audit_sha256',binding['ownership_audit']),('kos_receipt_sha256',binding['kos_receipt']),('module_roster_sha256',binding['module_roster']),('normalization_seal_sha256',binding['normalization_source_seal'])]:
  if p.get(field)!=record['sha256']:raise ValueError('launch exact receipt binding differs: '+field)
 env={k:v for k,v in os.environ.items()if k.startswith(('RE4DC_','FP_NOLIMIT'))}
 if p['environment']!=env or env!=dict(RE4DC_EMU='console',RE4DC_MAX_FLYCASTS='16',RE4DC_CONSOLE_EXE=p['console_source'],FP_NOLIMIT='1'):raise ValueError('literal console environment required')
 for path in(sys.executable,*P.glob('*.py'),P/'fixtures.json',HELPER,API,COUNTER,p['stock_runner'],p['console_source']):
  if str(Path(path))not in p['inputs']:raise ValueError('execution input pin missing: '+str(path))
 if p['inputs'][p['stock_runner']]!=p['stock_sha256']or p['inputs'][p['console_source']]!=p['console_sha256']:raise ValueError('stock/console pin differs')
 if p['stock_sha256']!=STOCK_SHA:raise ValueError('only reviewed exact stock fp_run supported')
 for path,pin in p['inputs'].items():
  if sha(path)!=pin:raise ValueError('input changed: '+path)
 for target,ref in p['hardlink_refs'].items():
  src=Path(ref['source']);st=src.stat();target=Path(target)
  if src.resolve()!=src.absolute()or(st.st_size,st.st_ino,st.st_dev,st.st_nlink)!=(ref['bytes'],ref['inode'],ref['device'],ref['links_before']):raise ValueError('retained hardlink source changed')
  if p['inputs'].get(str(src))!=ref['sha256']or target.parent!=Path(p['capture'])or target.name not in('track02.raw','track03.iso'):raise ValueError('only exact pinned twin links exempt')
 if{Path(x).name for x in p['hardlink_refs']}!={'track02.raw','track03.iso'}:raise ValueError('exact twin hardlink set required')
 return p
