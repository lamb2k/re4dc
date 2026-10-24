from pathlib import Path
import json,hashlib,subprocess,datetime
ROOT=Path('/root/work/lanes/gc-port23-full-target2-scratch')
E=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/gc-port23-20261023/full-target-static1d63-current')
E.mkdir(exist_ok=True)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
r=json.loads((ROOT/'receipt.json').read_text());assert r['complete'] and set(r['arms'])=={'off','on'}
assert all(sha(p)==h for p,h in r['pins'].items())
ends={};sections={};files={};gccount={}
for arm in ['off','on']:
 p=ROOT/arm;o=p/'out';dst=E/arm;dst.mkdir(exist_ok=True)
 for f in ['command.json','symbols.txt']:(dst/f).write_bytes((p/f).read_bytes())
 for f in ['resolved-knobs.txt']:(dst/f).write_bytes((o/f).read_bytes())
 for f in ['aliases.ld','aliases-all.ld','missing.txt','missing.cpp','pass1.log','defined.txt','undefined.txt']:
  s=p/'link-scratch'/f
  assert s.is_file()
  if f in ('aliases.ld','aliases-all.ld','missing.cpp'):assert b'gcasset' not in s.read_bytes()
  (dst/f).write_bytes(s.read_bytes())
 syms=(p/'symbols.txt').read_text().splitlines()
 ends[arm]={line.split()[-1]:int(line.split()[0],16) for line in syms if line.split()[-1] in ('_end','_edata','_etext')}
 gccount[arm]=sum('re4dc_gcasset' in line for line in syms)
 if arm=='off':assert gccount[arm]==0
 else:assert gccount[arm]>0
 for flag,name in [('-l','load-segments.txt'),('-S','sections.txt')]:
  data=subprocess.check_output(['/opt/toolchains/dc/sh-elf/bin/sh-elf-readelf','-W',flag,str(o/'re4dc-game.elf')])
  (dst/name).write_bytes(data)
 sections[arm]=[int(x) for x in r['arms'][arm]['size'].splitlines()[-1].split()[:3]]
 files[arm]=r['arms'][arm]['files']
 for name,v in files[arm].items():assert sha(o/name)==v['sha256']
 assert sha(p/'program.bin')==r['arms'][arm]['raw_sha256']
(E/'receipt.json').write_bytes((ROOT/'receipt.json').read_bytes())
summary=dict(status='FULL_NORMAL_CATALOG0_LINK_COMPLETE_ONLY',source=r['source'],baseline=r['baseline'],time=datetime.datetime.now(datetime.timezone.utc).isoformat(),off_programme_and_all14_identical=True,missing_symbols_both=0,GC_alias_or_stub=False,gc_symbol_counts=gccount,linked_sections=dict(zip(['text','data','bss'],[b-a for a,b in zip(sections['off'],sections['on'])])),linked_section_total=sum(sections['on'])-sum(sections['off']),boundary_symbols=ends,boundary_delta={k:ends['on'][k]-ends['off'][k] for k in ends['off']},raw_hashes={a:r['arms'][a]['raw_sha256'] for a in ['off','on']},scope='Fresh full normal source builds, exact current rP ordered args plus gate/catalog knobs. Real SDK/source/SH4ZAM pins before/after. No linked stubs or GC aliases. Catalog0 only; synthetic configured branch not qualified. No runtime heap, KOS/H2, guest, catalog, I001 or hardware performance acceptance.')
(E/'SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n')
manifest={str(p.relative_to(E)):dict(bytes=p.stat().st_size,sha256=sha(p)) for p in E.rglob('*') if p.is_file() and p.name!='SHA256-MANIFEST.json'}
(E/'SHA256-MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(summary,indent=2))