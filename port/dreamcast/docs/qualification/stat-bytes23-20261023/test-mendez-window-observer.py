import importlib.util,pathlib,tempfile
p=pathlib.Path(r'C:\Game Dev\Emulators\codex-lanes\stat-bytes23\mendez-window-observer.py')
spec=importlib.util.spec_from_file_location('mendez_observer',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def row(active,frame,pointer='0x8c123456',header='a'*64):return {'event_active':active,'frame':frame,'pMotion':pointer,'motion_header_sha256':header,'Frame_cnt':frame}
assert not m.summarize([row(True,0),row(True,3),row(False,4)])['normal_event_state_sequence_observed']
assert not m.summarize([row(False,0),row(True,0),row(True,3,header=None),row(False,4)])['normal_event_state_sequence_observed']
assert not m.summarize([row(False,0),row(True,0),row(True,3,pointer='0x8c234567'),row(False,4)])['normal_event_state_sequence_observed']
s=m.summarize([row(False,0),row(True,0),row(True,3),row(False,4)])
assert s['normal_event_state_sequence_observed'] and not s['window_jump_certified']
with tempfile.TemporaryDirectory() as d:
 f=pathlib.Path(d)/'log';tail=m.IncrementalLines(f);assert tail.poll()==[]
 f.write_bytes(b'warp: goto 2 at room fra');assert tail.poll()==[]
 with f.open('ab') as out:out.write(b'me 2050\nnext\nwarp: goto 3')
 lines=tail.poll();assert len(lines)==2 and m.START.search(lines[0]).group(1)=='2050'
 with f.open('ab') as out:out.write(b' at room frame 2300\n')
 lines=tail.poll();assert len(lines)==1 and m.END.search(lines[0])
 assert tail.poll()==[]
 f.write_bytes(b'x')
 try:tail.poll()
 except RuntimeError:pass
 else:raise AssertionError('log truncation not rejected')
print('incremental log and strict event sequence controls PASS; no guest')
