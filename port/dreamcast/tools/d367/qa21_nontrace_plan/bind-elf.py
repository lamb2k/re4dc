#!/usr/bin/env python3
"""Offline exact ELF/program/overlay binding, no emulator or stage operations.
Expected JSON: elf_sha256, program_sha256, overlays {filename:sha256}.
A matching overlay ELF-binding receipt remains a separate prerequisite.
"""
import argparse,hashlib,json,importlib.util
from pathlib import Path
from elftools.elf.elffile import ELFFile

def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 ap.add_argument('directory',type=Path);ap.add_argument('expected',type=Path);ap.add_argument('layout',type=Path);ap.add_argument('output',type=Path)
 a=ap.parse_args();e=json.loads(a.expected.read_text());layout=json.loads(a.layout.read_text())
 if a.output.exists():raise ValueError('refusing overwrite')
 if len(e['overlays'])!=14:raise ValueError('exactly14 overlays required')
 if any(Path(n).name!=n or not n.endswith('.ovl') for n in e['overlays']):raise ValueError('overlay filenames must be simple .ovl names')
 files={'re4dc-game.elf':e['elf_sha256'],'program.bin':e['program_sha256'],**e['overlays']}
 actual={n:sha(a.directory/n) for n in files}
 if actual!=files:raise ValueError('exact file identity mismatch')
 if layout['elf_sha256']!=e['elf_sha256']:raise ValueError('layout ELF mismatch')
 with (a.directory/'re4dc-game.elf').open('rb') as f:
  elf=ELFFile(f)
  sy={s.name:int(s.entry.st_value) for s in elf.get_section_by_name('.symtab').iter_symbols() if s.entry.st_shndx!='SHN_UNDEF'}
  if any('deathTrace' in n or 'death_trace' in n for n in sy):raise ValueError('diagnostic symbols present')
  if any(b'death trace:' in seg.data() for seg in elf.iter_segments() if seg['p_type']=='PT_LOAD'):raise ValueError('trace text present')
 spec=importlib.util.spec_from_file_location('adapter',Path(__file__).with_name('observer-adapter.py'));mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
 selected=mod.select_symbols(sy)
 result={'read_only':True,'scope':'offline identity and generic-symbol binding only; no runtime/stage/overlay-relocation acceptance',
 'actual':actual,'symbols':selected,'qa_available':all(selected[n] is not None for n in mod.OPTIONAL_QA),
 'layout_sha256':sha(a.layout),'expected_manifest_sha256':sha(a.expected)}
 a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':True,'qa_available':result['qa_available']}))
if __name__=='__main__':main()
