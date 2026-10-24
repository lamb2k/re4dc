from pathlib import Path
import hashlib,importlib.util,json,re,struct

e=Path(r'C:\Flycast-Evidence\re4-dreamcast\dedup-offline23-20261023\restrip23-fb254\root-forest-camera-v2')
c=e/'capture-r2'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=Path(r'\\wsl.localhost\Ubuntu-24.04\root\work\lanes\camera-log24\port\dreamcast\tools\d367\camera_log24\camera_log_v2.py')
spec=importlib.util.spec_from_file_location('camera_v2',p);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
run=json.loads((c/'run-result.json').read_text());bound=json.loads((c/'bounded-launch.json').read_text());held=json.loads((c/'freeze800-capture.json').read_text())
assert run['status']=='RUN_COMPLETE' and run['emu']=='console' and run['stopped']=='goal' and not run['errors']
assert run['stop']=='warp: frozen at tick 800' and run['stop_matched_s'] is not None
assert not bound['deadline_fired'] and bound['guest_exited'] and 0<bound['guest_observed_elapsed_s']<=55
assert bound['expected_executable_sha256']=='8e6c49871013c25b1a1c77c789167e3aaed8193e828adb7e2bbce9248d2add4a'
assert held['capture_completed'] and held['expected_room']=='100' and held['marker']['tick']==800 and not held['errors'] and all(held['buffer_stable_between_reads'])
assert held['config_matches_prelaunch'] and sha(c/'emu.cfg')==held['actual_config_sha256']==held['actual_config_final_sha256']
assert re.findall(r'(?mi)^aica\.LimitFPS\s*=\s*(.*?)\s*$',(c/'emu.cfg').read_text())==['yes']
raw=(c/'run-output.txt').read_bytes();records=re.findall(rb'PS2CAM2 [^\r\n]*(?:\r\n|\n)',raw)
assert records and raw.count(b'PS2CAM2 ')==len(records),'Unframed or partial row'
parsed={}
for rawrow in records:
    line=rawrow.decode('ascii').replace('\r\n','\n')
    assert len(line.encode('ascii'))==251
    row=mod.parse(line)
    assert row['frame'] not in parsed,'Duplicate camera frame'
    parsed[row['frame']]=row
frames=list(range(500,795,7));assert len(frames)==43 and all(f in parsed for f in frames)
selected=[parsed[f] for f in frames]
for row in selected:
    values=[row['far_bits']]+row['view_bits']+row['projection_bits']+row['viewport_bits']
    floats=[struct.unpack('<f',struct.pack('<I',x))[0] for x in values]
    assert all(abs(x)<float('inf') for x in floats)
    assert row['viewport_bits'][:2]==[0,0]
    assert floats[-4]>0 and floats[-3]>0
legacy=''.join(mod.legacy_line(row) for row in selected)
out=e/'FOREST-CAMERA-DERIVED-LEGACY.txt';out.write_text(legacy,newline='\n')
(e/'FOREST-CAMERA-V2-RAW-RECORDS.txt').write_bytes(b''.join(records))
pins={str(p.relative_to(e)):dict(bytes=p.stat().st_size,sha256=sha(p)) for p in [c/'run-output.txt',c/'run-result.json',c/'bounded-launch.json',c/'freeze800-capture.json',c/'emu.cfg',e/'PROGRAMME-PINS.json',e/'BASE-BINDING.json',out,e/'FOREST-CAMERA-V2-RAW-RECORDS.txt']}
for picture in held['images']:
    image=c/picture['path'];assert sha(image)==picture['sha256'];pins[str(image.relative_to(e))]=dict(bytes=image.stat().st_size,sha256=sha(image))
result=dict(status='PASS_COMPLETE_CAMERA_FOR_OFFLINE_MODEL',source='c2f0d82e95050a708d0b977f94fad34890cbc279',source_parser_sha256=sha(p),actual_guest_pid=bound['pid'],actual_guest_elapsed_seconds=bound['guest_observed_elapsed_s'],room='100',fixture='bf-r100-forest',freeze_tick=800,actual_logged_frame_range=[min(parsed),max(parsed)],complete_rows=len(parsed),selected_frames=frames,selected_rows=len(selected),legacy_derivation='Exact field expansion from 27 complete v2 words; only CRLF transport is normalized. No missing bits inferred.',all_six_viewport_words_authentic=True,far_f32=struct.unpack('<f',struct.pack('<I',selected[0]['far_bits']))[0],scope='Current source camera-only PVS2/batch0 diagnostic. Full logged camera tuples for offline calculations; held screenshots show forest, Leon and HUD, not a sampled full runtime state or hardware/performance acceptance.',root_visual_check='Both first buffer PNGs viewed: correct forest, Leon, HUD; no loading screen or watchdog overlay. Stable between two reads.',pins=pins)
(e/'CAMERA-ADMISSION.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='pins'},indent=2))
