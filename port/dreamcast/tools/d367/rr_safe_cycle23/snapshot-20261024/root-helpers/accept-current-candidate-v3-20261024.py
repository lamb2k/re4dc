from pathlib import Path
import fcntl,hashlib,json,shutil
e=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/rr-candidate-handback/fb254e82-20261024/bounded-console-boot-v3')
c=Path('/mnt/c/Game Dev/Emulators/RE4DC-RR/cand-fb254e82')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
with Path('/root/rr/rr.lock').open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    execution=json.loads((e/'ROOT-EXECUTION.json').read_text());bound=json.loads((e/'capture/bounded-console.json').read_text())
    assert execution['status']=='PASS_BOUNDED_FINAL_GDI_TITLE_BOOT'
    assert bound['status']=='PROCESS_GUARD_PASS' and not bound['reason'] and not bound['error'] and bound['harness_rc']==0
    assert 0<bound['observed_child_elapsed_upper_s']<=55 and bound['fps_limit']['aica_LimitFPS']=='yes'
    assert bound['saved_launch_cfg_sha256']==sha(e/'capture/bounded-launch-emu.cfg')
    assert execution['results']['title']['decision']['status']=='BOOT_TITLE_GOAL_PASS'
    approved=Path('/root/probe/rr-safe-boot-fb254e82-v3/ROOT-REVIEWED.json')
    assert sha(approved)==execution['config_sha256']
    backup=e/'root-candidate-metadata-before-acceptance';backup.mkdir(exist_ok=False)
    names=['README.txt','STEPS.txt','IDENTITY.json','QUALIFICATION-SHA256SUMS.txt','SHA256SUMS.txt']
    before={}
    for name in names:
        shutil.copyfile(c/name,backup/name);assert sha(c/name)==sha(backup/name);before[name]=sha(c/name)
    oldrows=[line.split('  ',1) for line in (c/'QUALIFICATION-SHA256SUMS.txt').read_text().splitlines() if line]
    for digest,name in oldrows:assert sha(c/name)==digest,name
    boot=dict(status='PASS_BOUNDED_FINAL_GDI_TITLE_BOOT',source='fb254e82ee6f9a3d9e34d53d1d442348a46b9cf2',adapter='34a5c48bfe22c3d9718810166407048a906b8bcc',profile=bound['profile'],actual_console_sha256=bound['actual_console_sha256'],exact_child_upper_seconds=bound['observed_child_elapsed_upper_s'],child_limit_seconds=55,requested_observation_seconds=45,stop='state title=',grace_seconds=5,explicit_FPS_limit='yes',actual_launch_cfg_sha256=bound['saved_launch_cfg_sha256'],root_execution_receipt=str(e/'ROOT-EXECUTION.json'),root_execution_receipt_sha256=sha(e/'ROOT-EXECUTION.json'),bounds_receipt_sha256=sha(e/'capture/bounded-console.json'),title_log_only=True,full_route_QA_hardware_or_performance_acceptance=False)
    identity=json.loads((c/'IDENTITY.json').read_text())
    identity['status']='PRIVATE_CURRENT_CANDIDATE_BOUNDED_FLYCAST_TITLE_PASS_PHYSICAL_PENDING'
    identity['actual_candidate_console55_boot']=boot
    identity['current_bounded_console_full_cycle_pass']=False
    identity['metadata_backup_before_root_acceptance']=str(backup)
    (c/'IDENTITY.json').write_text(json.dumps(identity,indent=2)+'\n')
    readme=(c/'README.txt').read_text()
    old="Fresh actual-candidate console55 boot remains PENDING for root's bounded adapter."
    assert readme.count(old)==1
    new='Fresh actual final-GDI title boot now PASS: console mode, explicit FPS limit yes, 8.266 seconds observed child upper bound under 55, title goal plus five-second grace and no error rows. Both the independent process-bound audit and separate title judge pass. This log-only check does not establish a fresh full quick/QA cycle, visual acceptance, New Game, full route, hardware speed or physical acceptance. V2 path preflight was refused before any guest; its receipt is retained.'
    (c/'README.txt').write_text(readme.replace(old,new))
    steps=(c/'STEPS.txt').read_text();old="Root's fresh actual-disc console55 boot is pending.";assert steps.count(old)==1
    (c/'STEPS.txt').write_text(steps.replace(old,'Root completed a bounded console-mode Flycast title boot with explicit FPS limit. The physical/manual steps below remain pending.'))
    (c/'QUALIFICATION-SHA256SUMS.txt').write_text(''.join(sha(c/name)+'  '+name+'\n' for _,name in oldrows))
    for line in (c/'QUALIFICATION-SHA256SUMS.txt').read_text().splitlines():
        digest,name=line.split('  ',1);assert sha(c/name)==digest,name
    assert sha(c/'SHA256SUMS.txt')==before['SHA256SUMS.txt']
    registry=Path('/mnt/c/Game Dev/Emulators/CONSOLE-DISCS-TEST23.md')
    shutil.copyfile(registry,backup/'CONSOLE-DISCS-TEST23.md')
    entry='''

## Current integration candidate fb254e82 — 2026-10-24 root handback

Private disc: C:/Game Dev/Emulators/RE4DC-RR/cand-fb254e82/gdemu. See its README.txt, STEPS.txt, IDENTITY.json and SHA256SUMS.txt. No SD copy or publication.

Main raw49a4173a1792823ff5e275b0681b2c354c4e45140b7078d87c1253f2e926090b and all14 programmes match the retained qualified production baseline. Actual1712-file readback/1697unchanged asset rows and four-track hashes are retained. Production DEDUP0/PREFETCH0/SELECT_LEAN20 remain unchanged; all41 Ganado textures stay retained.

Fresh final-GDI console-mode Flycast title check PASS: explicit FPS=yes, requested45/title goal/grace5, observed child upper8.266seconds under55. Separate bounds and semantic receipts: C:/Flycast-Evidence/re4-dreamcast/rr-candidate-handback/fb254e82-20261024/bounded-console-boot-v3/ROOT-EXECUTION.json. This is log-only title evidence, not fresh full-route/QA/visual/hardware acceptance. Existing watcher quick+QA PASS remains its separate legacy profile (32harness plus2console60 captures). QA ZIP retained and hashed without new extraction or QA-media readback. Manual New Game, VMU, boat/dam/church/Mendez and physical performance remain pending.
'''
    assert '## Current integration candidate fb254e82 — 2026-10-24 root handback' not in registry.read_text()
    with registry.open('a') as f:f.write(entry)
    receipt=dict(status='PRIVATE_CURRENT_CANDIDATE_METADATA_ACCEPTED_TITLE_ONLY',before=before,after={name:sha(c/name) for name in names},registry_sha256=sha(registry),boot=boot,disc_assets_recipe_or_QA_zip_changed=False,publication_or_SD=False)
    with (e/'ROOT-DELIVERY.json').open('x') as f:json.dump(receipt,f,indent=2);f.write('\n')
    print(json.dumps(dict(status=receipt['status'],elapsed_upper_s=boot['exact_child_upper_seconds'],identity_sha256=sha(c/'IDENTITY.json'),disc=str(c/'gdemu'),physical_acceptance='PENDING'),indent=2))
