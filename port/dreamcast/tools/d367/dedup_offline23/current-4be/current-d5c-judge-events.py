from pathlib import Path
import hashlib,json,re
E=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/dedup-offline23-20261023/current-4be08e01')
O=Path('/root/probe/lanes/route/out-dd23cur4be08e01onrT')
S='4be08e0110592510e3630c01fa9f49b3ac2fed3d'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
binding=json.loads((E/'event-reference-binding.json').read_text());assert binding['source']==S and binding['status'].startswith('PASS_')
assert (O/'stack.txt').read_text().strip()==S
base=E/'base-trace-current4be-r1';meta=json.loads((base/'base.json').read_text());assert meta['elf']==str(O/'re4dc-game.elf')
rows={}
for scene,n in [('bell',2866),('mendez',2692)]:
 p=E/(scene+'-on-console-r1');r=json.loads((p/'run-result.json').read_text());b=json.loads((p/'bounded-launch.json').read_text());s=(p/'run-output.txt').read_text(errors='replace')
 assert r['status']=='RUN_COMPLETE' and r['stopped']=='goal' and r['emu']=='console' and not r['errors'] and not b['deadline_fired']
 assert r['tracks']['track03_sha256']==(base/'track03.sha256').read_text().strip()
 for kind,fp in binding['scenes'][scene]['fixtures'].items():assert r['fixtures'][kind]['sha256']==fp['wire_sha256']
 d=json.loads((E/('decisions-'+scene+'-current4be-r1.json')).read_text())
 assert d['verdict']=='MUST-IDENTICAL' and d['compared']==n and d['drift']['player_max']==0 and d['drift']['enemy_max']==0 and d['drift']['slot_id_mismatches']==0
 movies=[]
 for line in s.splitlines():
  if line.startswith('route movie terminal='):
   kv=dict(re.findall(r'(\w+)=([^\s]+)',line));movies.append(kv)
 if scene=='bell':
  m=next(x for x in movies if x['id']=='10130');assert m['terminal']=='1' and m['frames']=='1331/1331'
  assert m['uploaded']==m['presented'];assert int(m['uploaded'])<=1331
 else:
  assert s.count('warp: kill 0x35 hp<=0')==2 and 'phase=enter room=10f' in s
  for mid,nf in [('11f02',1067),('11f10',265),('11f11',321)]:
   m=next(x for x in movies if x['id']==mid);assert m['terminal']=='1' and m['frames']==f'{nf}/{nf}' and int(m['uploaded'])==int(m['presented'])==nf
  returns=[x for x in s.splitlines() if x.startswith('MOVIEARENA return')]
  assert len(returns)==2 and all('restored=1' in x and 'used=363360' in x for x in returns)
 rows[scene]=dict(log_sha256=sha(p/'run-output.txt'),result_sha256=sha(p/'run-result.json'),bounded_sha256=sha(p/'bounded-launch.json'),elapsed_host_s=b['guest_observed_elapsed_s'],track03_sha256=r['tracks']['track03_sha256'],decision_report_sha256=sha(E/('decisions-'+scene+'-current4be-r1.json')),compared_ticks=n,ref_records=d['ref_records'],test_records=d['test_records'],window=d['window'],must_verdict=d['verdict'],drift=d['drift'],movies=movies,moviearena_rows=[x for x in s.splitlines() if x.startswith('MOVIEARENA ')])
out=E/'events-bell-mendez-r1.json';assert not out.exists()
out.write_text(json.dumps(dict(status='PASS_SCOPED_CURRENT_EVENT_DECISIONS',source=S,reference_binding_sha256=sha(E/'event-reference-binding.json'),on_elf_sha256=sha(O/'re4dc-game.elf'),on_resolved_sha256=sha(O/'resolved-knobs.txt'),scenes=rows,limits='Reused qualified OFF reference captures authenticated by freshly linked current OFF main/all14 equality and source/data/fixture bindings. Actual common frame windows only; Mendez current trace has two additional records outside common window. Bell1331 decoded but1318 uploaded/presented (reference1313); do not claim complete movie uploads. Mendez fixture intentionally cancels/skips intro movies11f00/1011f00; required11f02/11f10/11f11 full and two world-loan restores pass. No physical-console or performance acceptance.'),indent=2)+'\n')
print('EVENT_DECISIONS_PASS',[(k,v['compared_ticks']) for k,v in rows.items()])

