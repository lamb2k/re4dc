from pathlib import Path
import json,hashlib,subprocess
source='4be08e0110592510e3630c01fa9f49b3ac2fed3d'
ev=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/dedup-offline23-20261023/current-4be08e01')
ref=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/audits23-takeover/5e4de9a0')
tree=Path('/root/work/lanes/dedup-offline23-current-d5c')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
identity=json.loads((ev/'current-off-trace-identity.json').read_text());assert identity['source']==source and identity['status'].startswith('PASS')
programme=identity['programmes']['reference'];base=ref/'_discs/on-t';meta=json.loads((base/'base.json').read_text())
assert meta['elf']==programme['path']+'/re4dc-game.elf'
a=json.loads((base/'base-manifest.json').read_text());b=json.loads(Path('/root/work/lanes/dedup-offline23-current-d5c-scratch/standard/off/manifest.json').read_text())
allowed={'1ST_READ.BIN','dc/warp.txt','dc/padscript.txt','dc/w11.txt'}|{'dc/'+n for n in programme['overlays']}
different={n for n in a.keys()|b.keys() if a.get(n,{}).get('sha256')!=b.get(n,{}).get('sha256')}
assert not different-allowed,sorted(different-allowed)
assert a['1ST_READ.BIN']['sha256']==programme['raw_sha256']
for n,h in programme['overlays'].items():assert a['dc/'+n]['sha256']==h
fixtures={'bell':dict(warp=tree/'port/dreamcast/tools/d367/fullplay/segments/bell-trg-warp.txt'),
'mendez':dict(warp=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/stat-bytes23-20261023/mendez-bounded-itemack-r3/mendez-bounded-warp.txt'),pad=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/stat-bytes23-20261023/mendez-bounded-itemack-r3/mendez-bounded-pad.txt'))}
rows={}
for scene,fs in fixtures.items():
    cap=ref/('decisions-'+scene+'-on-r1');r=json.loads((cap/'run-result.json').read_text());bound=json.loads((cap/'bounded-launch.json').read_text())
    assert r['status']=='RUN_COMPLETE' and r['stopped']=='goal' and not r['errors'] and r['emu']=='console' and not bound['deadline_fired']
    assert r['tracks']['track03_sha256']==(base/'track03.sha256').read_text().strip()
    pins={}
    for kind,p in fs.items():
        wire=p.read_bytes().replace(b'\r',b'')
        assert r['fixtures'][kind]['sha256']==hashlib.sha256(wire).hexdigest()
        assert (cap/('fixture-'+kind+'.txt')).read_bytes().replace(b'\r',b'')==wire
        pins[kind]=dict(path=str(p),source_sha256=sha(p),wire_sha256=hashlib.sha256(wire).hexdigest())
    rows[scene]=dict(reference_capture=str(cap),log_sha256=sha(cap/'run-output.txt'),result_sha256=sha(cap/'run-result.json'),bounded_sha256=sha(cap/'bounded-launch.json'),fixtures=pins)
report=dict(status='PASS_REUSED_EVENT_REFERENCE_PROGRAMME_DATA_FIXTURE_BINDING',source=source,reference_source='5e4de9a0262d3629c9833c959557de198b2e9f0c',current_off_trace_identity_sha256=sha(ev/'current-off-trace-identity.json'),reference_manifest_sha256=sha(base/'base-manifest.json'),current_standard_off_manifest_sha256=sha(Path('/root/work/lanes/dedup-offline23-current-d5c-scratch/standard/off/manifest.json')),nonprogramme_data_equal=True,excluded_hot_fixture_paths=['dc/warp.txt','dc/padscript.txt','dc/w11.txt'],actual_capture_fixtures_explicitly_bound=True,scenes=rows,limits='Reused qualified actual baseline captures, not fresh OFF guests; currentOFF trace main/all14 freshly linked byte-identical and sourceprogramme/data/fixture identities established.')
p=ev/'event-reference-binding.json';assert not p.exists();p.write_text(json.dumps(report,indent=2)+'\n')
print('REUSED_REFERENCE_BINDING_PASS',list(rows))
