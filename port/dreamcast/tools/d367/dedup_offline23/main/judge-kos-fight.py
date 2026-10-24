from pathlib import Path
import re,json
r=Path(r'C:\Flycast-Evidence\re4-dreamcast\dedup-offline23-20261023')
rows=[]
for k in ('kos0','kos1'):
 p=r/f'gate-{k}-r1'; t=(p/'run-output.txt').read_text(errors='replace'); rr=json.loads((p/'run-result.json').read_text())
 h=[int(x) for x in re.findall(r'kos watch:[^\n]*headroom=(\d+)',t)];top=[int(x) for x in re.findall(r'kos watch:[^\n]*top=(\d+)',t)]
 held=re.findall(r'kos squeeze: held=(\d+)[^\n]*frag=(\d+)',t)
 bad=re.findall(r'^.*(?:Out of memory|MISSING|HALT|FAULT).*$' ,t,re.M)
 row=dict(case=k,emu=rr['emu'],status=rr['status'],seconds=rr['seconds'],min_headroom=min(h) if h else None,min_top=min(top) if top else None,held=held,bad=bad,end_marker='warp: alert at room frame' in t)
 row['pass']=bool(rr['emu']=='console' and rr['status']=='RUN_COMPLETE' and h and min(h)>=4096 and held==[('49152',k[-1])] and not bad and row['end_marker'])
 rows.append(row)
(r/'kos-fight-gate-r1.json').write_text(json.dumps(rows,indent=2)+'\n')
print(json.dumps(rows))
