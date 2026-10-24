"""Offline r117 normal-solve source-state witness. No guests, writes to inputs or fabricated success."""
import argparse,hashlib,json,pathlib,re

def judge(text):
 baseline=False;started=False;rows=[];solved=[]
 for line in text.splitlines():
  m=re.search(r'warp: flags applied rsf\[117\]=([0-9a-fA-F]{8})',line)
  if m:baseline=not(int(m[1],16)&0x40000000)
  m=re.search(r'warp: frame (\d+) room=117 pl=(-?\d+),(-?\d+),(-?\d+) status1=([0-9a-fA-F]{8}) rsf=([0-9a-fA-F]{8})',line)
  if not m:continue
  frame=int(m[1]);pos=list(map(int,m.group(2,3,4)));sf1=int(m[5],16);rsf=int(m[6],16)
  if baseline and rsf&0x20000000:started=True
  row={'frame':frame,'pos':pos,'status1':f'{sf1:08x}','rsf':f'{rsf:08x}'};rows.append(row)
  if baseline and started and (rsf&0x60000000)==0x40000000 and not(sf1&0x10000000) and abs(pos[0]+2910)<100 and abs(pos[1]-4000)<100 and abs(pos[2]-6610)<100:solved.append(row)
 faults=re.findall(r'\b(?:HALT|FAULT|ASSERT(?:ION)?|Out of memory)\b',text,re.I)
 return {'baseline_unsolved_observed':baseline,'mechanism_started_observed':started,'solved_disarmed_event_clear_endpose_observed':bool(solved),'source_state_witness_pass':bool(baseline and started and solved and not faults),'fault_tokens':faults,'final_witness':solved[-1] if solved else None,'sample_rows':len(rows),'limits':'Not a beam-allocation-failure injection, rendered-light fidelity, continued-play STRICT or physical-console gate. Bind exact programme/data/fixture hashes separately.'}
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('log',type=pathlib.Path);ap.add_argument('--out',type=pathlib.Path);a=ap.parse_args()
 raw=a.log.read_bytes();r=judge(raw.decode('ascii','replace'));r['log_sha256']=hashlib.sha256(raw).hexdigest();s=json.dumps(r,indent=2)+'\n'
 if a.out:
  with a.out.open('x') as f:f.write(s)
 print(s,end='');raise SystemExit(0 if r['source_state_witness_pass'] else 1)
