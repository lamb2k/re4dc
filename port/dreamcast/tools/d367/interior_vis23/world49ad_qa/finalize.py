#!/usr/bin/env python3
"""Seal completed programme-only QA receipts; do not stage or execute anything."""
import hashlib, json, runpy, shutil, subprocess
from pathlib import Path

HERE=Path(__file__).resolve().parent
P=runpy.run_path(str(HERE/'programme.py'),run_name='qa_programme_binding')
EV,WORK,TREE,SOURCE=P['EV'],P['WORK'],P['TREE'],P['SOURCE']
GATE=Path('/mnt/c/Game Dev/Emulators/codex-lanes/world-emit23/current-gates/current_gates.py')
G=runpy.run_path(str(GATE),run_name='current_gate_binding_only')
sha=P['sha'];identity=P['identity'];write=P['write'];P['source_check']()
assert G['SOURCE']==SOURCE
pins=json.loads((GATE.parent/'pins.json').read_text())
assert pins['source']==SOURCE and pins['recipe_sha256']==P['RECIPE']
subprocess.run(['git','-C',str(TREE),'merge-base','--is-ancestor',pins['base_current'],SOURCE],check=True)
rows={}
for arm in ('reference','off','both'):
 receipt=json.loads((EV/arm/'receipt.json').read_text());assert receipt['source']==SOURCE
 for name,info in receipt['programme_files'].items():assert identity(EV/arm/name)==info,(arm,name)
 actual=G['knobs']((EV/arm/'resolved-knobs.txt').read_text())
 for key,value in G['BASE_KNOBS'].items():assert actual.get(key)==str(value),(arm,key,actual.get(key),value)
 for key,value in P['REQUIRED'].items():assert actual.get(key)==value,(arm,key)
 for key in ('SCENERY_SELECT_LEAN2','SCENERY_EMIT_PREFETCH'):assert actual[key]==str(int(arm=='both'))
 end=int((EV/arm/'end.txt').read_text().strip(),16)
 rows[arm]=dict(elf=identity(EV/arm/'re4dc-game.elf'),main=identity(EV/arm/'main-no-stack.bin'),
                scrambled=identity(EV/arm/'1ST_READ.BIN'),overlays={p.name:identity(p) for p in sorted((EV/arm).glob('*.ovl'))},
                end_address=hex(end),base_knobs={k:actual[k] for k in G['BASE_KNOBS']},
                qa_knobs={k:actual[k] for k in P['REQUIRED'] if k.startswith('QA_') or k in ('WORLD_METER','GAME_TICK_LOG','PHASE_METER','DISC_READ_METER','KOS_WATCH','KOS_SQUEEZE')})
 build=WORK/'build'/arm
 for name in ('launch.log','kos-before.sha256','kos-after.sha256'):shutil.copy2(build/name,EV/arm/name)
 assert (build/'kos-before.sha256').read_bytes()==(build/'kos-after.sha256').read_bytes()
for pair in ('off','both'):
 report=json.loads((EV/('compare-'+pair+'.json')).read_text());assert report['source']==SOURCE
 if pair=='off':assert not report['normalized_profile_differences'] and all(report['programme_byte_equal'].values())
 else:assert report['normalized_profile_differences']=={'SCENERY_SELECT_LEAN2':['0','1'],'SCENERY_EMIT_PREFETCH':['0','1']}
assert len(list((EV/'preset-plan-snapshot').glob('*.txt')))==34
assert sum(l.startswith('p ') for l in (EV/'preset-plan-snapshot/menu.txt').read_text().splitlines())==33
for info in json.loads((EV/'plan.json').read_text())['qa_presets'].values():
 p=Path(info['path']);assert sha(EV/'preset-plan-snapshot'/p.name)==info['sha256']
assert not any(p.name in ('gdemu','pkgtree','_discs','capture','captures') for p in EV.rglob('*') if p.is_dir())
shutil.copy2(GATE,EV/'current-gates-binding-source.py');shutil.copy2(GATE.parent/'pins.json',EV/'current-gates-pins.json')
summary=dict(kind='WORLD49AD PRIVATE QA PROGRAMMES ONLY; NOT READY',source=SOURCE,
             source_tree=str(TREE),recipe_sha256=P['RECIPE'],current_gate_source=identity(EV/'current-gates-binding-source.py'),
             helper_source=identity(Path(__file__)),programmes=rows,
             off_reproduces_fresh_normal_QA_reference_main_and_all14=True,
             both_changes_exactly=['SCENERY_SELECT_LEAN2','SCENERY_EMIT_PREFETCH'],
             qa_presets=33,effective_quality_divisor=20,
             static_end_delta_both_minus_off=int(rows['both']['end_address'],16)-int(rows['off']['end_address'],16),
             unit_binding_scope='Exact source ancestry, current-gate BASE_KNOBS and normal-QA overrides only; no old gate result is promoted to a new QA pass',
             production_switches='OFF; no Dreamcast hardware gain established',hair_repair='not production approved; no asset staged',
             stages=0,guests=0,root_review='PENDING; remaining unit/image/asset/console qualification belongs to root')
write(EV/'PROGRAMME-HANDBACK.json',summary)
manifest={str(p.relative_to(EV)):identity(p) for p in sorted(EV.rglob('*')) if p.is_file()}
write(EV/'SHA256-MANIFEST.json',dict(kind='programme/planning evidence only; no game assets',source=SOURCE,files=manifest))
print(json.dumps(dict(source=SOURCE,off_main=rows['off']['main']['sha256'],both_main=rows['both']['main']['sha256'],
                     end_delta=summary['static_end_delta_both_minus_off'],manifest_sha256=sha(EV/'SHA256-MANIFEST.json'),
                     evidence_bytes=sum(v['bytes'] for v in manifest.values()),unit_base_knobs=len(G['BASE_KNOBS']),ready=False)))
