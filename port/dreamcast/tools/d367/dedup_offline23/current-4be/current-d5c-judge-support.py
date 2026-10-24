from pathlib import Path
import hashlib,json,re
E=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/dedup-offline23-20261023/current-4be08e01')
O=Path('/root/probe/lanes/route')
S='4be08e0110592510e3630c01fa9f49b3ac2fed3d'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
bad=re.compile(r'MISSING|DISC READ FAILED|short read|open failed|read failed|BAD-READ|DISCNOTE: (disc: .*(busy|timeout|abort|not accepted|late|did not land|failed|reinit|pio)|snd: stream table (bad|still))')
def capture(name,base):
 p=E/name;r=json.loads((p/'run-result.json').read_text());b=json.loads((p/'bounded-launch.json').read_text());s=(p/'run-output.txt').read_text(errors='replace')
 assert r['status']=='RUN_COMPLETE' and r['emu']=='console' and not r['errors'] and not b['deadline_fired']
 assert r['tracks']['track03_sha256']==(E/base/'track03.sha256').read_text().strip()
 assert not bad.search(s),name
 return p,r,s,dict(log_sha256=sha(p/'run-output.txt'),result_sha256=sha(p/'run-result.json'),bounded_sha256=sha(p/'bounded-launch.json'),elapsed_host_s=b['guest_observed_elapsed_s'],track03_sha256=r['tracks']['track03_sha256'])
diag=O/'out-fpdd23cur4be08e01diagW'
assert (diag/'stack.txt').read_text().strip()==S
kn=(diag/'resolved-knobs.txt').read_text()
for k in ['KOS_WATCH','KOS_SQUEEZE','MCHECK_LEONGC','NATIVE_MODEL_REGISTRY_CENSUS','TEX_CHECK','VRAM_ROOM_LOG']:
 assert re.search(r'(?m)^'+k+r'=1$',kn),k
rows={}
fields=['refusals','guard','guard_p','nocontig','latched','absent','gc_fx','dropped','fx_dropped','tex_rej','snd_fail']
for room in ['r100','r101','r103']:
 p,r,s,pins=capture('cg-'+room+'-console-r1','base-diag-current4be-r1')
 expected=room[1:]
 rooms=[dict(re.findall(r'(\w+)=(\w+)',x)) for x in s.splitlines() if x.startswith('vram room:') and 'r='+expected+' ' in x]
 gaps=[dict(re.findall(r'(\w+)=(\w+)',x)) for x in s.splitlines() if x.startswith('vram gaps:') and 'r='+expected+' ' in x]
 assert rooms and gaps
 for g in gaps:
  for k in fields:assert k in g and int(g[k])==0,(room,k,g)
 # Allocator fragmentation retries are telemetry, not I/O retries or refusals.
 tex=[dict(re.findall(r'(\w+)=(\d+)',x)) for x in s.splitlines() if x.startswith('texchk: frame=')]
 assert tex and all(all(int(x[k])==0 for k in ['fails','meta_changes','vram_changes']) for x in tex)
 assert 'LEON-GC PASS' in (E/('leongc-'+room+'-r1.txt')).read_text()
 dedup=[x for x in s.splitlines() if x.startswith('SCNDEDUP3 room='+expected+' ')]
 assert dedup and all('extra_heap=0 ' in x for x in dedup)
 rows[room]=dict(**pins,vram_room_rows=len(rooms),vram_gap_rows=len(gaps),min_free=min(int(x['free']) for x in rooms),min_largest=min(int(x['largest']) for x in rooms),zero_vram_fields=fields,max_allocator_retries=max(int(x['retries']) for x in rooms),max_evicted=max(int(x['evicted']) for x in rooms),texture_summary_rows=len(tex),dedup_rows=dedup,leongc_report_sha256=sha(E/('leongc-'+room+'-r1.txt')))
assert 'TEXCHK PASS (5/5 logs pass)' in (E/'texchk-r1.txt').read_text()
cast=(E/'castgc-r1.txt').read_text()
assert 'PASS' in cast and 'FAIL' not in cast
p,r,s,g=capture('gdemu1-console-r1','base-standard-current4be-on-r1')
assert r['stopped']=='goal' and 'phase=enter room=103' in s
assert r['emu_env']=={'RE4DC_GD_JITTER':'20000','RE4DC_GD_PROFILE':'gdemu','RE4DC_GD_SEED':'1'}
serial=(p/'serial.txt').read_text(errors='replace');profile=serial.splitlines()[0]
assert 'profile=gdemu ' in profile and 'jitter=20000 ' in profile and 'seed=1' in profile
race=[x for x in serial.splitlines() if re.search(r'earlyStat=[1-9]\d* landedAfterStat=[1-9]\d*',x)]
assert race
report=dict(status='PASS_SCOPED_CURRENT_CENSUS_TEXTURE_VRAM_GDEMU',source=S,diagnostic_resolved_knobs_sha256=sha(diag/'resolved-knobs.txt'),diagnostic_elf_sha256=sha(diag/'re4dc-game.elf'),rooms=rows,cast_gc_report_sha256=sha(E/'castgc-r1.json'),texchk_report_sha256=sha(E/'texchk-r1.txt'),gdemu=dict(**g,profile=profile,serial_sha256=sha(p/'serial.txt'),race_hit_rows=len(race),endpoint='phase=enter room=103'),limits='Actual enabled diagnostic capture and observed r100/r101/r103 consumers only; r103 em12 CROWD-SKIP0 not-drawn census row is not actor draw proof. r100 has allocator fragmentation retries (native_ui.cpp:3094,3595), explicitly reported, not zero-retry acceptance. No all-actor coverage, physical-console or performance acceptance.')
out=E/'support-census-vram-gdemu-r1.json';assert not out.exists();out.write_text(json.dumps(report,indent=2)+'\n');print(report['status'],{k:(v['min_free'],v['min_largest']) for k,v in rows.items()},'GD races',len(race))

