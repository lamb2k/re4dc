from pathlib import Path
import json,hashlib,math
from PIL import Image,ImageChops
ev=Path(r'C:\Flycast-Evidence\re4-dreamcast\dedup-offline23-20261023\current-4be08e01')
pre=json.loads((ev/'current4be-preflight-r1.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
results={}
for view in ('cross','farm','forest'):
    arms={}
    for arm in ('off','on'):
        cap=ev/f'{view}-{arm}-explicit-limited-console-r4'
        run=json.loads((cap/'run-result.json').read_text());bounded=json.loads((cap/'bounded-launch.json').read_text())
        assert run['status']=='RUN_COMPLETE' and run['stopped']=='goal' and run['emu']=='console' and not run['errors']
        assert not bounded['deadline_fired'] and bounded['guest_observed_elapsed_s']<=55
        cfg=(cap/'emu.cfg').read_text();assert 'aica.LimitFPS = yes' in cfg
        limited=json.loads((cap/'limitfps-run-binding.json').read_text());prelaunch=json.loads((cap/'limitfps-prelaunch.json').read_text())
        assert limited['guest_started'] and limited['pid']==bounded['pid'] and limited['aica.LimitFPS_yes'] and limited['config_still_matches_prelaunch']
        assert prelaunch['wrapper_sha256']=='872a4a2d30ec342cf01e15d04507269f02a713c8eccc68c3dde5320afb1eff15'
        assert sha(cap/'emu.cfg')==limited['actual_config_sha256']==prelaunch['actual_config_sha256']
        text=(cap/'run-output.txt').read_text(errors='replace')
        assert 'warp: frozen at tick 330' in text
        assert run['fixtures']['warp']['sha256']==hashlib.sha256((cap/'fixture-warp.txt').read_bytes().replace(b'\r',b'')).hexdigest()
        assert run['tracks']['track03_sha256']==(ev/f'base-standard-current4be-{arm}-r1'/'track03.sha256').read_text().strip()
        stop=run['stop_matched_s'];late=[]
        for shot in sorted((cap/'shots').glob('t*')):
            if int(shot.name[1:])<math.ceil(stop)+1:continue
            row=dict(path=str(shot),nominal_host_second=int(shot.name[1:]),frames={})
            for fb in ('fb0','fb1'):
                p=shot/'frames'/f'{fb}.png';im=Image.open(p).convert('RGB')
                row['frames'][fb]=dict(path=str(p),file_sha256=sha(p),pixel_sha256=hashlib.sha256(im.tobytes()).hexdigest(),size=list(im.size))
            late.append(row)
        assert late,(view,arm,'no unambiguously post-freeze screenshots')
        # Every observed late snapshot must be stable within this held frame.
        for fb in ('fb0','fb1'):
            assert len({x['frames'][fb]['pixel_sha256'] for x in late})==1,(view,arm,fb,'late framebuffer changed')
        arms[arm]=dict(stop_matched_s=stop,elapsed_host_s=run['elapsed_s'],fixture=run['fixtures']['warp'],log_sha256=sha(cap/'run-output.txt'),result_sha256=sha(cap/'run-result.json'),bounded_sha256=sha(cap/'bounded-launch.json'),actual_fps_limited_config_sha256=sha(cap/'emu.cfg'),limitfps_prelaunch_sha256=sha(cap/'limitfps-prelaunch.json'),limitfps_run_binding_sha256=sha(cap/'limitfps-run-binding.json'),post_freeze=late)
    assert arms['off']['fixture']['sha256']==arms['on']['fixture']['sha256']
    differences={}
    for fb in ('fb0','fb1'):
        a=Image.open(arms['off']['post_freeze'][-1]['frames'][fb]['path']).convert('RGB')
        b=Image.open(arms['on']['post_freeze'][-1]['frames'][fb]['path']).convert('RGB')
        assert a.size==b.size
        px=list(ImageChops.difference(a,b).getdata());count=sum(max(p)>0 for p in px)
        differences[fb]=dict(changed_pixels=count,max_channel_difference=max(max(p) for p in px),size=list(a.size))
    results[view]=dict(arms=arms,differences=differences,pixel_identical=all(x['changed_pixels']==0 for x in differences.values()))
report=dict(source=pre['source'],kind='MATCHED_AUTHENTICATED_FROZEN_FRAME_PIXEL_COMPARISON',freeze_marker='warp: frozen at tick 330',frame_semantics='Source halts at top of tick330; compare the held last-presented frame, not an asserted rendered tick330. Only post-marker screenshots with nominal time>=ceil(marker)+1; all observed late framebuffers stable within each arm.',preflight_sha256=sha(ev/'current4be-preflight-r1.json'),views=results,all_identical=all(x['pixel_identical'] for x in results.values()),limits='MODELLED Flycast FPS-limited still-only control, explicit root approval; exact source/fixture/programme/track/config identities; scoped visible comparison only, not all-frame actor/runtime-state equality; not arbitrary wall-time pair, motion/performance or physical-console acceptance.')
p=ev/'frozen-look-comparison-explicit-r4.json';assert not p.exists();p.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v['differences'] for k,v in results.items()},indent=2))
if not report['all_identical']:raise SystemExit(1)
