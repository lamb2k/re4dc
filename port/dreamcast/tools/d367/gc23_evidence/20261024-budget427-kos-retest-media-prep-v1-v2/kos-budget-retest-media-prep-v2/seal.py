"""Final source-only seal; no stage or guest."""
from pathlib import Path
import json,sys,types
HERE=Path(__file__).resolve().parent
assert sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
p=HERE/'core.py';k=types.ModuleType('core');k.__file__=str(p);sys.modules['core']=k;exec(compile(p.read_bytes(),str(p),'exec'),k.__dict__)
assert k.read(HERE/'HOST-CONTROLS.json')['success'];k.validate_binding(k.read(HERE/'BINDING.json'));k.baseline_check();assert not k.FINAL.exists() and not k.WORK.exists()
grant=dict(approved=False,scope='STAGE_ONLY_NO_GUEST_NO_SDK',source=k.SOURCE,toolchain_sha256='ROOT_MUST_PIN_FINAL_SEAL',binding_sha256=k.sha(HERE/'BINDING.json'),baseline_identity=k.row(HERE/'BASELINE.json'),owned_cap_bytes=k.AGG,C_admit_bytes=k.ADMIT,C_floor_bytes=k.FLOOR,arms=['off','on'],existing_OFF_reuse_only=True,new_final_arms=['on'],new_delta_cap=k.DELTA,aggregate_cap=k.AGG)
k.fresh(HERE/'ROOT-STAGE-GRANT-TEMPLATE.json',grant)
members={p.name:k.row(p) for p in HERE.iterdir() if p.is_file() and p.name not in ['TOOLCHAIN-SEAL.json','READBACK.json']}
k.fresh(HERE/'TOOLCHAIN-SEAL.json',dict(status='SOURCE_HOST_PREPARATION_NO_STAGE_NO_GUEST',source=k.SOURCE,members=members,parent_seal_sha256=k.PARENT_SEAL))
k.fresh(HERE/'READBACK.json',dict(status='READY_FOR_INDEPENDENT_PREPARATION_REVIEW_NO_ALLOCATION',seal=k.row(HERE/'TOOLCHAIN-SEAL.json'),baseline=k.row(HERE/'BASELINE.json'),binding=k.row(HERE/'BINDING.json'),capacity=k.capacity(),controls=k.read(HERE/'HOST-CONTROLS.json'),SDK=0,stage=0,guest=0,H2='HELD'))
print(json.dumps(dict(seal=k.row(HERE/'TOOLCHAIN-SEAL.json'),readback=k.row(HERE/'READBACK.json'))))
