"""Read actual actor programme/ownership receipts; no stage or native queries."""
from pathlib import Path
import json,re
from binding_helpers import native_path,checked_json,pin
from elf_image import verify_raw,ELF
from policy import FINAL_SOURCE,ACTOR_SOURCE,INTEGRATION
KOS_SOURCES={
 'kernel/arch/dreamcast/kernel/cache.s':'8e0973bea3fd977dee62ed2b3753115d9a9f5084dfbece80e56a22c18d669994',
 'kernel/arch/dreamcast/include/dc/cache.h':'c49bcc60b1f69ab4f9b8f2b9b55148a1ff7ccd213b5c0c40034964f1c96a4fd6',
 'utils/ldscripts/shlelf.xc':'fe2d763124ebb8616f96393c7f1d3b1f7c2aa83593e03bc8060faf28364451c2'}

def read(record,inputs):return checked_json(record['path'],record['sha256'],inputs)
def current_programme(stage,source,inputs):
 if source!=FINAL_SOURCE or stage['integration']!=INTEGRATION:raise ValueError('only exact f240 material-route integration')
 p=checked_json(stage['programme_receipt'],stage['programme_receipt_sha256'],inputs)
 if(p.get('status'),p.get('source'),p.get('actor_source'),p.get('integration'))!=('ACTOR23_BOUND_PROGRAMME_PENDING_MAIN_REVIEW',FINAL_SOURCE,ACTOR_SOURCE,INTEGRATION)or p.get('arm')not in('on','memory')or p.get('boot_mode')!=0 or p.get('runtime_admitted')is not False:raise ValueError('exact actor programme/boot0 provenance absent')
 if p.get('image_format')!='unscrambled-gdrom':raise ValueError('unscrambled GDROM image required')
 for key in ('elf','raw','resolved','syms_file','source_seal','compile_receipt'):pin(p[key]['path'],inputs,p[key]['sha256'])
 e=ELF(native_path(p['elf']['path']).read_bytes());evidence=verify_raw(e.data,native_path(p['raw']['path']).read_bytes())
 if p['raw_ELF_evidence']!=evidence:raise ValueError('actual ELF/raw evidence differs')
 symbols={name:e.symbols['_'+name]for name in ('re4dc_logbuf','re4dc_log_head','re4dc_stage','re4dc_actor_visibility23_mode')}
 if symbols!=p['symbols']or symbols['re4dc_actor_visibility23_mode']['size']!=4 or e.sections[symbols['re4dc_actor_visibility23_mode']['section']]['type']!=8:raise ValueError('actual reader/mode0 BSS symbols differ')
 syms=' '.join(hex(symbols[name]['address']-0x8c000000)for name in ('re4dc_logbuf','re4dc_log_head','re4dc_stage'))
 if p['syms']!=syms or native_path(p['syms_file']['path']).read_text().strip()!=syms:raise ValueError('exact actual reader offsets differ')
 source_seal=read(p['source_seal'],inputs);compiled=read(p['compile_receipt'],inputs)
 if source_seal.get('source')!=FINAL_SOURCE or source_seal.get('clean')is not True or source_seal.get('final_source_scope',{}).get('final_literal_clean')is not True or source_seal.get('import_lineage',{}).get('actor_source')!=ACTOR_SOURCE:raise ValueError('current source provenance absent')
 for key,value in dict(source=FINAL_SOURCE,integration=INTEGRATION,elf_sha256=p['elf']['sha256'],raw_sha256=p['raw']['sha256'],resolved_sha256=p['resolved']['sha256'],source_seal_sha256=p['source_seal']['sha256']).items():
  if compiled.get(key)!=value:raise ValueError('compile binding differs: '+key)
 objects=compiled['required_objects'];required={'native_actor_fast.o','native_static.o','native_ui.o','actor_visibility23.o','coarse_ganado.o','shz_bounds23.o','qa_menu.o','tick_log.o','dbgwarp_bridge.o'}
 if p['arm'] != 'on':raise ValueError('material census permits ON only')
 if not required<={Path(x['path']).name for x in objects}:raise ValueError('actual required objects absent')
 for obj in objects:pin(obj['path'],inputs,obj['sha256'])
 resolved=dict(line.split('=',1)for line in native_path(p['resolved']['path']).read_text().splitlines()if'='in line)
 expected=dict(ACTOR_VISIBILITY23_WITNESS='1',ACTOR_VISIBILITY23='1',WORLD_METER='1',CPU_BACKFACE='0',ACTOR_BACKFACE='0',VRAM_ROOM_ARENA='0',PS2_PVS='0',QA_MENU='1',DBG_WARP='1',WARP_AFTER_RESET='1',QA_TEST='22',QA_SRC='ws23',PS2_WORLD_ROOT_POSE='0')
 if p['arm']=='memory':expected.update(PC_SAMPLER='0',KOS_WATCH='1',KOS_SQUEEZE='1',KOS_SQUEEZE_BYTES='0',KOS_SQUEEZE_FRAG='0',HEAP4_WATER='1',HEAP_CENSUS='1')
 if p['required_resolved']!=expected or any(resolved.get(k,'').strip('"')!=v for k,v in expected.items())or'WORLD_SCRATCH'in resolved or p.get('world_scratch_evidence',{}).get('resolved_key_present')is not False:raise ValueError('actual actor controls/source-absent scratch basis differs')
 if len(p['overlays'])!=14 or len({x['package_path']for x in p['overlays']})!=14 or compiled['overlays']!={x['package_path']:x['sha256']for x in p['overlays']}:raise ValueError('all14 linked overlays required')
 for item in p['overlays']:pin(item['path'],inputs,item['sha256'])
 private=read(p['private_inputs'],inputs)
 if private['source']!='bea2d402ba06d41fb7b39946b5a9431a72f5b52a' or p['original_receipts'].get('private_inputs_authority_source')!=private['source'] or p['private_inputs']['sha256']!='3b6d907eda7c1df2fee8455b6696a7a62200da900e7e4f93754f4539dbb8828d' or len(private['sdk_files'])!=210 or len(private['certificate_files'])!=5:raise ValueError('exact private SDK/certificate inventory required')
 for item in [*private['sdk_files'],*private['certificate_files']]:pin(item['path'],inputs,item['sha256'])
 room=p['private_room_metadata']
 if room['sha256']!='9338bd8530b4f45b3c6e891e584f37cc81e93242c4eaec9a0a6bfd7abeb3d22c'or room.get('bytes')!=40080:raise ValueError('exact private room replacement required')
 return p,syms

def ownership_contract(stage,p,source,inputs):
 audit=read(stage['ownership_audit'],inputs)
 if audit.get('status')!='ACTOR23_FINAL_IMAGE_AUDIT_READY'or audit.get('source')!=source or audit.get('elf_sha256')!=p['elf']['sha256']or audit.get('raw_sha256')!=p['raw']['sha256']or audit.get('arm')!=p['arm']or audit.get('elf_type')!='EXEC'or audit.get('runtime_admitted')is not False:raise ValueError('main actual manual final-image audit required')
 for key in ('all14_modules_reviewed','actual_KOS_and_inline_memory_owners_reviewed','actor_world_receipt_and_preskin_paths_reviewed','SDK_private_certificate_inputs_reviewed'):
  if audit.get(key)is not True:raise ValueError('main image clearance absent: '+key)
 if not audit.get('evidence'):raise ValueError('main audit evidence pins absent')
 for item in audit['evidence']:pin(item['path'],inputs,item['sha256'])
 for field in ('kos_receipt','module_roster'):
  record=stage[field]
  from material_identity import require_bound_receipt
  require_bound_receipt(record,p[field],native_path)
  data=read(record,inputs)
  if data['source']!=source or data['elf_sha256']!=p['elf']['sha256']:raise ValueError('final KOS/modules binding differs')
  for item in data['files']:pin(item['path'],inputs,item['sha256'])
  if field=='module_roster':
   linked=data['linked_modules']
   if data['modules']!=p['overlays']or len(linked)!=14 or len({x['path']for x in linked})!=14 or{x['package_path']for x in linked}!={x['package_path']for x in p['overlays']}:raise ValueError('all14 exact derived module ELF pins required')
   for item in linked:pin(item['path'],inputs,item['sha256'])
  else:
   for key in ('archive','cache_disassembly'):pin(data[key]['path'],inputs,data[key]['sha256'])
   if native_path(data['archive']['path']).name!='libkallisti.a'or set(data['sources'])!=set(KOS_SOURCES):raise ValueError('actual KOS archive/known source pins required')
   for name,digest in KOS_SOURCES.items():
    if data['sources'][name]['sha256']!=digest:raise ValueError('KOS source drift')
    pin(data['sources'][name]['path'],inputs,digest)
 return dict(symbols=p['symbols'],boot_mode=0,manual_image_audit=stage['ownership_audit'])
