from pathlib import Path
import hashlib, json, subprocess, sys, tempfile
import contracts as c
P = Path(__file__).resolve().parent
log = subprocess.run([sys.executable, '-B', str(P/'test_runner.py'), '-v'], capture_output=True, text=True)
if log.returncode: raise RuntimeError(log.stdout+log.stderr)
checks = []
stage = json.loads(Path('C:/Flycast-Evidence/re4-dreamcast/pvs23-20261022/actor23-bea2d402-on-q01/stage-receipt.json').read_bytes())
bind = json.loads((P.parent/'native-census-bea2r2/BINDINGS.json').read_bytes())
for key in ('ownership_audit','kos_receipt','module_roster'):
 c.require_bound_receipt(stage[key],bind[key],Path)
 checks.append(key+': actual normalized path, same file and SHA pass')
for key in ('ownership_audit','kos_receipt','module_roster'):
 bad = dict(stage[key], sha256='0'*64)
 try: c.require_bound_receipt(bad,bind[key],Path)
 except ValueError: checks.append(key+': wrong hash refused')
 else: raise AssertionError('wrong hash admitted')
with tempfile.TemporaryDirectory(dir=P) as folder:
 f = Path(folder)/'different.json'; f.write_bytes(Path(stage['ownership_audit']['path']).read_bytes())
 try: c.require_bound_receipt(dict(stage['ownership_audit'],path=str(f)),bind['ownership_audit'],Path)
 except ValueError: checks.append('different file with identical content refused')
 else: raise AssertionError('different path admitted')
result=dict(status='PASS',methods=8,existing_test_output=log.stdout+log.stderr,receipt_controls=checks,guest=False)
(P/'HOST-TEST-RESULTS.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))