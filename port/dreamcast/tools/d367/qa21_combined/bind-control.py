from pathlib import Path
import hashlib,json,sys
sys.path.insert(0,'C:/Game Dev/Emulators/codex-lanes/feedback21-boss-qa/python-deps');from elftools.elf.elffile import ELFFile
R=Path('C:/Flycast-Evidence/re4-dreamcast/qa21-combined-regression-20261021');B=R/'builds/qa-control';S=Path('C:/Flycast-Evidence/re4-dreamcast/feedback21-boss-qa-20261021/qa-repair-input/gdemu')
old=json.loads((R/'combined-binding.json').read_text());names={'logbuf':'_re4dc_logbuf','head':'_re4dc_log_head','stage':'_re4dc_stage','end':'_end','pG':'_pG','pPL':'_pPL','EmMgr':'_EmMgr','qa_frames':'__ZN12_GLOBAL__N_1L9qa_framesE','qa_flags':'__ZN12_GLOBAL__N_1L7g_flagsE','Joy':'_Joy','Pad_data':'__ZL8Pad_data','SceSys':'_SceSys','SubScreenWk':'_SubScreenWk'}
with (B/'re4dc-game.elf').open('rb') as f:
 sym=ELFFile(f).get_section_by_name('.symtab');symbols={}
 for key,name in names.items():
  hits={s['st_value'] for s in sym.get_symbol_by_name(name) or [] if s['st_shndx']!='SHN_UNDEF'};assert len(hits)==1;symbols[key]=hex(hits.pop())
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
assert sha(B/'program.bin')=='5c5a6c434751b03a0aaa05d8e2478820ca82a3790d7c3b06799f7845d6c5f68b'
assert sha(S/'track03.iso')=='2a6b3200fb0016a89af9b9da275a207eea7a63c7adc7dfedaf07b4a40709fc9a'
old.update(input_track03_sha256=sha(S/'track03.iso'),elf_sha256=sha(B/'re4dc-game.elf'),disc_program_sha256=sha(B/'program.bin'),elf_binary_sha256=sha(B/'program.bin'),symbols=symbols,disc_path=str(S),scope='Exact retained QA control5c5a6c43: QA fix ON, native pause presentation OFF; fresh separate control lineage only.')
p=R/'control-binding.json';assert not p.exists();p.write_text(json.dumps(old,indent=2)+'\n');print(json.dumps({'control_program':old['disc_program_sha256'],'elf':old['elf_sha256'],'track':old['input_track03_sha256']}))