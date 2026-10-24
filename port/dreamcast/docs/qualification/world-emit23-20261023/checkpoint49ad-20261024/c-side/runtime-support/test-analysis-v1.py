import copy,importlib.util,json,pathlib,re,shutil,tempfile
p=pathlib.Path('/mnt/c/Game Dev/Emulators/codex-lanes/world-emit23/runtime-support/analyse-meter-v1.py')
s=importlib.util.spec_from_file_location('meter',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
src=pathlib.Path('/mnt/c/Flycast-Evidence/re4-dreamcast/world-emit23-takeover/7a3af776');arm='E';scene='b1'
with tempfile.TemporaryDirectory(prefix='worldemit-analyser-',dir='/dev/shm') as tmp:
 root=pathlib.Path(tmp);cap=root/'runtime-support/E-m-b1-q1';cap.mkdir(parents=True);(root/'identities').mkdir()
 for name in ['run-output.txt','bounded-launch.json','run-result.json','fixture-warp.txt']:shutil.copy2(src/'runtime-support/E-m-b1-q1'/name,cap/name)
 (cap/'flycast.exe').symlink_to(src/'runtime-support/E-m-b1-q1/flycast.exe')
 for name in ['E-m-resolved-knobs.txt','E-m-stack.txt']:shutil.copy2(src/'identities'/name,root/'identities'/name)
 baseline={p:p.read_bytes() for p in [cap/'run-output.txt',cap/'bounded-launch.json',cap/'run-result.json',root/'identities/E-m-resolved-knobs.txt']}
 assert len(m.inspect(root,arm,scene)['windows'])==13
 cases={
 'wrong-runtime-lod':lambda: (cap/'run-output.txt').write_text((cap/'run-output.txt').read_text().replace('lod_px=5','lod_px=4')),
 'wrong-room':lambda:(cap/'run-output.txt').write_text((cap/'run-output.txt').read_text().replace('warp: start room=101 next_room=101 ','warp: start room=100 next_room=100 ')),
 'census-in-timing':lambda:(cap/'run-output.txt').write_text((cap/'run-output.txt').read_text()+'\nWEC23 BEGIN f=1200 room=101 threshold=1200\n'),
 'missing-wrapped-field':lambda:(cap/'run-output.txt').write_text(re.sub(r' cpu=\d+/\d+','',(cap/'run-output.txt').read_text())),
 'overrun-guard':lambda:(cap/'bounded-launch.json').write_text(json.dumps(dict(json.loads((cap/'bounded-launch.json').read_text()),deadline_fired=True))),
 'bad-meter-knob':lambda:(root/'identities/E-m-resolved-knobs.txt').write_text((root/'identities/E-m-resolved-knobs.txt').read_text().replace('SCENERY_EMIT_CENSUS=0','SCENERY_EMIT_CENSUS=1200')),
 }
 for name,mutate in cases.items():
  for p,data in baseline.items():p.write_bytes(data)
  mutate()
  try:m.inspect(root,arm,scene)
  except AssertionError:print('REJECT',name)
  else:raise AssertionError('accepted mutation '+name)
 print('PASS actual-log positive and six refusal controls; RAM-only fixtures')