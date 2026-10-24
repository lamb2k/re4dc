#!/usr/bin/env python3
import hashlib,json,pathlib,re,subprocess
T=pathlib.Path('/root/work/lanes/audits23-target-on');D=T/'port/dreamcast/tools/d367';E=pathlib.Path('/mnt/c/Flycast-Evidence/re4-dreamcast/audits23-takeover/5e4de9a0');C=E/'census-on'
BASELINE=pathlib.Path('/mnt/c/Flycast-Evidence/re4-dreamcast/stat-bytes23/takeover-2a14662d/census-on');receipt=json.loads((C/'receipt.json').read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def txt(p):return p.read_text(errors='replace').replace('\0','') if p.exists() else ''
def tool(cmd,out):
 files=[(x,sha(pathlib.Path(x))) for x in cmd if pathlib.Path(x).is_file() and pathlib.Path(x).suffix!='.json']
 files += [(str(D/p),sha(D/p)) for p in ['castgc/allow.tsv','castgc/notdrawn-allow.tsv']]
 fingerprint=hashlib.sha256(json.dumps([cmd,files],sort_keys=True).encode()).hexdigest()
 meta=out.with_name(out.name+'.receipt.json')
 if out.exists() and meta.exists():
  old=json.loads(meta.read_text())
  if old['fingerprint']==fingerprint and old['result']['sha256']==sha(out):return old['result']
 p=subprocess.run(cmd,text=True,capture_output=True);out.write_text(p.stdout+p.stderr)
 result={'rc':p.returncode,'output':str(out),'sha256':sha(out),'summary':(p.stdout+p.stderr).splitlines()[-5:]}
 meta.write_text(json.dumps({'fingerprint':fingerprint,'result':result},indent=2)+'\n')
 return result
def inspect(r,root):
 cap=root/f'cg-{r}';log=cap/'run-output.txt';text=txt(log);room=int(r[1:],16)
 nm=[m.groupdict() for m in re.finditer(r'NMRS f=(?P<f>\d+) room=(?P<room>[0-9a-f]+) id=(?P<id>[0-9a-f]+)[^\n]*?native=(?P<native>\d+) crowd=(?P<crowd>\d+)',text) if int(m['room'],16)==room]
 critical=[l for l in text.splitlines() if re.search(r'HALT|FAULT|RE4DC MISSING|Out of memory|\[LOG OVERRUN',l)]
 entry=bool(re.search(r'warp: room enter 0*'+r[1:]+r'\b',text))
 memories=[l for l in text.splitlines() if any(v in l for v in ['room lifecycle:','native UI VRAM:','w11 census:','koswatch:'])]
 return {'room':r,'log':str(log),'log_sha256':sha(log) if log.exists() else None,'entered':entry,'target_nmrs_rows':len(nm),'target_draw_rows':sum(int(m['native'])+int(m['crowd'])>0 for m in nm),'target_max_nmrs_frame':max([int(m['f']) for m in nm],default=None),'critical':critical,'no_contiguous':text.count('no contiguous'),'room_memory_entry':re.findall(r'room lifecycle: phase=enter room=0*'+r[1:]+r'\b[^\n]*',text),'native_ui_vram_rows':sum('native UI VRAM:' in l for l in memories),'memory_rows':len(memories),'heap_check_bad':[l for l in memories if 'heap_check=' in l and 'heap_check=ok' not in l],'memory_tail':memories[-8:],'texchk_lines':[l for l in text.splitlines() if 'TEXCHK' in l][-8:]}
rows=[]
for r in receipt['rooms']:
 cap=C/f'cg-{r}';log=cap/'run-output.txt';row=inspect(r,C)
 row['capture']=json.loads((cap/'run-result.json').read_text()) if (cap/'run-result.json').exists() else None
 row['bounded']=json.loads((cap/'bounded-launch.json').read_text()) if (cap/'bounded-launch.json').exists() else None
 row['screenshots']=[{'path':str(p),'sha256':sha(p),'bytes':p.stat().st_size} for p in cap.glob('shots/**/*.png')]
 row['tools']={}
 for key,cmd in [('castgc',['python3',str(D/'cast_gc.py'),str(log),'--not-drawn','--label','audits23-on-'+r,'--json',str(cap/'castgc.json')]),('leongc',['python3',str(D/'mcheck/leongc_check.py'),str(log)]),('texchk',['bash',str(D/'texchk/texchk.sh'),str(log)])]:
  row['tools'][key]=tool(cmd,cap/(key+'.txt'))
 row['baseline']=inspect(r,BASELINE) if (BASELINE/f'cg-{r}'/'run-output.txt').exists() else None
 row['pass']=all([row['entered'],row['target_nmrs_rows']>0,row['target_draw_rows']>0,not row['critical'],row['no_contiguous']==0,row['memory_rows']>0,bool(row['room_memory_entry']),row['native_ui_vram_rows']>0,not row['heap_check_bad'],bool(row['screenshots']),row['capture'] and row['capture']['status']=='RUN_COMPLETE' and not row['capture']['errors'],row['bounded'] and not row['bounded']['deadline_fired'] and row['bounded']['guest_exited'],all(x['rc']==0 for x in row['tools'].values())])
 rows.append(row)
logs=[str(C/f'cg-{r}'/'run-output.txt') for r in receipt['rooms']]
agg={}
agg['castgc']=tool(['python3',str(D/'cast_gc.py'),*logs,'--not-drawn','--label','audits23-on','--json',str(C/'castgc.json')],C/'castgc.txt')
agg['leongc']=tool(['python3',str(D/'mcheck/leongc_check.py'),*logs],C/'leongc.txt')
agg['texchk']=tool(['bash',str(D/'texchk/texchk.sh'),*logs],C/'texchk.txt')
result={'source':receipt['source'],'evidence_kind':'Flycast console regression, not hardware or performance','baseline_source':'2a14662d4b025031cd93f64eed6a5d8159d473b7','baseline_only':False,'rooms':rows,'aggregate':agg,'pass_rooms':sum(x['pass'] for x in rows),'total_rooms':len(rows),'tool_sha256':{str(D/p):sha(D/p) for p in ['cast_gc.py','mcheck/leongc_check.py','texchk/texchk.sh','texchk/texchk.py','castgc/allow.tsv','castgc/notdrawn-allow.tsv']}}
(C/'results.json').write_text(json.dumps(result,indent=2)+'\n')
for r in rows:print(r['room'],'PASS' if r['pass'] else 'FAIL/INCOMPLETE','entry',r['entered'],'nmrs',r['target_nmrs_rows'],'draw',r['target_draw_rows'],'critical',len(r['critical']),'contig',r['no_contiguous'],'shots',len(r['screenshots']),'tools',{k:v['rc'] for k,v in r['tools'].items()})
print('TOTAL',result['pass_rooms'],'/',result['total_rooms'])
