"""Bind actual actor ON/memory inputs; read-only sources, no stage/profile/guest."""
from pathlib import Path
import argparse,concurrent.futures,gzip,hashlib,json,re,struct,subprocess
from binding_helpers import native_path
from elf_image import ELF,verify_raw,fnv
from policy import FINAL_SOURCE,ACTOR_SOURCE,INTEGRATION,EVIDENCE_ROOT
from coverage_proof import private_readback,HEADER_SHA
from proof_objects import verify_objects
from source_proof import live_source,validate
P=Path(__file__).resolve().parent

def digest(data):return hashlib.sha256(data).hexdigest()

def validate_config(config,arm):
 if config.get('source')!=FINAL_SOURCE or config.get('root')!=EVIDENCE_ROOT or set(config.get('arms',{}))!={'on'} or arm!='on':raise ValueError('exact coverage successor ON scope required')

def validate_certificate(private,compiled,check,jcheck):
 expected={'actor_visibility23_r119_certificate.h':HEADER_SHA,'room.r4rc':'9338bd8530b4f45b3c6e891e584f37cc81e93242c4eaec9a0a6bfd7abeb3d22c','OCCL.bin':'ea2ceae5920f388efab7aa00510c161414a077bf228536a40b913d43e1997cf8','candidate.json':'2b1e3ea8e1d085156432b67ec4ad11017c8bfddd777ed89bea7e6efc75fe6658','geometry-proof.json':'8b541c6596d59f4d0a62269c8c80477e35cf64e7f4910b72f02660f1d2a93c37'}
 rows=private['certificate_files'];names={Path(x['path']).name:x for x in rows}
 if len(rows)!=5 or len(names)!=5 or {k:v['sha256']for k,v in names.items()}!=expected:raise ValueError('exact five reviewed successor certificate files required')
 deps=jcheck(compiled['dependency_inputs']);headers=[x for x in deps if Path(x['path']).name=='actor_visibility23_r119_certificate.h']
 if len(headers)!=1 or headers[0]['sha256']!=HEADER_SHA or headers[0]['bytes']!=416:raise ValueError('actual compile dependency must bind new 416-byte header')
 pp=jcheck(compiled['preprocessing']);units=[x for x in pp if Path(x['object']).name=='native_static.o']
 if len(units)!=1:raise ValueError('actual native_static contributing-world target preprocessing required')
 text=gzip.decompress(check(units[0]['artifact'])).decode()
 if not re.search(r'full\s*\[\s*\]\s*=\s*\{\s*0xd80U\s*,\s*0xd80U\s*\}',text):raise ValueError('actual target preprocessed full masks must be d80/d80')
 return True

def normalize(arm,write=False):
 config=json.loads((P/'NORMALIZATION-INPUTS.json').read_text());validate_config(config,arm);c=config['arms'][arm];root=config['root'];inputs={}
 def check(record):
  path=native_path(record['path']);data=path.read_bytes();value=digest(data)
  if value!=record['sha256']or('bytes'in record and len(data)!=record['bytes']):raise ValueError('actual input changed: '+record['path'])
  inputs[str(path)]=value;return data
 def jcheck(record):return json.loads(check(record))
 def original(relative,pin):
  record=dict(path=root+'/'+relative,sha256=pin);return record,jcheck(record)
 link_record,link=original('on2/LINK-RECEIPT.json',c['link_sha256']);folder='on2/source-compile-r2'
 sr,source=original(folder+'/source-seal.json',c['source_sha256']);cr,compiled=original(folder+'/compile.json',c['compile_sha256'])
 if link['source_head']!=FINAL_SOURCE or link['base']!=INTEGRATION or link['arm']!=arm or link['runtime_admitted']is not False or source['source']!=FINAL_SOURCE or compiled['source']!=FINAL_SOURCE:raise ValueError('exact actual actor programme source/arm required')
 if source.get('import_lineage',{}).get('actor_bounds_source')!='7662a04038231e1d8718be077f3d0cb56aa7c977':raise ValueError('exact actor bounds provenance absent')
 if source.get('import_lineage',{}).get('actor_source')!=ACTOR_SOURCE or source['import_lineage'].get('WORLD_METER')!=['14afb24fe','272e2892f']or source['import_lineage'].get('integration_instances')!=['9c6c57005','73a13949b']:raise ValueError('exact actor/meter provenance absent')
 for key in ('elf_sha256','raw_sha256','resolved_sha256'):
  ref={'elf_sha256':'main','raw_sha256':'raw','resolved_sha256':'resolved'}[key]
  if compiled[key]!=link[ref]['sha256']:raise ValueError('compile/link binding differs: '+key)
 if compiled.get('image_format')!='unscrambled-gdrom' or compiled.get('source_seal_sha256')!=sr['sha256']:raise ValueError('actual compile source/raw encoding differs')
 required={'native_actor_fast.o','native_static.o','native_ui.o','actor_visibility23.o','coarse_ganado.o','shz_bounds23.o','qa_menu.o','tick_log.o','dbgwarp_bridge.o'}
 if arm=='memory':required|={'os.o','main_mem.o','native_movie.o'}
 if not required<={Path(x['path']).name for x in compiled['required_objects']}:raise ValueError('actual actor/SDK/fixture/diagnostic objects absent')
 records=[link['main'],link['raw'],link['scrambled'],link['resolved'],link['objects_manifest'],link['source_manifest'],link['modules_roster'],*link['overlays'],*link['kos'],compiled['dependency_inputs'],compiled['commands'],compiled['preprocessing'],compiled['build_log'],compiled['link_command'],compiled['relocation_validation'],compiled['module_derivation_script'],*compiled['required_objects']]
 for record in records:check(record)
 final=jcheck(config['final_clean']);scope=validate(source,check(source['clean_remote_proof']).decode(),final,None,live_source(),FINAL_SOURCE,check)
 counts={}
 for name,record in [('sources',link['source_manifest']),('dependencies',compiled['dependency_inputs'])]:
  rows=jcheck(record)
  with concurrent.futures.ThreadPoolExecutor(max_workers=4)as pool:list(pool.map(check,rows))
  counts[name]=len(rows)
 mapping=jcheck(c['object_mapping']);counts['objects']=verify_objects(jcheck(link['objects_manifest']),mapping,link['objects_manifest'],FINAL_SOURCE,arm,c['link_sha256'],check)
 preprocessing=jcheck(compiled['preprocessing'])
 for row in preprocessing:
  data=gzip.decompress(check(row['artifact']))
  if len(data)!=row['preprocessed_bytes']or digest(data)!=row['preprocessed_sha256']:raise ValueError('actual preprocessed input differs')
 private=jcheck(config['private_inputs']);allocation=jcheck(config['allocation_inputs'])
 if source['private_inputs_receipt']['sha256']!=config['allocation_inputs']['sha256'] or source['private_inputs_readback']['sha256']!=config['private_inputs']['sha256']:raise ValueError('source/private allocation joins differ')
 preparation=jcheck(private['preparation']);prior=jcheck(private['old_input_proof'])
 if preparation['source']!='bea2d402ba06d41fb7b39946b5a9431a72f5b52a' or preparation['unchanged_room_and_OCCL']is not True or preparation['prior_input_readback']!=private['old_input_proof'] or private['successor_seal_sha256']!='88074289fd127d294d12555519fc0078db0fe282fd212e3ae06c7ff6b4c8f82c' or prior['sdk_files']!=private['sdk_files']:raise ValueError('private preparation/unchanged SDK lineage differs')
 for rec in [preparation['successor_seal'],preparation['review'],*preparation['inputs']]:check(rec)
 if private['source']!='bea2d402ba06d41fb7b39946b5a9431a72f5b52a' or allocation['source']!='bea2d402ba06d41fb7b39946b5a9431a72f5b52a' or len(private['sdk_files'])!=210 or len(private['certificate_files'])!=5 or private['copied_or_modified']is not False:raise ValueError('exact private SDK/certificate provenance absent')
 for record in [*allocation['inputs'],*private['sdk_files'],*private['certificate_files']]:check(record)
 coverage=private_readback()
 for record in coverage['records']:check(record)
 validate_certificate(private,compiled,check,jcheck)

 resolved=dict(line.split('=',1)for line in check(link['resolved']).decode().splitlines()if'='in line)
 expected=dict(ACTOR_VISIBILITY23_WITNESS='1',ACTOR_VISIBILITY23='1',WORLD_METER='1',CPU_BACKFACE='0',ACTOR_BACKFACE='0',VRAM_ROOM_ARENA='0',PS2_PVS='0',QA_MENU='1',DBG_WARP='1',WARP_AFTER_RESET='1',QA_TEST='22',QA_SRC='ws23',PS2_WORLD_ROOT_POSE='0')
 if arm=='memory':expected.update(PC_SAMPLER='0',KOS_WATCH='1',KOS_SQUEEZE='1',KOS_SQUEEZE_BYTES='0',KOS_SQUEEZE_FRAG='0',HEAP4_WATER='1',HEAP_CENSUS='1')
 if any(resolved.get(k,'').strip('"')!=v for k,v in expected.items()):raise ValueError('actual actor/QA/memory controls differ')
 elf=ELF(check(link['main']));source_hits=[x['path']for x in jcheck(link['source_manifest'])if Path(x['path']).name in ('world_scratch.cpp','world_scratch.h')];symbol_hits=[name for name in elf.symbols if 're4dc_world_scratch' in name];pp_hits=[]
 for row in preprocessing:
  text=gzip.decompress(check(row['artifact'])).decode(errors='replace')
  if re.search(r'^#define RE4DC_WORLD_SCRATCH 1\b|re4dc_world_scratch',text,re.M):pp_hits.append(row['object'])
 if 'WORLD_SCRATCH'in resolved or source_hits or symbol_hits or pp_hits:raise ValueError('exact actor source-absent scratch control differs')
 scratch_evidence=dict(basis='source-absent/off; actual resolved has no WORLD_SCRATCH assignment',resolved_key_present=False,matching_source_files=source_hits,matching_ELF_symbols=symbol_hits,matching_enabled_touched_preprocessing=pp_hits)
 raw_evidence=verify_raw(elf.data,check(link['raw']));symbols={name:elf.symbols['_'+name]for name in ('re4dc_logbuf','re4dc_log_head','re4dc_stage','re4dc_actor_visibility23_mode')};mode=symbols['re4dc_actor_visibility23_mode']
 if mode['size']!=4 or elf.sections[mode['section']]['type']!=8:raise ValueError('actual zero-initialized actor mode BSS absent')
 syms=' '.join(hex(symbols[name]['address']-0x8c000000)for name in ('re4dc_logbuf','re4dc_log_head','re4dc_stage'))
 roster=jcheck(link['modules_roster']);overlays={Path(x['path']).name:x for x in link['overlays']};module_rows=[];linked=[];validation=check(compiled['relocation_validation']).decode()
 if len(roster)!=14 or len(overlays)!=14:raise ValueError('exact14 module/overlay pairs required')
 for row in roster:
  record=dict(path=root+'/on2/modules/'+row['elf'],sha256=row['elf_sha256']);module=ELF(check(record));section,image=module.section(row['section']);overlay=overlays[row['overlay']];data=check(overlay);header=struct.unpack_from('<16I',data)
  if(header[0],header[1],header[2],header[4])!=(0x4f344552,1,len(image),section['address'])or section['address']!=row['vma']or len(image)!=row['bytes']or digest(image)!=row['image_sha256']or data[64:64+len(image)]!=image or len(data)!=64+len(image)+header[3]*4:raise ValueError('actual final-A derived module/overlay bytes differ')
  reloc=data[64+len(image):];offsets=struct.unpack('<'+str(header[3])+'I',reloc)
  if fnv(image)!=header[12]or fnv(reloc)!=header[13]or list(offsets)!=sorted(set(offsets))or any(x%4 or x>=len(image)for x in offsets):raise ValueError('actual overlay relocation/FNV invalid')
  exact='gen_overlay: %s %u bytes, %u relocations, image outside it identical at both addresses -> %s'%(row['section'],len(image),header[3],overlay['path'])
  if validation.splitlines().count(exact)!=1:raise ValueError('actual two-address validation missing/duplicate')
  package='dc/'+row['overlay'];linked.append(dict(record,package_path=package));module_rows.append(dict(package_path=package,section=row['section'],image_sha256=digest(image),overlay_sha256=overlay['sha256'],relocations=header[3],actual_two_address_validation=exact))
 if len({x['package_path']for x in linked})!=14 or len({x['path']for x in linked})!=14:raise ValueError('duplicate package/module ELF')
 command=['/opt/toolchains/dc/sh-elf/bin/sh-elf-objdump','-d','--disassemble=_cache_write_ccr',link['main']['path']];disasm=subprocess.check_output(command)
 if b'<_cache_write_ccr>:'not in disasm:raise ValueError('actual linked KOS CCR routine absent')
 out=P/'bound'/arm;artifacts={}
 def save(name,data):
  raw=data if isinstance(data,bytes)else(data if isinstance(data,str)else json.dumps(data,indent=2,sort_keys=True)+'\n').encode();artifacts[name]=raw;return dict(path=str(out/name),sha256=digest(raw),bytes=len(raw))
 provenance=dict(link_receipt=link_record,source_seal=sr,compile=cr,object_mapping=c['object_mapping'],private_inputs_authority_source='bea2d402ba06d41fb7b39946b5a9431a72f5b52a',private_inputs=config['private_inputs'],allocation_inputs=config['allocation_inputs'],final_clean=config['final_clean'],coverage_source_review=dict(source_private_seal_sha256=coverage['records'][0]['sha256'],independent_review_sha256=coverage['records'][1]['sha256'],private_header_sha256=HEADER_SHA,full_masks=[0xd80,0xd80],readback_modified_inputs=False,preparation='copied sealed certificate bytes; readback itself made no copies'))
 source_out=save('source-seal.json',dict(source,normalization_of=sr,final_source_scope=scope,final_clean=config['final_clean'],runtime_admitted=False))
 compile_out=save('compile.json',dict(compiled,source_seal_sha256=source_out['sha256'],normalization_of=cr,object_proof_classification=counts['objects'],original_source_seal_sha256=sr['sha256'],raw_ELF_evidence=raw_evidence,runtime_admitted=False))
 syms_out=save('syms.txt',syms+'\n');disasm_out=save('cache-write-ccr-final-ELF.txt',disasm);overlays_list=[dict(x,package_path='dc/'+Path(x['path']).name)for x in link['overlays']]
 kos=save('kos.json',dict(source=FINAL_SOURCE,elf_sha256=link['main']['sha256'],archive=link['kos'][0],cache_disassembly=disasm_out,files=[*link['kos'],disasm_out],sources={x['path'].split('/kos-re4dc-d367/')[1]:x for x in link['kos'][1:]},original_link_receipt=link_record,main_review='PENDING'))
 modules=save('modules.json',dict(source=FINAL_SOURCE,elf_sha256=link['main']['sha256'],modules=overlays_list,linked_modules=linked,module_bindings=module_rows,files=[link['modules_roster'],compiled['relocation_validation'],compiled['module_derivation_script']],main_review='PENDING'))
 programme=save('programme.json',dict(status='ACTOR23_BOUND_PROGRAMME_PENDING_MAIN_REVIEW',source=FINAL_SOURCE,actor_source=ACTOR_SOURCE,integration=INTEGRATION,arm=arm,elf=link['main'],raw=link['raw'],scrambled=link['scrambled'],image_format='unscrambled-gdrom',raw_ELF_evidence=raw_evidence,resolved=link['resolved'],required_resolved=expected,syms_file=syms_out,syms=syms,symbols=symbols,boot_mode=0,source_seal=source_out,compile_receipt=compile_out,overlays=overlays_list,kos_receipt=kos,module_roster=modules,private_inputs=config['private_inputs'],private_room_metadata=next(x for x in private['certificate_files']if x['path'].endswith('/room.r4rc')),world_package_baseline=jcheck(next(x for x in private['certificate_files']if x['path'].endswith('/candidate.json')))['input_binding'],world_scratch_evidence=scratch_evidence,original_receipts=provenance,main_manual_image_review='PENDING',actual_camera_ticks='PENDING',runtime_admitted=False))
 save('NORMALIZATION-READBACK.json',dict(source=FINAL_SOURCE,arm=arm,programme=programme,verified_actual_manifest_entries=counts,preprocessed_units=len(preprocessing),private_SDK_files=210,private_certificate_files=5,raw_ELF_evidence=raw_evidence,actual_symbols=symbols,source_scope=scope,original_receipts=provenance,main_review='PENDING',stage=False,profile=False,guest=False));save('PINNED-INPUTS.json',inputs)
 if sum(map(len,artifacts.values()))>3*1024**2:raise ValueError('per-arm normalized metadata3MiB cap')
 if write:
  out.mkdir(parents=True,exist_ok=True)
  for name,data in artifacts.items():
   path=out/name
   if path.exists()and path.read_bytes()!=data:raise ValueError('preserve existing normalization: '+name)
   if not path.exists():path.write_bytes(data)
 return dict(written=write,arm=arm,programme_sha256=programme['sha256'],metadata_bytes=sum(map(len,artifacts.values())),verified_actual_manifest_entries={k:v for k,v in counts.items()if k!='objects'},objects={k:v for k,v in counts['objects'].items()if k!='historical_records'},main_review='PENDING',stage=False,profile=False,guest=False)

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--arm',choices=['on'],required=True);parser.add_argument('--write',action='store_true');a=parser.parse_args();print(json.dumps(normalize(a.arm,a.write)))
