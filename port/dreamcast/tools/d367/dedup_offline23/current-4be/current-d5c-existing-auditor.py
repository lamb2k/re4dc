from pathlib import Path
import json,subprocess,sys
root=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/dedup-offline23-20261023/current-4be08e01');pre=json.loads((root/'current4be-preflight-r1.json').read_text())
auditor=Path('/root/work/lanes/dedup-offline23/port/dreamcast/tools/d367/dedup_offline23/audit_evidence.py')
fixture=Path(pre['tools']['fullplay/segments/h2-warp.txt']['path']);fsha=pre['tools']['fullplay/segments/h2-warp.txt']['sha256'];plans=root/'current4be-programme-pins-r1.json'
for arm in ('off','on'):
 base=root/('base-standard-current4be-'+arm+'-r1');cap=root/('h2-'+arm+'-console-r1');out=root/('audit-current-h2-'+arm+'-r1.json')
 subprocess.run([sys.executable,str(auditor),'--capture',str(cap),'--program-plan',str(plans),'--arm',arm,'--fixture',str(fixture),'--fixture-sha256',fsha,'--base-json',str(base/'base.json'),'--track-sha256',(base/'track03.sha256').read_text().strip(),'--expected-emu','console','--output',str(out)],check=True)
 r=json.loads(out.read_text());assert not r['identity_errors'];assert not r['warnings'];assert r['observations']['faults']['count']==0
 print(arm,'identity_errors',r['identity_errors'],'faults',r['observations']['faults']['count'],'screenshot_count',r['screenshot_count'],'pixel_identity',r['observations']['pixel_identity'])
 print('diagnostic_sections', {k:r['observations'][k].get('status','rows-only') if isinstance(r['observations'][k],dict) else len(r['observations'][k]) for k in ('kos','texchk','cast_gc','leon_gc','vram')})