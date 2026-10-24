"""Judge current4be normal QA captures; no blanket texture-completeness claim."""
from pathlib import Path
import hashlib,json,re,sys
E=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/dedup-offline23-20261023/current-4be08e01')
arm,kind=sys.argv[1:];assert arm in ('off','on') and kind in ('boot','warp','h2')
p=E/f'qa-{arm}-{kind}-console-r1';s=(p/'run-output.txt').read_text(errors='replace');r=json.loads((p/'run-result.json').read_text());b=json.loads((p/'bounded-launch.json').read_text())
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
m=json.loads((E/'qa-media-r1/pair-media-identity.json').read_text());x=m['arms'][arm]
bad=[l for l in s.splitlines() if re.search(r'\b(?:HALT|FAULT|FATAL|ASSERT)\b|MISSING|DISC READ FAILED|short read|open failed|read failed|BAD-READ|DISCNOTE: (disc: .*(busy|timeout|abort|not accepted|late|did not land|failed|reinit|pio)|snd: stream table (bad|still))',l)]
passed=r['status']=='RUN_COMPLETE' and r['emu']=='console' and r.get('stopped')=='goal' and not r['errors'] and not b['deadline_fired'] and b['guest_exited'] and b['guest_observed_elapsed_s']<=55 and not bad
cfg=(p/'emu.cfg').read_text();passed=passed and 'aica.LimitFPS = no' in cfg
row=dict(source=m['source'],arm=arm,kind=kind,capture=str(p),status='PASS' if passed else 'FAIL',elapsed_host_s=b['guest_observed_elapsed_s'],fault_rows=bad,programme_elf_sha256=x['programme']['elf_sha256'],final_track03_sha256=x['tracks']['track03.bin']['sha256'])
if kind=='boot':
 selected='qa: boot choice /cd/dc/qa/r100.txt' in s and 'phase=enter room=100' in s
 keys=r['key_log'];owned_keys=len(keys)==4 and all(k['windows']>0 for k in keys) and not r.get('keys_pending')
 # Actual final standard GDI via --disc; no low-density fixture redirection.
 assert Path(p/'disc.gdi').read_bytes()==Path(x['path']).joinpath('gdemu/disc.gdi').read_bytes()
 passed=passed and selected and owned_keys and not r['fixtures']
 row.update(media='FINAL_STANDARD_GDI',selected_r100=selected,all4_pid_targeted_steps=owned_keys,key_log=keys)
else:
 proxy=json.loads((E/f'qa-proxy-{arm}-identity-r1.json').read_text())
 assert r['tracks']['track03_sha256']==proxy['track03_sha256']
 row.update(media='SEPARATE_FIXTURE_PROXY_EXACT_FINAL_PROGRAMME_ALL14_DATA',proxy_identity_sha256=sha(E/f'qa-proxy-{arm}-identity-r1.json'),fixtures=r['fixtures'])
 if kind=='warp':
  checks={k:k in s for k in ['qa: auto teleport /cd/dc/qa/r103.txt','warp: qa: preset armed at soft reset','phase=enter room=101','phase=enter room=103']}
  passed=passed and all(checks.values());row['menu_warp_checks']=checks
 else:
  movies=[]
  for mid,n in [('10003',1465),('10020',571),('10030',340)]:
   lines=[l for l in s.splitlines() if 'route movie terminal=1 id='+mid+' ' in l]
   okay=any(f'frames={n}/{n} uploaded={n} presented={n}' in l for l in lines);passed=passed and okay
   movies.extend(lines)
  pos=s.rfind('MOVIEARENA borrow id=10030');restored=pos>=0 and bool(re.search(r'MOVIEARENA return[^\n]*restored=1',s[pos:]))
  hs=re.findall(r'heap_before=(\d+)', '\n'.join(movies));heap=int(hs[-1]) if hs else 0
  passed=passed and restored and heap>0;row.update(movies=movies,restored=restored,heap_before=heap,limits='Normal QA heap, separate from standard memory gate; no blanket actor/texture completeness or physical/performance claim.')
row['status']='PASS' if passed else 'FAIL';row['sha256']={n:sha(p/n) for n in ['run-result.json','bounded-launch.json','run-output.txt','serial.txt','emu.cfg','disc.gdi']}
out=p/'qa-gate.json';assert not out.exists();out.write_text(json.dumps(row,indent=2)+'\n')
print(json.dumps({k:v for k,v in row.items() if k not in ['sha256','key_log']},indent=2));assert passed,row

