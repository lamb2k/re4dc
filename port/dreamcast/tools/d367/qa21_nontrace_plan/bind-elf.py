#!/usr/bin/env python3
"""Offline exact ELF/program/overlay binding, no emulator or stage operations.
Expected JSON: elf_sha256, program_sha256, overlays {filename:sha256}.
A matching overlay ELF-binding receipt remains a separate prerequisite.
"""
import argparse,hashlib,json,importlib.util,collections
from pathlib import Path
from elftools.elf.elffile import ELFFile

def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 ap.add_argument('directory',type=Path);ap.add_argument('expected',type=Path);ap.add_argument('layout',type=Path);ap.add_argument('output',type=Path);ap.add_argument('--source-contract',type=Path,required=True)
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
  groups=collections.defaultdict(list)
  for symbol in elf.get_section_by_name('.symtab').iter_symbols():
   if symbol.name and symbol.entry.st_shndx!='SHN_UNDEF':
    groups[symbol.name].append(dict(address=int(symbol.entry.st_value),bytes=int(symbol.entry.st_size),type=symbol.entry.st_info.type,binding=symbol.entry.st_info.bind,section=symbol.entry.st_shndx))
  sy={n:items[0]['address'] for n,items in groups.items() if len({(v['address'],v['bytes'],v['type']) for v in items})==1}
  duplicates={n:items for n,items in groups.items() if len(items)>1}
  if any('deathTrace' in n or 'death_trace' in n for n in sy):raise ValueError('diagnostic symbols present')
  if any(b'death trace:' in seg.data() for seg in elf.iter_segments() if seg['p_type']=='PT_LOAD'):raise ValueError('trace text present')
 spec=importlib.util.spec_from_file_location('adapter',Path(__file__).with_name('observer-adapter.py'));mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
 sy=mod.resolve_symbol_groups(groups)
 selected=mod.select_symbols(sy)
 sizes={'_pG':4,'_pPL':4,'_pSys':4,'_ItemMgr':layout['found']['cItemMgr']['bytes'],'_Key':layout['found']['KeyWork']['bytes'],'_SceSys':layout['found']['cSceSys']['bytes'],'_SubScreenWk':layout['found']['SUB_SCREEN']['bytes']}
 for n,size in sizes.items():
  if n not in sy or groups[n][0]['bytes']!=size or groups[n][0]['type']!='STT_OBJECT':raise ValueError('symbol object ABI mismatch '+n)
 for n in mod.OPTIONAL_QA:
  if n in sy and (groups[n][0]['bytes']!=4 or groups[n][0]['type']!='STT_OBJECT'):raise ValueError('QA scalar ABI mismatch '+n)
 source_contract=json.loads(a.source_contract.read_text())
 if source_contract['source']!=e['source']:raise ValueError('source contract mismatch')
 abi=mod._contract.validate_layout(layout)
 result={'read_only':True,'scope':'offline identity and generic-symbol binding only; no runtime/stage/overlay-relocation acceptance',
 'actual':actual,'symbols':selected,'qa_available':all(selected[n] is not None for n in mod.OPTIONAL_QA),
 'source':e['source'],'source_contract_sha256':sha(a.source_contract),'abi':abi,'duplicate_symbols':duplicates,'selected_symbol_records':{n:groups.get(n,[]) for n in selected},'unavailable_symbols':{n:('ambiguous' if n in groups else 'absent') for n,v in selected.items() if v is None},'layout_sha256':sha(a.layout),'expected_manifest_sha256':sha(a.expected)}
 a.output.write_text(json.dumps(result,indent=2)+'\n',newline='\n');print(json.dumps({'passed':True,'qa_available':result['qa_available']}))
if __name__=='__main__':main()
