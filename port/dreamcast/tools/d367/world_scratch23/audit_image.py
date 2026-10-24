"""Read-only final-image gate. Does not enable runtime admission or edit KOS."""
import argparse, hashlib, json, pathlib, re, subprocess
EXPECTED = {
 'kernel/arch/dreamcast/kernel/cache.s':'8e0973bea3fd977dee62ed2b3753115d9a9f5084dfbece80e56a22c18d669994',
 'kernel/arch/dreamcast/include/dc/cache.h':'c49bcc60b1f69ab4f9b8f2b9b55148a1ff7ccd213b5c0c40034964f1c96a4fd6',
 'utils/ldscripts/shlelf.xc':'fe2d763124ebb8616f96393c7f1d3b1f7c2aa83593e03bc8060faf28364451c2'}
def digest(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def section(text):
 rows=[]
 for line in text.splitlines():
  m=re.match(r'\s*\d+\s+\.ocram\s+([0-9a-f]+)\s+([0-9a-f]+)\s+([0-9a-f]+)\s+([0-9a-f]+)\s+2\*\*(\d+)',line)
  if m:rows.append(tuple(int(x,16) for x in m.groups()[:4])+(int(m.group(5)),))
 if len(rows)!=1:raise ValueError('expected exactly one .ocram section')
 size,vma,lma,offset,align=rows[0]
 if size!=8192 or vma!=0x7c001000 or align<5:raise ValueError('wrong final .ocram size/address/alignment')
 return dict(bytes=size,address=hex(vma),align=1<<align)
def check_symbols(text):
 rows=[]
 for line in text.splitlines():
  m=re.match(r'^([0-9a-fA-F]+)\s+([0-9a-fA-F]+)\s+\w\s+(.+)$',line)
  if m and 0x7c001000<=int(m.group(1),16)<0x7c003000 and int(m.group(2),16):rows.append(m.groups())
 if len(rows)!=1 or int(rows[0][0],16)!=0x7c001000 or int(rows[0][1],16)!=8192 or 'projected_records' not in rows[0][2]:
  raise ValueError('foreign, missing or overlapping OCRAM owner')
 return rows[0][2]
def audit(elf,kos,modules,prefix):
 def run(tool,*args):return subprocess.check_output([prefix+tool,*map(str,args)],text=True)
 info=run('readelf','-h',elf)
 if not re.search(r'Type:\s+EXEC',info):raise ValueError('requires final EXEC ELF, not relocatable object')
 sec=section(run('objdump','-h',elf));symbols=check_symbols(run('nm','-S','-C','--defined-only',elf))
 # NOLOAD must be NOBITS in the final linked ELF, never silently shipped bytes.
 if not re.search(r'\.ocram\s+NOBITS\s+7c001000\b',run('readelf','-SW',elf)):raise ValueError('.ocram is not final NOLOAD/NOBITS')
 checked={}
 for rel,expected in EXPECTED.items():
  actual=digest(kos/rel)
  if actual!=expected:raise ValueError('KOS source drift: '+rel)
  checked[rel]=actual
 roster=[]
 for p in modules:
  hdr=run('objdump','-h',p)
  if re.search(r'\s\.ocram\s',hdr):raise ValueError('separately linked module owns OCRAM: '+str(p))
  syms=run('nm','-C',p)
  if re.search(r'cache_write_ccr|dcache_toggle_ocram|dcache_toggle_ocindex',syms):raise ValueError('module cache-mode owner: '+str(p))
  roster.append(dict(path=str(p.resolve()),sha256=digest(p)))
 return dict(receipt_version=1,elf=str(elf.resolve()),sha256=digest(elf),ocram=sec,owner=symbols,kos=str(kos.resolve()),kos_sources=checked,modules=roster,
  requires_manual_review='Verify complete runtime module roster, no inline CCR owner or hidden OCRAM pointers; runtime CCR/thread admission remains mandatory. This receipt alone does not prove console correctness.')
def main():
 a=argparse.ArgumentParser();a.add_argument('--elf',required=True,type=pathlib.Path);a.add_argument('--kos',required=True,type=pathlib.Path)
 a.add_argument('--module',action='append',default=[],type=pathlib.Path);a.add_argument('--complete-module-roster-reviewed',required=True,action='store_true')
 a.add_argument('--prefix',default='/opt/toolchains/dc/sh-elf/bin/sh-elf-');a.add_argument('--output',required=True,type=pathlib.Path)
 n=a.parse_args();result=audit(n.elf,n.kos,n.module,n.prefix);n.output.write_text(json.dumps(result,indent=2)+'\n');print('PASS: final linked storage/KOS/module-symbol gate; manual inline-owner review still required')
if __name__=='__main__':main()
