#!/usr/bin/env python3
import hashlib,json,pathlib,shutil
D=pathlib.Path('C:/Game Dev/Emulators/RE4DC-QA23-Audits-5e4de9a0')
E=pathlib.Path('C:/Flycast-Evidence/re4-dreamcast/audits23-takeover/5e4de9a0')
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
 return h.hexdigest()
j=json.loads((D/'IDENTITY.json').read_text()); tracks={k:sha(D/k) for k in j['tracks']}; assert all(tracks[k]==v['sha256'] for k,v in j['tracks'].items())
backup=E/'qa-identity/docs-pre-refresh-v1';backup.mkdir(exist_ok=False)
for n in ('README.txt','STEPS.txt','IDENTITY.json','SHA256SUMS.txt'):shutil.copy2(D/n,backup/n)
(D/'STEPS.txt').write_text('''PRIVATE AUDITS QA — normal arena-OFF profile, source5e4de9a0

Start each progression check from a fresh boot so earlier solves do not carry over.
Boot gdemu/disc.gdi. Choose TELEPORT, Chapter1, then the named preset.
In game, hold L+R and press D-pad Down to reopen the QA menu.
Keep the normal quality/view settings and cap4; use ordinary movement/buttons.

1. Normal village: choose R101 VILLAGE SQUARE (FIGHT START).
   Walk and fight around the cross and houses. Note any freeze, missing
   geometry, stuck progress or fault; photograph the full screen if one occurs.

2. Dam first villager: choose R10C DAM. Follow the dam path to its first
   scripted axe-Ganado encounter. The first villager should appear and animate;
   the event should finish and return control, rather than skip the actor or hang.
   Continue normally toward the later enemies. If the event does not start,
   photograph your position and report that; room entry alone is not a pass.
   This manual QA route is separate from the source-bound placement fixture
   used in the local check; a full dam traversal is still a console test.

3. Church light puzzle: choose R117 ENTRY. Climb to the upper mechanism
   and use OPERATE. From the fresh unsolved puzzle, select the first light
   and rotate twice, the second three times, and the third once. Return to
   the colour-selection menu between lights, then choose the fourth/check
   pattern option. Let the opening event finish. Check that the way opens,
   control returns and the mechanism no longer offers OPERATE.
   Report a crash, frozen beams/menu or a gate that stays closed; photograph it.

4. Arena challenge: use the SEPARATE RE4DC-QA23-Audits-Arena-53fcbc0b
   disc and its own STEPS.txt for two physical minutes in the r101 fight.
   This normal disc has VRAM_ROOM_ARENA0 and cannot test the arena-enabled profile.

The matched local OFF/ON dam and church sequences complete in console-mode
Flycast; source/host allocation-failure controls pass. Physical checks above
are pending. No physical crash-cause, arena cure, speed gain or full release
acceptance is claimed. No SD or publication operation was performed.
''',encoding='utf-8')
(D/'README.txt').write_text('''PRIVATE NORMAL AUDITS QA — 5e4de9a0

Source5e4de9a0262d3629c9833c959557de198b2e9f0c, normal arena-OFF QA.
ESP_POOL_RECYCLE1 R117_EFFECT_FAILURE_SAFE1 KOS_CACHE_P2_1
R10C_SPAWN_LIVE_GUARD1; EM_READ_RETRY1 STAT_ROUTINE_BYTES1.
STAT_DIAG0 KOS_CACHE_P2_DIAG0 QA_MENU1 PC_SAMPLER0 VRAM_ROOM_ARENA0.
The KOS switch's actual name is KOS_CACHE_P2=1 (the line above is prose).
At this document refresh production's four audit switches remain OFF;
root is preparing the qualified integration landing.

Local console-mode Flycast checks (timing MODELLED): production-profile
H2 s30 340/340, heap_before93920; both48KiB memory modes; ten disc seeds;
four-room census/TEXCHK and bell/Mendez decision comparisons pass.
Matched OFF/ON source-native dam observations identify the actual live first
villager, motion progression and normal event exit. Both normal puzzle
sequences solve; root inspected real loaded before/after mechanism pictures.
These pictures are phase-qualified, not tick-matched pixel-identity proof.
Historical allocation failures and exact overlay phases were not injected.

This exact QA package has its own boot26.6s, menu-warp22.3s and H2 32.1s
checks, all goals reached with no harness errors/deadline; s30 340/340 and
heap_before48768. Its profile differs from production diagnostics.
Loader/standard package lint and staged programme/all14overlay readback pass.
Full identities and local receipts are bound in IDENTITY.json.

Physical acceptance, the historical arena two-minute run/crash cause,
whole IRQ-blocked cache duration and a fresh full release remain pending.
Use separate RE4DC-QA23-Audits-Arena-53fcbc0b for the ARENA1 challenge.
Neither current disc is historical B/B3 layout-identical.

See STEPS.txt. No SD copy, release, GitHub post or publication.
'''.replace('KOS_CACHE_P2_1','KOS_CACHE_P2=1').replace("The KOS switch's actual name is KOS_CACHE_P2=1 (the line above is prose).\n",''),encoding='utf-8')
j['local_unit_qualification']={'status':'BOUNDED_LOCAL_GATES_PASS_RECIPE_LANDING_PENDING','receipt':str(E/'LOCAL-GATE-RECEIPT.json'),'receipt_sha256':sha(E/'LOCAL-GATE-RECEIPT.json'),'off_events_source':'2a14662d4b025031cd93f64eed6a5d8159d473b7','on_events_source':j['source'],'dam_and_puzzle_local_observed':True,'historical_failure_injected_in_guest':False,'overlay_phases_authenticated':False,'pixel_identical_claim':False,'physical_acceptance':False,'full_release_acceptance':False}
(D/'IDENTITY.json').write_text(json.dumps(j,indent=2)+'\n',encoding='utf-8')
files=sorted(f for f in D.rglob('*') if f.is_file() and f.name!='SHA256SUMS.txt')
(D/'SHA256SUMS.txt').write_text(''.join(f'{sha(f)}  {f.relative_to(D).as_posix()}\n' for f in files),encoding='utf-8')
assert all(sha(D/k)==v for k,v in tracks.items())
r={'tracks_unchanged':tracks,'docs':{n:sha(D/n) for n in ('README.txt','STEPS.txt','IDENTITY.json','SHA256SUMS.txt')},'backup':str(backup),'physical_acceptance':False}
(E/'qa-identity/docs-refresh-v1.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))