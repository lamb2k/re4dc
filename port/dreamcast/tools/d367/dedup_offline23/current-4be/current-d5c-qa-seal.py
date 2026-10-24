"""Seal actual current4be private normal QA pair for root review; no publication."""
from pathlib import Path
import hashlib,json,shutil
E=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/dedup-offline23-20261023/current-4be08e01')
T=Path('/root/work/lanes/dedup-offline23-qa-4be08e01/port/dreamcast/tools/d367')
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
m=json.loads((E/'qa-media-r1/pair-media-identity.json').read_text());plan=json.loads((E/'private-qa-plan-prelink.json').read_text());report={}
for arm,mode in [('off',0),('on',3)]:
 x=m['arms'][arm];d=Path(x['path']);gates={}
 k=dict(v.split('=',1) for v in (Path(x['programme']['path'])/'resolved-knobs.txt').read_text().splitlines() if '=' in v)
 assert k['SCENERY_EMIT_PREFETCH']=='0' and k['SCENERY_SELECT_LEAN2']=='0'
 for kind in ('boot','warp','h2'):
  p=E/f'qa-{arm}-{kind}-console-r1/qa-gate.json';g=json.loads(p.read_text());assert g['status']=='PASS' and g['source']==m['source'];gates[kind]=g
 retirement=E/f'qa-{arm}-proxy-retirement-r1.json';rr=json.loads(retirement.read_text());assert rr['status']=='REMOVED_ONLY_EXACT_AUTHORIZED_NEW_PROXY_BACKING' and rr['all_final_tracks_full_readback_equal']
 assert not Path(rr['resolved_target']).exists()
 for n,p in x['tracks'].items():assert (d/'gdemu'/n).stat().st_size==p['bytes'] and sha(d/'gdemu'/n)==p['sha256']
 for n in ('README.txt','STEPS.txt','IDENTITY.json','SHA256SUMS.txt','README-tooling.txt'):assert not (d/n).exists()
 other='On' if arm=='off' else 'Off'
 readme=f"""RE4DC private normal QA23 dedup {arm.upper()} - source4be08e01
LOCAL QA GATES PASS; ROOT REVIEW / INTEGRATION / PHYSICAL ACCEPTANCE PENDING.
This is a private QA tool, not a release. No SD copy or publication performed.

Source: {m['source']}
Baseline: d5c1ceab9e06461462669b3ce1d28a379747a74a.
SCENERY_DEDUP={mode}; same standard DATA29 and original assets on both arms,
plus the exact same four compact ps2-dd3 alternate files. OFF0 uses originals;
ON3 selects the strict validated compact alternate. All original geometry,
UV/color/LOD/source identity and all41 texture assets retained; no pruning.
Current audits four fixes ON, EM_READ_RETRY1, arena0; SELECT_ONLY/REPLAY_LEAN/
SUBMIT_BATCH1. Normal QA1/PC0, KOS/squeeze/census/diagnostic contamination0.
SCENERY_EMIT_PREFETCH=0 and SCENERY_SELECT_LEAN2=0 only. The separately found`nexperimental PREFETCH1 context defect is outside this qualified profile.`nProduction recipe dedup remains OFF pending root decision.

Programme {x['programme']['label']}
Raw programme SHA256: {x['programme']['raw_sha256']}
Final standard GDI track03 SHA256: {x['tracks']['track03.bin']['sha256']}
The delivered GDI has independent full track and all-file readback, both
loader/standard lint, actual final-GDI PID-targeted menu boot toR100 PASS.
Separately labelled proxies (same programme/all14/data; only fixture-directory
redirection differs) pass QA menu->R103 and fullH2 1465/571/340 uploads/presents,
restored1. Normal QA s30 heap_before={gates['h2']['heap_before']} bytes.
These are bounded console-mode Flycast MODELLED safety checks, not physical
console acceptance or hardware performance. Standard non-QA matched H2
OFF93920/ON139552 +45632, KOS48 all8, requiredGDEMU10, scoped census/texture/
VRAM checks, event common-window decisions and three held still views pass.
No blanket all-textures-zero claim: the known baseline Mendez late-pair
material limitation remains. Root's separate private PS2 upload repair is not
included or admitted here, and its visible use is unproven.

Compare with RE4DC-QA23-Dedup-{other}-4be08e01 using STEPS.txt.
README-tooling.txt is the unchanged historical QA-menu controls guide; this
README/IDENTITY give actual current provenance. MEDIA-IDENTITY.json preserves
the earlier mastering checkpoint; IDENTITY.json supersedes its pending-gates
status only within local tests. Root final review remains required.
"""
 steps="""PRIVATE TWO-MINUTE R101 COMPARISON - physical observation still pending
Use the same Dreamcast, display, controller and view-distance setting for both
Off and On. Keep existing saves/media untouched; no SD/publication is performed
by this package. Select gdemu/disc.gdi in an emulator for private inspection.

1. At QA menu choose Teleport -> CHAPTER1-1: VILLAGE ->
   R101 VILLAGE SQUARE (FIGHT START). Record which Off/On disc and source4be08e01.
2. Spend at least two minutes moving between the cross, houses and village edges.
   Turn the camera through near/far transitions, building edges and clip seams.
   Look for missing/wrong geometry, UV/color changes, flicker, corrupt strips,
   black frames, freezes, input loss or new loading failures. Repeat same route
   on the other arm; do not infer speed improvement from feel.
3. Hold both triggers fully +D-pad Down to open QA in free play. Check Diagnostics;
   X cycles QR pages, B backs out. Preserve photos/logs and exact scene/action.
4. Optional next checks: R103 farm then R100 forest/house and movie return/reload.
   The authored H2 proxy tests already cover the three movie terminals, but this
   is not proof of physical-console movie/load behavior.
Known baseline Mendez late-pair material limitation remains unrelated; do not
report all materials correct from these bounded tests. No hardware FPS claim.
"""
 (d/'README.txt').write_text(readme);(d/'STEPS.txt').write_text(steps)
 shutil.copyfile(T/'qa20/README-package.txt',d/'README-tooling.txt')
 (d/'QUALIFICATION-PENDING.txt').write_text('Local normal QA checks pass. Root review/integration and physical acceptance remain pending; no SD/publication.\n')
 identity=dict(status='LOCAL_NORMAL_QA_PAIR_GATES_PASS_ROOT_REVIEW_PENDING',source=m['source'],baseline_source='d5c1ceab9e06461462669b3ce1d28a379747a74a',arm=arm,scenery_dedup=mode,programme=x['programme'],tracks=x['tracks'],final_manifest_sha256=x['manifest_sha256'],post_final_manifest_sha256=rr['final_post_manifest_sha256'],only_programme_differences=m['only_programme_differences'],original_assets_and_exact4_alternates_common=True,baseline_packages=plan['baseline_packages'],compact_alternates=plan['alternates'],normal_qa_gates=gates,proxy_retirement_receipt_sha256=sha(retirement),gdemu10_gates_sha256=sha(E/'gdemu10-gates-r1.json'),known_limitations=['Physical-console acceptance pending','No hardware performance claim','Known baseline Mendez late-pair material issue retained; separate unproven-visible PS2 private repair not included','Scoped observed diagnostics, not all-material completeness','SCENERY_EMIT_PREFETCH=0 / SCENERY_SELECT_LEAN2=0 only; separate PREFETCH1 defect is unqualified','Root integration/recipe decision pending'])
 (d/'IDENTITY.json').write_text(json.dumps(identity,indent=2)+'\n')
 sums=[]
 for f in sorted(d.rglob('*')):
  if f.is_file() and f.name!='SHA256SUMS.txt':sums.append(sha(f)+'  '+str(f.relative_to(d)))
 (d/'SHA256SUMS.txt').write_text('\n'.join(sums)+'\n')
 report[arm]=dict(path=str(d),identity_sha256=sha(d/'IDENTITY.json'),sha256sums_sha256=sha(d/'SHA256SUMS.txt'),normal_qa_s30_heap=gates['h2']['heap_before'],final_track03_sha256=x['tracks']['track03.bin']['sha256'])
assert report['on']['normal_qa_s30_heap']>=report['off']['normal_qa_s30_heap']
out=E/'private-qa-pair-seal-r1.json';assert not out.exists();out.write_text(json.dumps(dict(status='LOCAL_NORMAL_QA_PAIR_PASS_ROOT_REVIEW_PENDING',source=m['source'],arms=report,qa_heap_gain=report['on']['normal_qa_s30_heap']-report['off']['normal_qa_s30_heap'],all_final_gdi_bytes_read_back=True,known_baseline_mendez_limit_retained=True,no_sd_publication_or_zip=True,c_free_after=shutil.disk_usage('/mnt/c').free),indent=2)+'\n')
print('PRIVATE_QA_PAIR_SEALED_ROOT_REVIEW_PENDING',report,flush=True)

