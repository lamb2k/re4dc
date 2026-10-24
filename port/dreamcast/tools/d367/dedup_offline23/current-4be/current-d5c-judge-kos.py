from pathlib import Path
import json,hashlib,re
ev=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/dedup-offline23-20261023/current-4be08e01')
o=Path('/root/probe/lanes/route/out-fpdd23cur4be08e01diagW')
knobs=dict(x.split('=',1) for x in (o/'resolved-knobs.txt').read_text().splitlines() if '=' in x)
for k in ('SCENERY_DEDUP=3','KOS_WATCH=1','KOS_SQUEEZE=1','W11_FIXTURE=1','TEX_CHECK=1','MCHECK_LEONGC=1','NATIVE_MODEL_REGISTRY_CENSUS=1','VRAM_ROOM_LOG=1'):
    key,value=k.split('=');assert knobs[key]==value,k
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
rows={}
for scene in ('fight','call','leave100','leave103'):
    for frag in (0,1):
        name=f'kos-{scene}-{frag}';cap=ev/(name+'-console-r1')
        rr=json.loads((cap/'run-result.json').read_text());b=json.loads((cap/'bounded-launch.json').read_text());text=(cap/'run-output.txt').read_text(errors='replace')
        assert rr['status']=='RUN_COMPLETE' and rr['emu']=='console' and not rr['errors'] and not b['deadline_fired']
        assert b['guest_observed_elapsed_s']<=55
        held=re.findall(r'kos squeeze: held=(\d+)',text);assert held==['49152']
        hs=[int(v) for v in re.findall(r'kos watch:[^\n]*headroom=(\d+)',text)];assert hs and min(hs)>=4096,(name,min(hs) if hs else None)
        assert not re.search(r'\b(?:HALT|FAULT|MISSING)\b|Out of memory',text)
        endpoint=dict(fight='warp: alert at room frame',call='subscreen backing: open',leave100='phase=enter room=100',leave103='phase=enter room=103')[scene]
        assert endpoint in text,(name,'missing endpoint')
        if scene in ('leave100','leave103'):assert 'phase=enter room=101' in text
        cfg=(cap/'emu.cfg').read_text();assert 'aica.LimitFPS = no' in cfg
        assert rr['tracks']['track03_sha256']==(ev/'base-diag-current4be-r1/track03.sha256').read_text().strip()
        rows[name]=dict(minimum_headroom=min(hs),held=49152,fragmentation=frag,observed_guest_seconds=b['guest_observed_elapsed_s'],endpoint=endpoint,log_sha256=sha(cap/'run-output.txt'),result_sha256=sha(cap/'run-result.json'),bounded_sha256=sha(cap/'bounded-launch.json'),config_sha256=sha(cap/'emu.cfg'),fixture=rr['fixtures']['warp'])
report=dict(status='PASS_CURRENT_48K_ALL8_BOUNDED_SCENES',source='4be08e0110592510e3630c01fa9f49b3ac2fed3d',programme=str(o),elf_sha256=sha(o/'re4dc-game.elf'),knobs_sha256=sha(o/'resolved-knobs.txt'),runs=rows,limits='MODELLED console FP_NOLIMIT1, actual held/headroom/endpoints; no physical-hardware timing/memory or all-frame state equality claim.')
p=ev/'kos-48k-gates-r1.json';assert not p.exists();p.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v['minimum_headroom'] for k,v in rows.items()}))
