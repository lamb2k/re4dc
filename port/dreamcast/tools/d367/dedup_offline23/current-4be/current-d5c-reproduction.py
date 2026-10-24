from pathlib import Path
import hashlib,json,subprocess
source='4be08e0110592510e3630c01fa9f49b3ac2fed3d'
ev=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/dedup-offline23-20261023/current-4be08e01')
root=Path('/root/probe/lanes/route');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
rows={}
for arm,mode in [('off','0'),('on','3')]:
    release=root/('out-dd23cur4be08e01'+arm+'rP');p=root/('out-fpdd23cur4be08e01'+arm+'gP');w=root/('out-fpdd23cur4be08e01'+arm+'gW')
    for o in (release,p,w):
        assert (o/'stack.txt').read_text().splitlines()==[source] and not (o/'missing.txt').read_bytes()
        k=dict(s.split('=',1) for s in (o/'resolved-knobs.txt').read_text().splitlines() if '=' in s)
        assert k['SCENERY_DEDUP']==mode
        for name in ('SCENERY_SELECT_ONLY','SCENERY_REPLAY_LEAN','SCENERY_SUBMIT_BATCH','STAT_ROUTINE_BYTES','ESP_POOL_RECYCLE','R117_EFFECT_FAILURE_SAFE','KOS_CACHE_P2','R10C_SPAWN_LIVE_GUARD','EM_READ_RETRY'):assert k[name]=='1'
        for name in ('QA_MENU','WORLD_METER','PC_SAMPLER','NATIVE_MODEL_REGISTRY_CENSUS','KOS_WATCH','KOS_SQUEEZE','STAT_DIAG','KOS_CACHE_P2_DIAG','VRAM_ROOM_ARENA'):assert k[name]=='0'
    raw={}
    for name,o in [('release',release),('reproduction',p)]:
        f=Path('/dev/shm')/('dedup4be-repro-'+arm+'-'+name+'.bin');assert not f.exists()
        subprocess.run(['/opt/toolchains/dc/sh-elf/bin/sh-elf-objcopy','-R','.stack','-O','binary',str(o/'re4dc-game.elf'),str(f)],check=True)
        raw[name]=sha(f)
    assert raw['release']==raw['reproduction']
    a={f.name:sha(f) for f in release.glob('*.ovl')};b={f.name:sha(f) for f in p.glob('*.ovl')}
    assert len(a)==len(b)==14 and a==b
    rows[arm]=dict(release=str(release),reproduction=str(p),warp_twin=str(w),raw=raw,all14_overlays_equal=True,overlay_sha256=a,warp_elf_sha256=sha(w/'re4dc-game.elf'),warp_resolved_sha256=sha(w/'resolved-knobs.txt'))
(ev/'reproduction-identity.json').write_text(json.dumps(dict(status='PASS_ACTUAL_RELEASE_REPRODUCTION_MAIN_AND_ALL14',source=source,arms=rows),indent=2)+'\n')
print('CURRENT_RELEASE_REPRODUCTION_MAIN_ALL14_PASS',list(rows))
