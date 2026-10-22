from pathlib import Path
import hashlib,json,sys
sys.path.insert(0,'C:/Game Dev/Emulators/codex-lanes/feedback21-boss-qa/python-deps')
from elftools.elf.elffile import ELFFile
R=Path('C:/Flycast-Evidence/re4-dreamcast/qa21-combined-regression-20261021');B=R/'builds/combined'
names={'logbuf':'_re4dc_logbuf','head':'_re4dc_log_head','stage':'_re4dc_stage','end':'_end','pG':'_pG','pPL':'_pPL','EmMgr':'_EmMgr','qa_frames':'__ZN12_GLOBAL__N_1L9qa_framesE','qa_flags':'__ZN12_GLOBAL__N_1L7g_flagsE','Joy':'_Joy','Pad_data':'__ZL8Pad_data','SceSys':'_SceSys','SubScreenWk':'_SubScreenWk'}
with (B/'re4dc-game.elf').open('rb') as f:
 sym=ELFFile(f).get_section_by_name('.symtab');symbols={}
 for key,name in names.items():
  found={s['st_value'] for s in sym.get_symbol_by_name(name) or [] if s['st_shndx']!='SHN_UNDEF'}
  assert len(found)==1,(key,found);symbols[key]=hex(found.pop())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
r=json.loads((R/'combined-input/candidate-receipt.json').read_text());assert sha(B/'program.bin')==r['program_sha256'];assert sha(B/'re4dc-game.elf')==r['elf_sha256']
row=dict(input_track03_sha256=r['input_track03_sha256'],disc_track03_name=r['disc_track03_name'],elf_sha256=r['elf_sha256'],disc_program_sha256=r['program_sha256'],elf_binary_sha256=sha(B/'program.bin'),source_candidate=r['source'],symbols=symbols,scope='Fresh combined pause and QA target. Cold or same-program unedited checkpoint lineage only.')
dest=R/'combined-binding.json';assert not dest.exists();dest.write_text(json.dumps(row,indent=2)+'\n');print(json.dumps(row))