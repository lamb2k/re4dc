"""Root-authorized read-only binding after real independent OFF/ON handback.

No SDK, media writes or guest. All inputs and output metadata paths are fixed.
The original baseline/capacity and missing-track HOLD are never rewritten.
"""
from pathlib import Path
import argparse,datetime,hashlib,json,sys,types
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent/'review-kos-budget-retest-media-poststage-v2'
HANDOFF=ROOT/'ROOT-RECOVERY-HANDOFF.json'

def read(p):return json.loads(Path(p).read_bytes())
def row(p):
 with Path(p).open('rb') as f:d=hashlib.file_digest(f,'sha256').hexdigest()
 return dict(size=Path(p).stat().st_size,sha256=d)
def verify(p,pin):
 if row(p)!=pin:raise RuntimeError('Exact input changed: '+str(p))
def fresh(n,j):
 with (HERE/n).open('x') as f:json.dump(j,f,indent=1);f.write('\n')
def encoded(j):return (json.dumps(j,indent=1)+'\n').encode()
def load(name,path):
 raw=Path(path).read_bytes();m=types.ModuleType(name);m.__file__=str(path);sys.modules[name]=m;exec(compile(raw,str(path),'exec',dont_inherit=True),m.__dict__);return m

def actual_drift(old,current):
 differences=[]
 for p in sorted(set(old['members'])|set(current['members'])):
  a=old['members'].get(p);b=current['members'].get(p)
  # Increased hardlink counts alone are not changed bytes or missing identity.
  if a and b and all(a[k]==b[k] for k in ['size','dev','ino','sha256']) and b['nlink']>=a['nlink']:continue
  if a==b:continue
  differences.append(dict(path=p,old=a,current=b))
 return differences

if __name__=='__main__':
 if not (__debug__ and sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode):raise SystemExit('Isolated nonoptimized WSL source required')
 ap=argparse.ArgumentParser();ap.add_argument('--source-seal-sha256',required=True);ap.add_argument('--handoff-sha256',required=True);a=ap.parse_args()
 source_seal=HERE/'SOURCE-REVIEW-SEAL.json'
 if row(source_seal)['sha256']!=a.source_seal_sha256:raise SystemExit('Wrong independently reviewable source seal')
 for n,v in read(source_seal)['members'].items():verify(HERE/n,v)
 if HANDOFF.is_symlink() or row(HANDOFF)['sha256']!=a.handoff_sha256:raise SystemExit('Exact root recovery handoff required')
 h=read(HANDOFF)
 if not (h['approved_readonly_binding'] is True and h['source']=='427784b1f48aa30742850bb5025925ab619b740e' and h['scope']=='FULL_MEDIA_READBACK_AND_EXPLICIT_CURRENT_BASELINE_ONLY_NO_GUEST'):raise SystemExit('No root baseline-only allocation')
 r=load('binding_context',HERE/'recovery_context.py');c=load('binding_common',HERE/'common.py')
 if h['off_base']!=str(r.OFF) or h['on_base']!=str(r.ON):raise SystemExit('Wrong actual protected media roots')
 final=ROOT/'FINAL-READBACK.json';verify(final,h['poststage_identity']);report=read(final)
 if report['status']!='CLEAR_RECOVERY_PAYLOAD_READBACK_ONLY_NO_GUEST' or report['payload_contract_source']!=r.SOURCE:raise SystemExit('Fresh independent both-media CLEAR required')
 r.producer_guard(report)
 # The original sealed reader verifies all1715 ISO files/IP/sixredirects;
 # the actual Rain-produced OFF ELF provenance stays distinct from427.
 if c.sha(c.MEDIA/'TOOLCHAIN-SEAL.json')!=c.MEDIA_SEAL:raise SystemExit('Original reader source changed')
 for n,v in c.read(c.MEDIA/'TOOLCHAIN-SEAL.json')['members'].items():c.verify(c.MEDIA/n,v)
 base=c.module('binding_stage_core',c.MEDIA/'core.py',c.read(c.MEDIA/'TOOLCHAIN-SEAL.json')['members']['core.py']['sha256'])
 actual={}
 for arm,path in [('off',r.OFF),('on',r.ON)]:
  got=r.media_readback(base,c,arm,path);expected=report['arms'][arm]
  if expected['base']!=str(path) or expected['actual_producer_source']!=(r.PRODUCER_OFF if arm=='off' else r.SOURCE):raise SystemExit('Actual producer/source root rebound')
  if any(got[k]!=expected[k] for k in ['manifest','redirect_records','tracks']):raise SystemExit('Fresh actual payload/IP/redirect/track differs from independent readback')
  if r.host_metadata(path,got['tracks']['track03.iso']['sha256'])!=expected['host_base_metadata']:raise SystemExit('Fresh host base metadata differs from independent readback')
  actual[arm]=got
 if actual['on']['tracks']['track03.iso']['sha256']!='86d1f4107417912abc74af0e2005a3bbd79a2eed03e543721db6e022dd815dfa':raise SystemExit('Corrected ON image changed')
 # Explicit old->current differences are root-approved by their exact JSON
 # identity. Do not auto-forgive additional KEEP, retired image or inode drift.
 baseline=r.inventory(r.BASELINE_ROOTS,hashes=True)
 old=c.read(c.MEDIA/'BASELINE.json');prior={p:v for p,v in baseline['members'].items() if any(Path(p).is_relative_to(Path(root)) for root in old['roots'])}
 drift=actual_drift(old,dict(members=prior))
 drift_bytes=(json.dumps(drift,indent=1)+'\n').encode();drift_identity=dict(size=len(drift_bytes),sha256=hashlib.sha256(drift_bytes).hexdigest())
 if h['approved_old_to_current_drift_identity']!=drift_identity:
  fresh('OLD-TO-CURRENT-DRIFT-CANDIDATE.json',drift)
  raise SystemExit('Current drift differs from root acknowledgement; candidate preserved, no baseline bound')
 if baseline['unique_bytes']>r.AGG:raise SystemExit('Current retained baseline already exceeds aggregate6.5GiB')
 fs=__import__('os').statvfs('/mnt/c')
 if fs.f_bavail*fs.f_frsize<r.ADMIT:raise SystemExit('C26GiB admission')
 baseline.update(status='EXPLICIT_CURRENT_RETAINED_BASELINE_AFTER_VERIFIED_FRESH_OFF',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source=r.SOURCE,root_handoff=dict(path=str(HANDOFF),identity=row(HANDOFF)),approved_old_to_current_drift_identity=drift_identity,allocation=dict(new_delta_cap=r.DELTA,aggregate_cap=r.AGG,C_start=r.ADMIT,C_floor=r.FLOOR))
 old_disappearance=HERE.parent/'kos-budget-retest-guest-prep-v1/BASELINE-DRIFT.json'
 baseline_bytes=encoded(baseline)
 binding=dict(status='BOUND_FRESH_RECOVERY_OFF_AND_ON_FULL_READBACK_NO_GUEST',source=r.SOURCE,off_actual_producer_source=r.PRODUCER_OFF,off_payload_equivalence_only=True,old_image_restoration_claim=False,off_base=str(r.OFF),on_base=str(r.ON),old_disappearance=dict(path=str(old_disappearance),identity=row(old_disappearance)),baseline_path=str(HERE/'CURRENT-BASELINE.json'),baseline_identity=dict(size=len(baseline_bytes),sha256=hashlib.sha256(baseline_bytes).hexdigest()),poststage=dict(path=str(final),identity=row(final)),off_actual_track_sha256=actual['off']['tracks']['track03.iso']['sha256'],root_handoff=dict(path=str(HANDOFF),identity=row(HANDOFF)))
 r.binding_guard(binding)
 outputs={'CURRENT-BASELINE.json':baseline,'RECOVERY-BINDING.json':binding,**{arm.upper()+'-FRESH-READBACK.json':v for arm,v in actual.items()}}
 new=r.inventory([str(HERE),str(r.FINAL),*map(str,c.META_ROOTS)],allow_absent=True)
 state=r.account(baseline,baseline,new,fs.f_bavail*fs.f_frsize,r.ADMIT);reserve=sum(len(encoded(v)) for v in outputs.values())
 if reserve+state['new_unique_bytes']>r.DELTA or reserve+state['aggregate_bytes']>r.AGG or state['C_free']-reserve<r.FLOOR:raise SystemExit('Binding metadata reservation exceeds successor caps/floor')
 for name,value in outputs.items():
  fs=__import__('os').statvfs('/mnt/c')
  if fs.f_bavail*fs.f_frsize<r.FLOOR+len(encoded(value)):raise SystemExit('C24GiB floor before metadata write')
  fresh(name,value)
 print(json.dumps(dict(status='CURRENT_RECOVERY_METADATA_BOUND_NO_GUEST',baseline=row(HERE/'CURRENT-BASELINE.json'),binding=row(HERE/'RECOVERY-BINDING.json'),source_review_seal=row(source_seal))))
