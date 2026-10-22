from pathlib import Path
import hashlib,json,shutil,sys
sys.path.insert(0,'C:/Game Dev/Emulators/codex-lanes/feedback21-boss-qa/python-deps')
from elftools.elf.elffile import ELFFile
R=Path('C:/Flycast-Evidence/re4-dreamcast/qa21-death-repair-runtime-20261021');R0=Path('C:/Flycast-Evidence/re4-dreamcast/qa21-combined-regression-20261021');B=R/'builds/trace';D=R/'trace-input/gdemu';deps=R0/'dependencies-route-v4';T=Path('//wsl.localhost/Ubuntu-24.04/root/probe/codex-qa21-death-repair/port/dreamcast/tools/d367/qa21_death_repair');BASE=Path('//wsl.localhost/Ubuntu-24.04/root/probe/codex-qa21-combined-regression/port/dreamcast/tools/d367/qa21_combined')
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
stage=json.loads((R/'stage-receipt.json').read_text());build=json.loads((R/'build-receipt.json').read_text());assert stage['all14_staged_overlays_match_build'] and stage['unrelated_exact_file_count']==1728
names={'logbuf':'_re4dc_logbuf','head':'_re4dc_log_head','stage':'_re4dc_stage','end':'_end','pG':'_pG','pPL':'_pPL','EmMgr':'_EmMgr','qa_frames':'__ZN12_GLOBAL__N_1L9qa_framesE','qa_flags':'__ZN12_GLOBAL__N_1L7g_flagsE','Joy':'_Joy','Pad_data':'__ZL8Pad_data','SceSys':'_SceSys','SubScreenWk':'_SubScreenWk'}
with (B/'re4dc-game.elf').open('rb') as f:
 sym=ELFFile(f).get_section_by_name('.symtab');symbols={}
 for key,name in names.items():
  hits={s['st_value'] for s in sym.get_symbol_by_name(name) or [] if s['st_shndx']!='SHN_UNDEF'};assert len(hits)==1;(symbols.update({key:hex(hits.pop())}))
binding=json.loads((R0/'combined-binding.json').read_text());binding.update(input_track03_sha256=stage['staged_track03_sha256'],disc_track03_name='track03.iso',elf_sha256=sha(B/'re4dc-game.elf'),disc_program_sha256=sha(B/'program.bin'),elf_binary_sha256=sha(B/'program.bin'),source_candidate=build['source']['trace_tools_HEAD'],symbols=symbols,disc_path=str(D),scope='Fresh cold isolated death trace lineage only; no prior program state')
assert binding['disc_program_sha256']==stage['program_sha256'];layout=B/'dwarf-layout.json';assert json.loads(layout.read_text())['elf_sha256']==binding['elf_sha256'];assert not (R/'trace-binding.json').exists();(R/'trace-binding.json').write_text(json.dumps(binding,indent=2)+'\n')
tools=R/'tools';tools.mkdir();shutil.copy2(T/'cold-lineage.py',tools/'cold-lineage.py');shutil.copy2(T/'evidence_footprint.py',tools/'evidence_footprint.py');inputs={'cold':'r103-cold-keys.txt','empty':None,'BB':'new-room-no-qa-keys.txt','continue':'continue-keys.txt'};keys={}
for key,name in inputs.items():
 p=tools/(name or 'empty-keys.txt')
 if name:shutil.copy2((Path('C:/Game Dev/Emulators/codex-lanes/qa21-combined-regression') if key=='continue' else BASE)/name,p)
 else:p.write_bytes(b'')
 keys[key]={'path':str(p),'sha256':sha(p)}
controller=tools/'normal-r103-door-v2.py';shutil.copy2(BASE/controller.name,controller)
m={'scope':'trace-runtime-qualification','evidence_root':str(R),'dependencies_root':str(deps),'binding':str(R/'trace-binding.json'),'elf':str(B/'re4dc-game.elf'),'layout':str(layout),'disc':str(D),'build_receipt':str(R/'build-receipt.json'),'stage_receipt':str(R/'stage-receipt.json'),'keys':keys,'door_controller_sha256':sha(controller),'dependencies':{p.name:sha(p) for p in deps.glob('*.py')},'launcher_sha256':sha(tools/'cold-lineage.py'),'evidence_footprint_sha256':sha(tools/'evidence_footprint.py')};(R/'runtime-manifest.json').write_text(json.dumps(m,indent=2)+'\n');print(json.dumps({'program':binding['disc_program_sha256'],'ELF':binding['elf_sha256'],'image':binding['input_track03_sha256'],'symbols':symbols}))
