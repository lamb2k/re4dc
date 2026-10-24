from pathlib import Path
import hashlib,json,subprocess
C=Path('/mnt/c/Game Dev/Emulators/codex-lanes/dedup-offline23')
E=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/dedup-offline23-20261023/current-4be08e01')
r=subprocess.run(['python3',str(C/'test_current_gdemu10.py')],capture_output=True,text=True,env={'PATH':'/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1'})
assert r.returncode==0,(r.stdout,r.stderr)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
out=E/'gdemu10-host-controls-r1.json';assert not out.exists()
out.write_text(json.dumps(dict(status='PASS_HOST_ACTUAL_SEED1_BINDING_NEGATIVES',source='4be08e0110592510e3630c01fa9f49b3ac2fed3d',frozen_plan_sha256=sha(E/'gdemu10-plan-r1.json'),test_sha256=sha(C/'test_current_gdemu10.py'),helper_sha256=sha(C/'current-d5c-gdemu10.py'),test_groups=2,negative_controls=['absent-seed','wrong-seed','wrong-profile','wrong-source','actual-absent-env-seed','actual-wrong-env-seed','actual-wrong-env-profile','serial-seed','profile-only-no-read','no-landing','no-endpoint','bad-read','deadline'],stdout=r.stdout,stderr=r.stderr),indent=2)+'\n')
print('HOST_GDEMU10_RECEIPT',sha(out))

