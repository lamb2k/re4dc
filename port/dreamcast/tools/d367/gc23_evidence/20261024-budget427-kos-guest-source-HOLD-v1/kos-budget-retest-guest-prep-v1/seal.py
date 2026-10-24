"""Freeze source candidate with honest environmental HOLD, never guest authority."""
from pathlib import Path
import datetime,json,sys,types
HERE=Path(__file__).resolve().parent
assert __debug__ and sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
p=HERE/'common.py';c=types.ModuleType('guest_common');c.__file__=str(p);sys.modules[c.__name__]=c;exec(compile(p.read_bytes(),str(p),'exec'),c.__dict__);k=c.context()
host=c.read(HERE/'HOST-CONTROLS.json');assert host['tests']==53 and host['failures']==2 and host['errors']==0 and not host['success']
native=c.read(HERE/'WINDOWS-HOST-CONTROLS.json');assert native['status']=='WINDOWS_OWNED_BENIGN_CHILD_CONTROLS_PASS' and len(native['controls'])==8
assert 'actual_exact_instance_terminated_and_exit_observed' in native['controls']
try:c.capacity(k)
except AssertionError as exc:assert str(exc)=='Historical baseline byte total changed';resource_refusal=str(exc)
else:raise AssertionError('External media state changed; inspect before freezing this HOLD')
assert not (HERE/'attempts').exists() and not c.read(HERE/'ROOT-GUEST-GRANT-TEMPLATE.json')['approved']
now=datetime.datetime.now(datetime.timezone.utc).isoformat();status=dict(status='SOURCE_HOST_CANDIDATE_HOLD_BASELINE_DRIFT_NO_GUEST',timestamp_UTC=now,source=c.SOURCE,media_kit_sha256=c.MEDIA_SEAL,actual_poststage_historical=c.read(HERE/'POSTSTAGE-PINS.json'),public_controls=host,Windows_controls=native['controls'],current_resource_guard_refusal=resource_refusal,drift_receipt=c.row(HERE/'BASELINE-DRIFT.json'),SDK=0,stage=0,production_locks=0,guest=0,H2='HELD',limits='No source/runtime acceptance or memory pass. Root explicit successor media/baseline decision required; no rebase/restore/substitution was performed.')
c.fresh(HERE/'STATUS.json',status)
members={p.name:c.row(p) for p in HERE.iterdir() if p.is_file() and p.name not in ['TOOLCHAIN-SEAL.json','READBACK.json']}
c.fresh(HERE/'TOOLCHAIN-SEAL.json',dict(status=status['status'],source=c.SOURCE,members=members))
c.fresh(HERE/'READBACK.json',dict(status=status['status'],seal=c.row(HERE/'TOOLCHAIN-SEAL.json'),files=len(members),public_tests=53,public_pass=51,environment_guard_refusals=2,Windows_actual_owned_benign_controls=8,current_media_HOLD=True,root_grant=False,SDK=0,stage=0,guest=0))
print(json.dumps(dict(seal=c.row(HERE/'TOOLCHAIN-SEAL.json'),readback=c.row(HERE/'READBACK.json'),status=c.row(HERE/'STATUS.json'))))
