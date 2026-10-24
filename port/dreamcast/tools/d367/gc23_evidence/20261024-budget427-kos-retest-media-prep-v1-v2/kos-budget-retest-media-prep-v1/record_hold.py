"""Freeze read-only capacity HOLD, original contracts and target terminal identity."""
from pathlib import Path
import hashlib,json,sys,types,datetime
HERE=Path(__file__).resolve().parent
assert sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
path=HERE/'capacity.py';m=types.ModuleType('capacity');exec(compile(path.read_bytes(),str(path),'exec',dont_inherit=True),dict(m.__dict__,__file__=str(path)))
# Load source directly, never adjacent pyc.
scope={'__file__':str(path),'__name__':'capacity_source'};exec(compile(path.read_bytes(),str(path),'exec',dont_inherit=True),scope)
def row(p):
 p=Path(p)
 with p.open('rb') as f:h=hashlib.file_digest(f,'sha256').hexdigest()
 return dict(path=str(p),bytes=p.stat().st_size,sha256=h)
def read(p):return json.loads(Path(p).read_text())
lane=HERE.parent;receipt=Path('/dev/shm/gc-motion24-budget-on-cont-v1-2e6wsv2a/continuation-receipt.json')
pin=row(receipt);assert pin['sha256']=='4cccda258c4db04e5be740be727cf9b7af20e94a289df5401ee8bd916470e0b9'
terminal=read(receipt);assert terminal['complete'] and terminal['source']=='427784b1f48aa30742850bb5025925ab619b740e' and terminal['arms']['off']['reused'] and not terminal['arms']['off']['new_SDK'] and terminal['arms']['on']['complete']
paths=[lane/'qa-memory-media-prep'/n for n in ['MEDIA-PLAN.json','FUTURE-GUEST-COMMANDS.json','CURRENT-CANDIDATE-MANIFEST.json','SOURCE-IP.BIN','fixtures/kos-fight-49152-0.txt','fixtures/kos-fight-49152-1.txt']]
paths += [lane/'kos-failure-audit-v1'/n for n in ['CAPTURE-ARITHMETIC.json','SOURCE-BINARY-READBACK.json','NEXT-DIAGNOSTIC-PAIR.json']]
paths += [lane/'pillow-isolated-prep-v1'/n for n in ['SOURCE-SEAL.json','PILLOW-PINS.json','pillow_launcher.py']]
report=dict(status='CAPACITY_HOLD_NO_STAGE_NO_GUEST',timestamp_UTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),capacity=scope['census'](scope['ROOTS']),original_contract_pins=[row(p) for p in paths],corrected_terminal=pin,target_files={a:terminal['arms'][a]['files'] for a in ['off','on']},target_independent_readback='PENDING_ROOT_PROVIDED_SEAL',durable_programmes='PENDING_ROOT_EXPORT',no_media_or_asset_payload_copies=True,cleanup=0,stage=0,SDK=0,guest=0,limits='Unchanged cumulative4GiB fails before stage. No reinterpretation, weaker cap, deletion, new image, H2 or memory acceptance. Root must inspect separately approved reclaim/reuse before a stage contract can be finalized.')
assert not report['capacity']['within_cap']
with (HERE/'CAPACITY-HOLD.json').open('x') as f:json.dump(report,f,indent=1);f.write('\n')
print(json.dumps(row(HERE/'CAPACITY-HOLD.json')))
