from pathlib import Path
import json
r=Path('/root/work/lanes/dedup-offline23-current-d5c-scratch/standard');ev=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/dedup-offline23-20261023/current-4be08e01')
a=json.loads((r/'off/manifest.json').read_text());b=json.loads((r/'on/manifest.json').read_text())
diff={n:{'off':a.get(n),'on':b.get(n)} for n in a.keys()|b.keys() if a.get(n,{}).get('sha256')!=b.get(n,{}).get('sha256')}
allowed={'1ST_READ.BIN','dc/native/r100/ps2-dd3.re4mesh','dc/native/r101/ps2-dd3.re4mesh','dc/native/r103/ps2-dd3.re4mesh','dc/native/r101/ps2-dd3.r4sg'}
pre=json.loads((ev/'current4be-preflight-r1.json').read_text())
for name in pre['programs']['off']['overlays']:
 allowed.add('dc/'+name)
 assert a['dc/'+name]['sha256']==pre['programs']['off']['overlays'][name]['sha256']
 assert b['dc/'+name]['sha256']==pre['programs']['on']['overlays'][name]['sha256']
assert not (set(diff)-allowed),set(diff)-allowed
(ev/'current4be-matched-data-r1.json').write_text(json.dumps({'status':'MATCHED_FRESH_DATA_ONLY_PROGRAMMES_AND4_ALT_DIFFER','source':'4be08e0110592510e3630c01fa9f49b3ac2fed3d','different_paths':diff,'data29_same':True,'programme_overlay_differences_expected_and_pinned':True},indent=2)+'\n')
print('FULL_FRESH_DATA_DIFF_ONLY_PROGRAMMES_AND4_ALT',len(diff))