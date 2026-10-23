"""Pure main-runner checks; no process or native queries at import."""
from pathlib import Path
import datetime,hashlib,json
HERE=Path(__file__).resolve().parent
LANE=HERE.parent
ADAPTER=HERE
SOURCE='f2405bb06ebaff6e2a7681479d5308ec5d3b988a'
PROGRAMME_SHA='41beee7f50af4ff50c49b03a7cfa53d794086646322c5ebe7a85ffc7805a883d'
FLOOR=20468203520
CASE='r119-census'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def checked(path,pin):
 if sha(path)!=pin:raise ValueError('changed pinned receipt: '+str(path))
 return json.loads(Path(path).read_bytes())
def validate_resources(r,now=None):
 now=now or datetime.datetime.now(datetime.timezone.utc);age=(now-datetime.datetime.fromisoformat(r['utc'].replace('Z','+00:00'))).total_seconds()
 if not 0<=age<=60:raise ValueError('fresh <=60-second main resource admission required')
 if r.get('admitted')is not True or r.get('package_one_guest_admitted')is not True or r.get('errors'):raise ValueError('main resource admission refused')
 if any(type(r.get(k))is not int or r[k]<0 for k in ('root_cap','projected_peak','guest_peak','floor','package_cap','package_current_bytes')):raise ValueError('integer bounded resource counters required')
 if r['root_cap']!=16*1024**3 or r['projected_peak']>r['root_cap'] or r['guest_peak']!=60*1024**2 or r['floor']!=FLOOR:raise ValueError('root/guest/floor resource contract differs')
 if r['package_cap']!=3758096384 or r['package_current_bytes']+r['guest_peak']>r['package_cap']:raise ValueError('package/guest peak exceeds cap')
 return r
def require_no_guests(processes):
 if any(type(processes.get(k))is not int or processes[k]!=0 for k in ('global_live_guests','lane_live_guests')):raise ValueError('this sequential census requires no live guests')
 return processes
def validate_stage(stage):
 if (stage.get('status'),stage.get('source'),stage.get('integration'))!=('ACTOR23_TWIN_STAGED_NO_GUEST',SOURCE,'0b4beb704902a1dc6b2aace056be344863b4a0c1'):raise ValueError('exact fresh coverage stage required')
 if stage.get('programme_receipt_sha256')!=PROGRAMME_SHA or stage.get('ownership_audit',{}).get('sha256')!=audit_pin() or set(stage.get('fixture_pins',{}))!={CASE} or 'fixture_rebind'in stage:raise ValueError('current image and sole census fixture stage required')
 if stage['fixture_pins'][CASE]['sha256']!='6b28db8cdec172110720ab105fd9c3ce68b15f10d4607eb207dc19829d43cbe3':raise ValueError('exact approved census fixture required')
 return stage
def normalization_pin():
 from bindings import NORMALIZATION_SHA
 return NORMALIZATION_SHA

def audit_pin():
 from bindings import pending_safe_binding
 return pending_safe_binding()['ownership_audit']['sha256']

def verify_source(review_path,review_pin):
 review=checked(review_path,review_pin);seal=HERE/'SOURCE-SEAL.json'
 if review.get('status')!='CLEAR' or review.get('wrapper_source_seal_sha256')!=sha(seal):raise ValueError('exact independent material source review required')
 for name,row in json.loads(seal.read_bytes())['files'].items():
  path=HERE/name
  if not path.resolve().is_relative_to(HERE.resolve()) or sha(path)!=row['sha256'] or path.stat().st_size!=row['bytes']:raise ValueError('sealed material source changed: '+name)
 from bindings import verify_bound
 verify_bound({})
 return review

def require_bound_receipt(actual, expected, native_path):
 left = native_path(actual['path'])
 right = native_path(expected['path'])
 if any(p.is_symlink() or not p.is_file() for p in (left, right)):
  raise ValueError('ordinary bound receipt required')
 if left.resolve(strict=True) != right.resolve(strict=True) or not left.samefile(right):
  raise ValueError('bound receipt path identity differs')
 if actual.get('sha256') != expected['sha256'] or sha(left) != expected['sha256']:
  raise ValueError('bound receipt content identity differs')
def validate_native_stage(stage):
 from binding_helpers import native_path
 from bindings import pending_safe_binding
 binding=pending_safe_binding()
 expected=Path('C:/Flycast-Evidence/re4-dreamcast/pvs23-20261022/actor23-f2405bb0-on-q01/base')
 if native_path(stage['base']).resolve()!=expected.resolve():raise ValueError('exact fresh f240 stage path required')
 if 'native_path_provenance' in stage:raise ValueError('canonical original stage required')
 for key in ('ownership_audit','kos_receipt','module_roster'):
  require_bound_receipt(stage[key],binding[key],native_path)
 return stage
