"""Reproduce only reviewed V2 preauthorization/RAM findings; no SDK/locks/guest."""
from pathlib import Path
import json,subprocess,types,sys
from unittest import mock
K=Path(sys.argv[1]).resolve();R=Path(sys.argv[2]).resolve();R.mkdir(exist_ok=False)
hook=R/'owned-startup-hook.sh';marker=R/'BASH_ENV_EXECUTED'
hook.write_text('printf startup > '+str(marker)+'\n')
p=subprocess.run(['/usr/bin/bash',str(K/'run.sh')],env={'PATH':'/usr/bin:/bin','HOME':'/root','BASH_ENV':str(hook)},capture_output=True,text=True,timeout=5)
assert p.returncode==2 and marker.read_text()=='startup' and 'SOURCE_GRANT_REQUIRED' in p.stdout
mod=types.ModuleType('review_prepare');mod.__file__=str(K/'prepare.py');sys.modules[mod.__name__]=mod;exec(compile(Path(mod.__file__).read_bytes(),mod.__file__,'exec'),mod.__dict__)
class Stats:f_bavail=8*1024**3;f_frsize=1
with mock.patch.object(mod.os,'statvfs',return_value=Stats()),mock.patch.object(Path,'read_text',return_value='MemAvailable: 1024 kB\n') as reader:
 result=mod.free('/dev/shm');calls=reader.call_count
assert result==8*1024**3 and calls==0
(R/'REPRO.json').write_text(json.dumps({'BASH_ENV_before_invalid_grant':True,'returncode':p.returncode,'stdout':p.stdout,'reported_RAM':result,'physical_RAM_mock':1024**2,'MemAvailable_reads':calls,'SDK_or_locks_or_guest':False},indent=2)+'\n')
print('Both V2 findings reproduced; no SDK/locks/guest')
