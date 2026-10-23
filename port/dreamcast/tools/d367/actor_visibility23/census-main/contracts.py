"""Pure main-runner checks; no process or native queries at import."""
from pathlib import Path
import datetime,hashlib,json
HERE=Path(__file__).resolve().parent
LANE=HERE.parent
ADAPTER=LANE/'native-census-bea2r2'
SOURCE='bea2d402ba06d41fb7b39946b5a9431a72f5b52a'
ADAPTER_SHA='3efd021c932f037fa57cffa85cd95f38a6e7c8ac4d235dc708e240fdc6665bc3'
PROGRAMME_SHA='6eac4f0f475c8d5508427ff4c2d0e65dd7e80fdbfb53bb3e8706d0755d2f6f24'
AUDIT_SHA='865fa08adf6f2d6d035afc82bf13989111279b9ed769f1f21143df4d3ec6ac0a'
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
 if stage.get('programme_receipt_sha256')!=PROGRAMME_SHA or stage.get('ownership_audit',{}).get('sha256')!=AUDIT_SHA or set(stage.get('fixture_pins',{}))!={CASE} or 'fixture_rebind'in stage:raise ValueError('current image and sole census fixture stage required')
 if stage['fixture_pins'][CASE]['sha256']!='6b28db8cdec172110720ab105fd9c3ce68b15f10d4607eb207dc19829d43cbe3':raise ValueError('exact approved census fixture required')
 return stage
def verify_source(review_path,review_pin):
 review=checked(review_path,review_pin);seal=HERE/'SOURCE-SEAL.json'
 if review.get('status')!='CLEAR' or review.get('wrapper_source_seal_sha256')!=sha(seal):raise ValueError('exact independent main-wrapper source review required')
 for name,row in json.loads(seal.read_bytes())['files'].items():
  path=HERE/name
  if not path.resolve().is_relative_to(HERE.resolve()) or sha(path)!=row['sha256'] or path.stat().st_size!=row['bytes']:raise ValueError('sealed main wrapper input changed: '+name)
 deps=json.loads((HERE/'DEPENDENCIES.json').read_bytes())
 for row in deps['files']:
  if sha(row['path'])!=row['sha256'] or Path(row['path']).stat().st_size!=row['bytes']:raise ValueError('main wrapper dependency changed: '+row['path'])
 if sha(ADAPTER/'SOURCE-SEAL.json')!=ADAPTER_SHA:raise ValueError('exact census source seal required')
 for name,row in json.loads((ADAPTER/'SOURCE-SEAL.json').read_bytes())['files'].items():
  path=ADAPTER/name
  if sha(path)!=row['sha256'] or path.stat().st_size!=row['bytes']:raise ValueError('census adapter source changed')
 census_review=checked(deps['census_review']['path'],deps['census_review']['sha256'])
 if census_review.get('status')!='CLEAR' or census_review.get('adapter_source_seal_sha256')!=ADAPTER_SHA:raise ValueError('exact independent census review required')
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