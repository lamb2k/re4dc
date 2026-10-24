import importlib.util,pathlib
p=pathlib.Path(__file__).with_name('judge-r117-solve.py');s=importlib.util.spec_from_file_location('judge',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
base='warp: flags applied rsf[117]=00000000\n'
started='warp: frame 300 room=117 pl=-2910,4000,6610 status1=10000000 rsf=31100000\n'
end='warp: frame 1800 room=117 pl=-2910,4000,6610 status1=00000000 rsf=51104820\n'
assert m.judge(base+started+end)['source_state_witness_pass']
for text in [base,base+end,'warp: flags applied rsf[117]=40000000\n'+started+end,base+started+end.replace('status1=00000000','status1=10000000'),base+started+end.replace('-2910,4000,6610','169,-1000,6073'),base+started+end+'HALT test\n']:
 assert not m.judge(text)['source_state_witness_pass']
fixture=pathlib.Path(__file__).with_name('r117-light-solve-pad.txt').read_text();entries=[s.split('#')[0].split() for s in fixture.splitlines() if s.split('#')[0].strip()]
assert len(entries)<=64 and len(fixture.encode())<4095
assert all(int(v[1],16) in [0,0x100,0x200,6] for v in entries)
for name in ['r117-light-solve-warp.txt','r10c-first-villager-warp.txt']:
 lines=[s.split('#')[0].strip().split() for s in pathlib.Path(__file__).with_name(name).read_text().splitlines() if s.split('#')[0].strip()]
 assert not any(v[0] in ['rsf','find','status','scenario','unlock','kill','trg'] for v in lines)
print('source-state witness negatives and fixture bounds/no-completion-pokes PASS; no guest')
