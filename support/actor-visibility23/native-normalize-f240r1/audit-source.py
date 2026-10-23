from pathlib import Path
import json,hashlib,sys,gzip,struct,subprocess
L=Path('/mnt/c/Game Dev/Emulators/codex-lanes/actor-visibility23');P=L/'native-normalize-f240r1';O=Path('/root/probe/lanes/actor-visibility23-eligibility-witness-integration/on2');T=Path('/root/probe/codex-actor-visibility23-eligibility-witness-integration');A=L/'main-audit-f240-on2'
sys.path.insert(0,str(P));from elf_image import ELF
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rec(p):return dict(path=str(p),bytes=Path(p).stat().st_size,sha256=sha(p))
pp=json.loads((O/'source-compile-r2/PREPROCESS.json').read_text());controls=[]
witness_units={'native_actor_fast.o','native_static.o','actor_visibility23.o','coarse_ganado.o'}
for row in pp:
 macros=row['actual_control_macros'];unit=Path(row['object']).name
 assert macros['RE4DC_CPU_BACKFACE'] is None and macros['RE4DC_WORLD_SCRATCH']is None
 if unit in witness_units:assert macros['RE4DC_ACTOR_VISIBILITY23_WITNESS']=='1'
 text=gzip.decompress(Path(row['artifact']['path']).read_bytes()).decode(errors='replace')
 if unit=='native_actor_fast.o':
  assert 'source_cull!=1&&source_cull!=2' in text and 're4dc_actor_visibility23_source_cull(p.model,p.info,epoch)' in text
  assert 're4dc_actor_visibility23_witness_skip(0,level,mi,nv,nt)' in text and 're4dc_actor_visibility23_witness_skip(1,level,mi,nv,nt)'in text
 controls.append(dict(unit=unit,macros=macros,preprocessing=row['artifact']))
source_names=['platform/native_actor_fast.cpp','platform/actor_visibility23.cc','platform/native_static.cpp','coarse_ganado.cpp','platform/include/actor_visibility23_material.h','platform/include/actor_visibility23_witness.h']
source_records=[rec(T/'port/dreamcast/game'/name)for name in source_names]
sn=(T/'port/dreamcast/game/platform/native_actor_fast.cpp').read_text();assert sn.index('re4dc_actor_visibility23_witness_skip(0')<sn.index('chunk_positions(e, r, nv, k, s16_uv, all, any);',sn.index('re4dc_actor_visibility23_witness_skip(0'))
assert sn.index('re4dc_actor_visibility23_witness_skip(1')<sn.index('chunk_positions(e, r, nv, k, s16_uv, all, any);',sn.index('re4dc_actor_visibility23_witness_skip(1'))
# The only overlay candidate literal overlaps two unchanged data words at 2-byte alignment.
p=O/'modules/st1_3.elf';oldp=Path('/root/probe/lanes/actor-visibility23-coverage-integration/on/modules/st1_3.elf');elf=ELF(p.read_bytes());old=ELF(oldp.read_bytes());s,b=elf.section('.ovl_st1_3');_,prior=old.section('.ovl_st1_3');off=0xae28;assert b[off:off+8]==prior[off:off+8]==bytes.fromhex('cdcccc3f007c58c7')
owner=elf.symbols['__ZL13r11c_operatorv'];assert owner['address']<=s['address']+off and s['address']+off+8<=owner['address']+owner['size']
scan=json.loads((A/'OWNER-SCAN.json').read_text());assert scan['main_literal_role_rows_identical']is True
assert sum(len(r['literals'])for r in scan['images'][1:])==1
record=dict(status='SOURCE_PREPROCESS_AND_LITERAL_ROLE_READBACK_PASS_MANUAL_REVIEW_OPEN',source='f2405bb06ebaff6e2a7681479d5308ec5d3b988a',source_files=source_records,preprocessing_controls=controls,
 material_route='Backend cull0 requires current owned2b source one-sided certificate; all existing material/identity/numeric guards retained.',pre_position_skip_branches=[0,1],witness1_units=sorted(witness_units),boot_mode=0,
 main_CCR_OCRAM_literal_roles='Exact15 section/value/alignment/function/neighbor-word rows match retained historical OFF; source addresses relocated.',
 module_literal=dict(elf=rec(p),historical_elf=rec(oldp),section='.ovl_st1_3',offset=hex(off),bytes_hex=b[off:off+8].hex(),overlapping_value='0x7c003fcc',overlap_alignment=2,symbol='r11c_operator',role='unaligned overlap between unchanged 0x3fcccccd and 0xc7587c00 data words, not a separate address literal'),
 no_new_allocated_OCRAM_sections=True,cache_helper_bytes_unchanged=True,fresh_off_identity=False,main_manual_review='PENDING',runtime_admitted=False,stage=False,guest=False)
(A/'SOURCE-AND-LITERAL-CLASSIFICATION.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(rec(A/'SOURCE-AND-LITERAL-CLASSIFICATION.json')))
