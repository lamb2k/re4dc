"""Root bounded full-log adapter. Same sealed Parser; no log filtering or row relaxation."""
from pathlib import Path
import sys,stat,hashlib,json
KIT=Path('/mnt/c/Game Dev/Emulators/codex-lanes/gc-motion24/kos-census-media-prep-v1')
sys.path.insert(0,str(KIT))
import common as c
c.tool_integrity()
from census import Parser
from elf import ELF
import bind
assert len(sys.argv)==3 and sys.argv[1] in {'off','on'}
arm=sys.argv[1];out=Path(sys.argv[2]);assert not out.exists()
binding=bind.validate(c.read(KIT/'BINDING.json'),False);a=binding['arms'][arm];c.verify(a['ELF']['path'],a['ELF']['identity'])
elf=ELF(a['ELF']['path'],a['ELF']['identity']['sha256']);parser=Parser(elf)
log=c.FINAL/'captures'/('kos-'+arm+'-0-0-r1')/'run-output.txt'
s=log.stat();assert stat.S_ISREG(s.st_mode) and s.st_size<=64*1024**2
h=hashlib.sha256();count=0
with log.open('rb') as f:
 while True:
  line=f.readline(2049)
  if not line:break
  assert len(line)<=2048,'Overlong full-source log line'
  h.update(line);count+=len(line);assert count<=64*1024**2
  parser.feed(line.rstrip(b'\n').decode('utf-8',errors='replace'))
after=log.stat();assert (after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns)==(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns) and count==s.st_size
result=parser.result();result.update(arm=arm,log=str(log),log_bytes=count,log_sha256=h.hexdigest(),binding_sha256=c.sha(KIT/'BINDING.json'),adapter_sha256=c.sha(__file__),adapter_scope='Full unchanged log streamed with64MiB cap and2048-byte lines; sealed semantic Parser unchanged. No steady/coverage acceptance inferred.')
c.fresh(out,result)
print(json.dumps({k:result[k] for k in ['status','valid_whole_groups','log_bytes','log_sha256']}))
