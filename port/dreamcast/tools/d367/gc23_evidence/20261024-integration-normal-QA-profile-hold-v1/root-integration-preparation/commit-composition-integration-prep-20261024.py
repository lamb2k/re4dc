from pathlib import Path
import subprocess,json,datetime,hashlib
root=Path('/root/work/lanes/codex-composition-int24');owned=root/'port/dreamcast/tools/d367/composition_int24';readme=owned/'README.md'
readme.write_text('''# Local composition source preparation

This branch combines current fb254 integration with exact source units aab201ce (GC catalog/Motion),7eb109ea (visibility/source provenance/effective0),b6b4fa7a (PVS batching draw-all/deferred diagnostics), and da413ff0 (rain diagnostics). All experimental defaults and the production recipe remain unchanged. The local preparation merges are not t15/int landings or qualified runtime composition.

Root adds strict Make and both translation-unit source rejection for COMPOSE1 together with GC asset Gate/Motion diagnostics. These simultaneous enabled paths have not been qualified. COMPOSE0 still permits ordinary GC diagnostics; GC0 permits the existing receipt-only composition. The selected-original-affine source sentinel and effective0 guards are retained from the visibility source, rather than treating the older fb-only composition receipts as certified source proof.

Seven integrated actual-extracted host methods pass under256MiB and one worker. They retain ten intended failing compiled runtime mutants, actual hot/cold/end/batch/UV0/1 controls,18 full-file OFF preprocessing comparisons (GC0/1 separately with COMPOSE0) and disabled extracted host object identity. Three additional admission-guard removal mutations each fail the specific acceptance control. This does not prove actual target/cache/material/scene/numeric/raster receipts, SDK output or any hiding. The historical fb-based source test is preserved; this owned adapter uses the exact pre-composition integrated commit e3ed0d2ab2482ade7f5a3615009f59a43ccdcfae as its disabled identity comparison.

The first integrated host fixture omitted the actual Gate0 model accounting macros and failed compilation. Its exact fixture/compact failure receipt are preserved externally. The successor projects the two actual disabled source definitions; it does not invent model_handle state or mock an enabled GC provider. No game runtime was changed to make that fixture pass.

Receipt-only mode remains DRAW ALL. Source-pending physical batch closes precede unchanged eligibility/commit; deferred acquisition logs preserve old key/frame and sourceWorldAcquired0/1, with no new log while direct/retained world SQ is held on the supported path. Existing fatal/exception Render_before reentry while an active owner holds SQ remains unsupported. A void ui_begin early return would not stop its caller from continuing GX work, so no such workaround is claimed. The narrow prepare refusal preserves the current ticket, and is not a ticket revocation contract.

No SDK, guest, data generation, runtime cut, speed, memory gate, private QA disc, production recipe, SD or publication acceptance follows. Numeric/fresh-context candidate-specific hiding is still required after an actual useful proof and layout review. The root goal remains active.
''')
def run(*a):
 r=subprocess.run(['git','-C',str(root),*a],capture_output=True,text=True);assert r.returncode==0,(a,r.stdout,r.stderr);return r.stdout.strip()
paths=['port/dreamcast/game/scenery19.mk','port/dreamcast/game/platform/native_static.cpp','port/dreamcast/game/platform/native_ui.cpp','port/dreamcast/tools/d367/composition_int24/README.md','port/dreamcast/tools/d367/composition_int24/test_compose_integrated.py']
assert not run('diff','--name-only','fb254e82','--','port/dreamcast/tools/d367/rr/recipe.conf')
assert not run('diff','--check')
run('add','--',*paths);run('commit','-m','Prepare guarded visibility and diagnostics composition with exact source host controls')
head=run('rev-parse','HEAD');assert not run('status','--porcelain')
r={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source':head,'branch':'wip/codex-composition-int24-20261024','base':'fb254e82ee6f9a3d9e34d53d1d442348a46b9cf2','scope':'Default-off source preparation and strict cross-feature guard; local no-ff units retained, no t15/int landing/recipe/SDK/guest/asset change. Independent integrated review pending.','runtime_guard_paths':paths[:3],'tests':'7 integrated actual-extracted methods;10 existing intended failing compiled runtime mutants;18 OFF CPP pairs;disabled extracted host object identity;3 extra admission-guard mutants','preserved_failure':'First integrated fixture lacked actual GC Gate0 macro projection; compile refusal preserved, not counted as a semantic pass'}
out=Path('/mnt/c/Game Dev/Emulators/codex-lanes/composition-int24/ROOT-CHECKPOINT.json');out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
