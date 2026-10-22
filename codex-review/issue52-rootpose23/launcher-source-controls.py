"""Extract prepared launcher's pure helpers; fake children only, no imports/native queries."""
import ast,hashlib,json,threading,tempfile
from pathlib import Path
L=Path('/mnt/c/Game Dev/Emulators/codex-lanes/rootpose23/run-s30-console01.py')
F=Path('/root/probe/codex-rootpose23/port/dreamcast/tools/d367/fullplay/fp_run.py')
tree=ast.parse(L.read_text());main=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='main')
functions={n.name:n for n in main.body if isinstance(n,ast.FunctionDef)}
class FakeClock:
 t=0
 def monotonic(self):return self.t
class Child:
 def __init__(self):self.alive=True
 def poll(self):return None if self.alive else 0
 def terminate(self):self.alive=False
 def wait(self,timeout):return 0
 def kill(self):self.alive=False
clock=FakeClock();owned=[]
def original(*a,**k):clock.t=2;return Child()
G={'lock':threading.Lock(),'time':clock,'deadline':1,'reasons':[],'original':original,'owned':owned}
exec(compile(ast.Module(body=[functions['spawn']],type_ignores=[]),str(L),'exec'),G)
c=G['spawn'](['fake-never-executed'])
assert clock.t>G['deadline']and len(owned)==1 and c.alive
late={'control':'fake Popen admitted at0 returns at2 afterdeadline1','observed':'child appended and alive; no post-create deadline check','passes_as_reproduction':True}
class Done:
 def wait(self,n):return False
class Cap:
 def exists(self):return True
class Mod:
 CAPTURE_LIMIT=60*1024*1024;FLOOR=0
 def usage(self,p):raise OSError('fake concurrent stat disappearance')
G={'done':Done(),'time':clock,'deadline':3,'CAP':Cap(),'mod':Mod(),'reasons':[],'close_owned':lambda:None,'ROOT':Path('/never-used')}
exec(compile(ast.Module(body=[functions['guard']],type_ignores=[]),str(L),'exec'),G)
try:G['guard']();raise AssertionError('expected unhandled error')
except OSError:pass
assert G['reasons']==[]
err={'control':'fake quota stat raisesOSError','observed':'monitor unwinds without reason/cleanup','passes_as_reproduction':True}
ft=ast.parse(F.read_text());usage=next(n for n in ft.body if isinstance(n,ast.FunctionDef)and n.name=='usage')
G={'TRACKS':('disc.gdi','track01.bin','track01.iso','track02.raw','track03.bin','track03.iso')}
exec(compile(ast.Module(body=[usage],type_ignores=[]),str(F),'exec'),G)
T=Path('/root/probe/codex-issue52-rootpose23-review/codex-review/issue52-rootpose23')
with tempfile.TemporaryDirectory(prefix='fake-quota-',dir=T)as d:
 q=Path(d)
 for n in ['flycast.exe','track01.iso','evidence.txt']:(q/n).write_bytes(b'x'*128)
 measured=G['usage'](q)
 assert measured==128
quota={'control':'three owned128B files, no hardlinks','actual_file_bytes':384,'reported_usage':measured,'excluded_new_copies':['flycast.exe','track01.iso'],'passes_as_reproduction':True}
out={'source_only_fake_helpers':True,'no_native_query_subprocess_or_guest':True,'launcher_sha256':hashlib.sha256(L.read_bytes()).hexdigest(),'fp_run_sha256':hashlib.sha256(F.read_bytes()).hexdigest(),'controls':[late,err,quota]}
P=T/'LAUNCHER-fake-controls.json';assert not P.exists();P.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))

