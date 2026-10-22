from pathlib import Path
import copy,hashlib,json,subprocess,re,shutil
T=Path('/root/probe/codex-texture-rect21');R=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/texture-rect21-20261021');E=R/'canonical-programme-plan-01'
SOURCE='0425534d848973c1dae3ab960d0006ac9afcf363';OLD='845abb1f4ad3a2721d17f64899b6dc59d4bce66c'
OLDROOT='/root/probe/texture-rect21-world26-link-20261021-01';NEWROOT='/root/probe/texture-rect21-canonical36-link-20261021-01'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def pin(p):
 p=Path(p);return dict(path=str(p),bytes=p.stat().st_size,sha256=sha(p))
def frozen(p):
 p=Path(p);rel=str(p.relative_to(T));b=subprocess.check_output(['git','-C',str(T),'show',SOURCE+':'+rel]);assert b==p.read_bytes(),str(p);return pin(p)
assert not Path(NEWROOT).exists(),'plan only must not reuse old output root'
assert not subprocess.check_output(['git','-C',str(T),'status','--porcelain'],text=True).strip()
head=subprocess.check_output(['git','-C',str(T),'rev-parse','HEAD'],text=True).strip();subprocess.run(['git','-C',str(T),'merge-base','--is-ancestor',SOURCE,head],check=True)
P=R/'combined-programme-plan-01/plan02.json';assert sha(P)=='7b3effc046f9780c1b9d16c85761cf432ab570f238ea190d4d82a7091208e7fd'
p=json.loads(P.read_text());previous=json.loads((R/'world26-programme-01/qualification-final.json').read_text())
closure=json.loads((R/'world26-programme-01/actual-complete-dependency-closure.json').read_text());assert len(closure)==948
allowed={'scoped_representations.inc','provenance_certificates.inc','world_rect_provenance.h'};changes=[];fresh=[]
for row in closure:
 now=pin(row['path']);fresh.append(now)
 if now['sha256']!=row['sha256']:
  assert Path(row['path']).name in allowed,row['path'];changes.append(dict(before=row,after=now))
assert {Path(x['after']['path']).name for x in changes}==allowed
for row in p['unchanged_original_object_pins']+p['unchanged_library_pins']+p['link_support_pins']:
 assert pin(row['path'])==row,row['path']
for row in p['frozen_overlay_derived_objects']:
 assert pin(row['derived']['path'])==row['derived'];assert pin(row['original']['path'])==row['original']
for unit in ('native_static','native_ui'):
 row=p['replacement_compile_plans'][unit]['off_baseline'];assert pin(row['path'])==row
 # Runtime cpp unchanged; exact original OFF controls remain relevant.
 cpp=T/'port/dreamcast/game/platform'/ (unit+'.cpp');frozen(cpp)
 assert subprocess.check_output(['git','-C',str(T),'show',OLD+':'+str(cpp.relative_to(T))])==cpp.read_bytes()
for name in ('game30.mk','effects30.mk'):
 path=T/'port/dreamcast/game'/name
 if path.exists():assert subprocess.check_output(['git','-C',str(T),'show',OLD+':'+str(path.relative_to(T))])==path.read_bytes()
headers=[T/'port/dreamcast/tools/d367/texture_rect21'/x for x in('scoped_representations.inc','world_rect_bind.h','world_rect_provenance.h','provenance_certificates.inc','integration_canonical_world36.json')]
headerpins=[frozen(x)for x in headers]
canon=json.loads(headers[-1].read_text());assert canon['representations']==36 and canon['certificates']==3 and canon['host_checks']==573 and canon['runtime_CRC_unchanged']
for name,digest in canon['after'].items():assert sha(headers[0].parent/name)==digest
worlds={}
for path,digest in canon['worlds'].items():
 row=pin(path);assert row['sha256']==digest;worlds[Path(path).parent.name]=row
assert set(worlds)=={'r100','r101','r103'}
# Verify retained complete prior namespace identity list, including old programme.
retained_manifest=R/'world26-programme-01/retained-WSL-file-identities.json';retained=json.loads(retained_manifest.read_text())
for row in retained:
 path=Path(OLDROOT)/row['path'];assert pin(path)['sha256']==row['sha256'] and path.stat().st_size==row['bytes']
prior_final=[pin(x)for x in sorted((Path(OLDROOT)/'out').iterdir())if x.is_file()]
assert sha(Path(OLDROOT)/'out/re4dc-game.elf')==previous['ELF_sha256'] and sha(Path(OLDROOT)/'out/program.bin')==previous['programme_sha256']
manifest=Path('/root/re4data/private/texture-canonical1004-plan-v1-20261021/CANONICAL1004-MANIFEST.json')
assert sha(manifest)=='acf4abe0a6d449f31aaefa8ab7046cd14265b625edf90a03b429f7cd040ba7c6'
link_objects=[x.replace(OLDROOT,NEWROOT)for x in p['future_direct_link_argv']if x.endswith('.o')]
direct_names={x['path']for x in p['unchanged_original_object_pins']}
derived_names={x['derived']['path']for x in p['frozen_overlay_derived_objects']}
actual_direct=[pin(x)for x in link_objects if x in direct_names]
actual_derived=[pin(x)for x in link_objects if x in derived_names]
replacements=[x for x in link_objects if x.startswith(NEWROOT+'/objects/')]
other=[pin(x)for x in link_objects if x not in direct_names|derived_names and x not in replacements]
assert (len(link_objects),len(actual_direct),len(actual_derived),len(replacements),len(other))==(447,402,42,2,1)
assert other[0]['path'].endswith('/obj/missing.o')
# No rebuilt library or recipes: exact old recorded flags/headers/objects.
new=copy.deepcopy(p);new.update(schema=3,source=SOURCE,owned_checkout_commit=head,source_branch='codex/texture-rect21',status='PLAN_ONLY_NO_COMPILER_LINK_IMAGE_OR_GUEST',runtime_scope='Canonical WORLD_RECT21 source36/three certificates. Same algorithm/six policy anchors; no runtime CRC weakening, cache/Ganado/actor/atlas or recipe changes.',
 source_lineage=dict(runtime_source=SOURCE,owned_checkout=head,extra_checkout_files=[x for x in subprocess.check_output(['git','-C',str(T),'diff','--name-only',SOURCE,head],text=True).splitlines()],compiler_cpp_make_unchanged_since=OLD),
 freeze_policy='New hashes/ABI only from actual admitted compiler/link outputs. f42 and old C receipts STATIC/HOLD, not target adoption.',
 new_runtime_header_pins=headerpins,complete_actual_dependency_pins=fresh,expected_changed_dependencies=changes,
 owned_future_root=NEWROOT,future_direct_link_argv=[x.replace(OLDROOT,NEWROOT)for x in p['future_direct_link_argv']],
 canonical_world36=canon,canonical_world_file_pins=worlds,previous_static_hold_programme=dict(ELF_sha256=previous['ELF_sha256'],programme_sha256=previous['programme_sha256'],namespace=OLDROOT,retained_manifest=pin(retained_manifest),final_files=prior_final),
 old_default_off_controls={k:v for k,v in previous['objects'].items()if not k.endswith('-on')})
new.pop('world26_integration',None)
new['actual_link_object_census']=dict(total=447,retained_original_full=actual_direct,reused_derived_helpers=actual_derived,owned_replacements=replacements,retained_support=other,preserved_but_not_all_directly_linked=dict(original_pins=446,derived_pins=43))
new['environment']['TMPDIR']=NEWROOT+'/temp'
new['root36_object_gates']=new.pop('root26_object_gates')
new['root36_object_gates']+=[
 'Each TU default then explicit0 must equal its original QA stripped-object control (allocated sections/symbols/relocations included) before ANY ON link; default/0 preprocessing hashes exact each other. Preserve both control recipes/macros and prior f42 controls.',
 'Exact compiler frontend macro proof WORLD_RECT21=0/1 plus MESH_DIRECT and all6 inherited Package mip/PAL flags. Do not infer macros from argv alone; reject overriding forced headers.',
 'Recheck actual .d closure against948 pinned dependencies; only3 allowed existing headers changed fromf42 and no unknown dependencies. Record actual source checkout and042 runtime source equivalence.',
 'native_static area_flags20B and2 normalized relocations must equal original before rename and after fresh derived rename; no old object blind replacement.'
]
new['assets']=dict(status='CANONICAL_VIRTUAL_ONLY_NOT_A_PROGRAMME_QUALIFICATION',primary='M0 original6501 18fcee11491f2c1f212863d6d6b572b3997f691b2e990217e1c2518f134021ef vs canonical1004 candidate; full texture pipeline, not isolated mip causality',canonical_candidate_manifest_path=str(manifest),canonical_candidate_manifest_pin=pin(manifest),canonical_candidate_manifest_sha256='acf4abe0a6d449f31aaefa8ab7046cd14265b625edf90a03b429f7cd040ba7c6',canonical_candidate_expected_pack_sha256='89ef27a767fcee529c3ac6ca07fef5a8f9a3e2515f38eda63b61c8929fb0be62',pack_bytes=156248064,pack_members=6537,worlds=worlds,metadata='Old original R4ID/R4TC/PCL/OCCL/R4SG retained byteexact. New programme shared by both arms; actual physical checksums/profile/movie distinct from source anchors.',old_965_994='Historical held diagnostic fixtures, no substitution into canonical image',no_asset_or_image_write=True)
new['link_steps']=[
 'After parent allocation only, create one fresh owned namespace/link-context/temp; preserve every old namespace. Verify all pins and fresh capacity before output.',
 'Sequential six small TU objects through shared buildslot,55s bound each, exact recorded argv/forced headers, -MF/-o redirected, stack reports; OFF identity gates precede ON.',
 'Freshly derive native_static-linked.o only after exact area_flags body+normalized-relocation proof. Reuse402 directly linked original full objects,42 derived helper copies,one pinned missing.o and30 libraries and old linker scripts immutable; native_ui ON and derived native_static are only replacement link objects.',
 'ONE new base link<=180s plus14 sequential shifted link/seals; same exact overlay addresses/moves/slots. Each shifted ELF and gen_overlay temporary in owned monitored TMPDIR, preserve failure identities and bounded logs; remove only known owned rebuild intermediates.',
 'Patch genuinely new image IDs, independently validate14 header/payload/reloc-word FNV/targets/within-original-slot/newELF binding. Remove overlay sections from final ELF only after all reseals.',
 'Reconstruct raw via PT_LOAD and compare exact program bytes. Record _end/static RAM/tail/slack and actual static stacks. Preserve previous845/f42 entire immutable evidence; final program+ELF+14 exact Windows mirrors.',
 'Fresh newELF policy23vars/43fields and PhaseLatch/scene/table binding occurs only after actual qualification; no old e08/f42 ABI/state transfer. No staging or guest in this unit.'
]
new['resources']=dict(status='PARENT_REVIEW_REQUIRED_NOT_ALLOCATED',request_total_peak_and_final_new_bytes=128*1024**2,
 prior_actual_closed_bytes=77039087,forecast_components=dict(six_objects_and_small_diagnostics=6*1024**2,WSL_final_ELF_programme_overlays=34*1024**2,Windows_exact_final_mirror_and_ON_objects=35*1024**2,one_shifted_ELF=29*1024**2,gen_overlay_tmp_inside_monitored_TMPDIR=4*1024**2,plan_source_logs_receipts_and_reserve=20*1024**2),
 forecast_bytes=128*1024**2,monitor='All new programme B/E roots, owned TMPDIR and new plan/tools included; no full tree/object mirror and no full debug relocation dumps. Preserve failures within same hard cap.',
 start_floor='18GiB+640MiB+336MiB canonical pack reservation+64MiB next source+all other currently outstanding peer reservations, refreshed by parent before allocation',runtime_floor='18GiB+64MiB',
 shared_build_slot=True,unit_timeout_seconds=55,link_timeout_seconds=180,logs='stream compressed and<=8MiB cumulative, charged to total128MiB',
 plan_metadata='Read-only plan/tools/mirrors under remaining4MiB oracle/source envelope; actual total checked before mirror. This plan creates no future output tree/objects/programme.')
new['next_acceptance']='Main review/allocation. Actual strict Package/CRC canonical pack proof, fresh image and cold functional/equivalence/timing remain separate.'
# Arithmetic is exact; no quota lowering.
assert sum(new['resources']['forecast_components'].values())==new['resources']['forecast_bytes']
for f,x in [('plan02.json',new),('current948-dependency-pins.json',fresh),('three-changed-dependencies.json',changes)]:
 if (E/f).exists():assert json.loads((E/f).read_text())==x
 else:
  with(E/f).open('x')as out:json.dump(x,out,indent=2);out.write('\n')
print(json.dumps(dict(source=SOURCE,checkout=head,old_objects=446,directly_reused_full=402,actually_reused_derived=42,retained_support=1,derived_helpers=43,libraries=30,deps=len(fresh),changed_dependencies=len(changes),new_header_pins=len(headerpins),old_namespace_files=len(retained),plan_sha256=sha(E/'plan02.json'),plan_bytes=(E/'plan02.json').stat().st_size,forecast_bytes=128*1024**2)))