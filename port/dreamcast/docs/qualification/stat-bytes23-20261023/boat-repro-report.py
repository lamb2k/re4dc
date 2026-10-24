"""Build the bounded boat HUD evidence receipt; no guest starts or asset mutations."""
from pathlib import Path
import collections,hashlib,html,json,re,shutil
root=Path(r'C:\Flycast-Evidence\re4-dreamcast\stat-bytes23\takeover-2a14662d')
ev=root/'boat-repro-20261023';lane=Path(r'C:\Game Dev\Emulators\codex-lanes\stat-bytes23')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
result={'source':'2a14662d4b025031cd93f64eed6a5d8159d473b7','evidence':'MODELLED / Flycast console proxy, not physical Dreamcast','run_policy':'Sequential OFF then ON, exact owned child deadline55s, STAT slot then global trace slot16, FP_NOLIMIT1; no global input','arms':{}}
selected={'off':'s01-011390','on':'s01-011094'}
for arm in ['off','on']:
 cap=ev/arm;run=json.loads((cap/'run-result.json').read_text());bound=json.loads((cap/'bounded-launch.json').read_text());obs=json.loads((cap/'boat-observation.json').read_text())
 rows=[json.loads(s) for s in (cap/'boat-ram-samples.jsonl').read_text().splitlines()]
 assert run['status']=='RUN_COMPLETE' and not run['errors']
 assert bound['guest_exited'] and not bound['deadline_fired'] and bound['guest_observed_elapsed_s']<55
 assert obs['boat_samples']>0 and not any('fatal' in e for e in obs['errors'])
 shot=cap/'boat-stills'/selected[arm];state=json.loads((shot/'observed-state.json').read_text())
 assert state['routine_bytes']==[0,15,0,1] and state['room']=='10b' and state['weapon_no']==2 and state['pl_type']==0
 assert state['boat']['id']==15 and state['m_pBoat']!='0x0'
 target=ev/(arm.upper()+'-boat-HUD.png');shutil.copyfile(shot/'frames'/'fb0.png',target)
 knobs={}
 for line in (root/'identities'/(arm+'-g-knobs.txt')).read_text().splitlines():
  if re.match(r'^(SS_ACTOR_LIFETIME|STAT_DIAG|STAT_ROUTINE_BYTES|VMU_CONTEXT)=',line):
   k,v=line.split('=',1);knobs[k]=v
 assert knobs['STAT_ROUTINE_BYTES']==('0' if arm=='off' else '1') and knobs['STAT_DIAG']=='0'
 result['arms'][arm]={'pid':bound['pid'],'guest_started_monotonic':bound['guest_started_monotonic'],'guest_elapsed_s':bound['guest_observed_elapsed_s'],'deadline_fired':bound['deadline_fired'],'source_identity_sha256':sha(root/'identities'/(arm+'-g-source.txt')),'programmes_manifest_sha256':sha(root/'identities'/(arm+'-g-programmes.sha256')),'main_elf_sha256':(root/'identities'/(arm+'-g-programmes.sha256')).read_text().splitlines()[0].split()[0],'knobs':knobs,'sample_count':len(rows),'boat_sample_count':obs['boat_samples'],'boat_states':dict(collections.Counter(tuple(r['routine_bytes']) for r in rows if r['boat_routine_0_0f'])) if False else [{'bytes':list(k),'count':v} for k,v in collections.Counter(tuple(r['routine_bytes']) for r in rows if r['boat_routine_0_0f']).items()],'selected_state':state,'still':target.name,'still_sha256':sha(target),'observer_startup_or_transient_read_errors':obs['errors'],'log_overrun':bool(re.search(r'\[LOG OVERRUN',(cap/'run-output.txt').read_text(errors='replace')))}
a=result['arms'];assert a['off']['guest_started_monotonic']+a['off']['guest_elapsed_s']<a['on']['guest_started_monotonic']
result['selected_visual_observation']={'off':'Visible cyan ammunition digits10 and handgun cartridge icon','on':'No ammunition digits; cyan harpoon icon instead','expected_source':'cockpit.cpp dispBulletDigit returns0 for canonical upper-half000f; dispBulletIconMarkNo returns0x33 in room10b','limits':'Selected images differ in pose/camera/animation phase; not a pixel-identical pair. RAM samples authenticate actual boat player routine and boat-object association, not individual branch execution or VMU display acceptance.'}
for name in ['boat-repro-observer.py','boat-repro-run.sh','boat-repro-report.py','census-bound-run.py','stat-guest-slot.sh']:shutil.copyfile(lane/name,ev/name)
result['host_scripts']={n:sha(ev/n) for n in ['boat-repro-observer.py','boat-repro-run.sh','boat-repro-report.py','census-bound-run.py','stat-guest-slot.sh']}
(ev/'receipt.json').write_text(json.dumps(result,indent=2)+'\n')
report=f'''# Current-candidate boat HUD OFF / ON repro

MODELLED / Flycast console proxy. Source {result['source']}. Existing production g bases, original boat-warp.txt and boat-pad.txt, no runtime or production recipe edits. Both resolved STAT_DIAG=0; STAT_ROUTINE_BYTES OFF0 / ON1. Exact ELF hashes match the existing programme identities: OFF {a['off']['main_elf_sha256']}; ON {a['on']['main_elf_sha256']}.

**Visible result:** [OFF](OFF-boat-HUD.png) shows cyan ammunition digits10 and the handgun cartridge icon. [ON](ON-boat-HUD.png) suppresses the digits and shows the harpoon icon. The images have different animation/camera phases and are not a pixel-identical comparison.

The selected stills have read-only owned-process RAM receipts: room10b, Leon character0, equipped weapon2, player routine bytes00 0f 00 01 (native word01000f00; canonical000f0001), and a non-null m_pBoat whose actual object id is0f with routine01 01 00 00. This authenticates entry into the actual player boat routine, rather than inferring execution from STATDIAG mask disagreement. The selected OFF state was sampled at{a['off']['selected_state']['host_s']}s, ON at{a['on']['selected_state']['host_s']}s. Counts: OFF {a['off']['boat_sample_count']}/{a['off']['sample_count']} boat-state samples; ON {a['on']['boat_sample_count']}/{a['on']['sample_count']}.

The pinned source union is include/model.h:412-418 (r_no_0..3 atFC..FF); m_pBoat is include/em.h:182 at50c. pPL/pG symbols were read from the exact g ELFs: OFF8c363080/8c2b28dc, ON8c363020/8c2b287c. Process image and exact capture path were verified before read-only access; no RAM writes, debugger stops, window/global input, or new instrumentation. Existing capture_ui_vram.py reads both RGB565 framebuffers. State and framebuffer reads are asynchronous, not an exact simulation-tick correspondence.

Source expectation: src/game/cockpit.cpp:647-661 returns no digits in canonical routine0/0f; :696-709 selects icon0x33 in that state (except room333). The current SS_ACTOR_LIFETIME1 path obtains raw state through sscrn_bridge.cpp:564-567, which uses live pPL outside a subscreen snapshot. The current unit wraps the predicate constants with STAT_BE. Pl0f source documents the actual player boat dispatch and boarding/steering states at src/pl0f/pl0f.cpp:1-18. These stills do not prove the rudder step2 predicate executed; selected boarding state is0/0f/0/1. They also do not visually certify the optional VMU ammo display.

Run limits: one owned guest at a time; OFF PID{a['off']['pid']} {a['off']['guest_elapsed_s']}s, ON PID{a['on']['pid']} {a['on']['guest_elapsed_s']}s. Both RUN_COMPLETE with no harness errors, exact child55s deadlines not fired, no log overruns, sequential lifetimes verified. Each used the STAT three-slot allocator then host trace16 lock, console proxy and FP_NOLIMIT1. Observer startup reads briefly preceded committed RAM/log availability; recorded transient misses did not prevent hundreds of valid samples or selected verified reads. No branch-hit counter was added. No timing, whole-unit gameplay, physical console, release or source-provenance acceptance is claimed.

Stills and complete states: off/boat-stills/{selected['off']}/ and on/boat-stills/{selected['on']}/. Both original framebuffers and additional boat stills are preserved. receipt.json contains counts, exact state/ELF/script/still hashes and bounded-child evidence. Source-only host observer/runner/reporter are mirrored here; original captures and fixtures remain intact.
'''
(ev/'REPORT.md').write_text(report)
(lane/'BOAT-REPRO-RESULT.md').write_text(report)
(ev/'pair.html').write_text('<!doctype html><meta charset="utf-8"><title>Boat HUD OFF / ON</title><style>body{background:#151515;color:#eee;font:16px system-ui;margin:24px}main{display:flex;gap:20px;flex-wrap:wrap}figure{margin:0;max-width:640px}img{width:100%}figcaption{padding:12px 0}small{display:block;max-width:1200px;line-height:1.5}</style><h1>Current-candidate boat HUD</h1><main><figure><img src="OFF-boat-HUD.png"><figcaption>OFF: handgun cartridge icon and ammunition digits10 remain visible.</figcaption></figure><figure><img src="ON-boat-HUD.png"><figcaption>ON: ammunition digits hidden; boat harpoon icon displayed.</figcaption></figure></main><small>MODELLED / Flycast console proxy. Both selected samples: room10b, Leon, weapon2, actual player routine00 0f 00 01 and boat objectid0f. Asynchronous frames differ in pose/camera; this is a HUD behavior comparison, not a pixel-identical pair or physical-console acceptance. Source2a14662d4. See REPORT.md and receipt.json.</small>')
files=[p for p in ev.iterdir() if p.is_file() and p.name!='SHA256SUMS']
(ev/'SHA256SUMS').write_text(''.join(sha(p)+'  '+p.name+'\n' for p in sorted(files)))
print(json.dumps({'report':str(ev/'REPORT.md'),'arms':{arm:{k:v for k,v in a[arm].items() if k in ['pid','guest_elapsed_s','sample_count','boat_sample_count','still_sha256','log_overrun']} for arm in a},'report_sha256':sha(ev/'REPORT.md'),'receipt_sha256':sha(ev/'receipt.json')},indent=2))
