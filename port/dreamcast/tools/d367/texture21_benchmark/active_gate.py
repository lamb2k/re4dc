#!/usr/bin/env python3
"""C-only active-camera/freeplay gate; raw CPU rows are not a B/C speedup."""
import argparse,hashlib,json,math,re
from pathlib import Path

def camera_valid(row):
 if not row.get('camera_scope','').startswith('active pG->Cam'):return False,'active camera scope absent'
 p=row.get('pose',{});v=p.get('camera_view',[]);q=p.get('camera_projection',[]);par=p.get('camera_param',[])
 if len(v)!=12 or len(q)!=16 or len(par)!=8 or not all(math.isfinite(x) for x in v+q+par):return False,'missing/nonfinite camera'
 if not 0<par[7]<180:return False,'invalid active fov'
 basis=[v[i:i+3] for i in (0,4,8)]
 if any(abs(sum(x*x for x in b)-1)>.005 for b in basis):return False,'view basis not normalized'
 if any(abs(sum(basis[i][k]*basis[j][k] for k in range(3)))>.005 for i,j in ((0,1),(0,2),(1,2))):return False,'view basis not orthogonal'
 cot=1/math.tan(math.radians(par[7]/2))
 if abs(q[0]-cot/1.3333334)>1e-3 or abs(q[5]-cot)>1e-3 or abs(q[14]+1)>1e-6 or abs(q[15])>1e-6:return False,'projection does not match source perspective/fov'
 if max(abs(sum(basis[i][k]*par[k] for k in range(3))+v[4*i+3]) for i in range(3))>.25:return False,'view translation inconsistent with active camera position'
 return True,'active finite source perspective and look-at matrix'

def phases(text):
 windows={}
 for number,line in enumerate(text.splitlines(),1):
  m=re.match(r'PT f=(\d+)-(\d+)(?: n=(\d+))? (.*)',line)
  if not m:continue
  start,end=int(m[1]),int(m[2]);w=windows.setdefault((start,end),{'source_window':[start,end],'lines':[],'fields':{}});w['lines'].append(number)
  if m[3]:w['n']=int(m[3])
  for tag,avg,maxv,count in re.findall(r'(\S+)=(\d+)/(\d+)(?:/(\d+))?',m[4]):
   w['fields'][tag]=({'hits':int(avg),'misses':int(maxv),'units':'cache counts'} if tag=='rotcache' else {'mean_us':int(avg),'max_us':int(maxv),'units':'microseconds'})
   w['fields'][tag]['count']=int(count) if count else None
 for w in windows.values():
  n=w.get('n',0);w['freeplay_loop_complete']=n==60 and all(tag in w['fields'] and (w['fields'][tag]['count'] in (None,n)) for tag in ('Player','ObjMgr.move','CameraMove'))
 return list(windows.values())

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--cap',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
 raw=[json.loads(l) for l in (a.cap/'typed-observer.jsonl').read_text().splitlines()];accepted={};rejected={};witnesses=0
 for line,r in enumerate(raw,1):
  if r.get('event')!='sample' or r.get('room_id')!=0x103:continue
  good,reason=camera_valid(r)
  if not good:rejected[reason]=rejected.get(reason,0)+1;continue
  accepted.setdefault(r['source_tick'],[]).append({'line':line,'camera_scope':r['camera_scope'],'pose':r['pose'],'life_raw':r['life_raw'],'drive_nonmusic':r['drive_nonmusic']})
  witnesses+=int('minimum_header_witness' in r)
 windows=phases((a.cap/'run-output.txt').read_text(errors='replace'));wanted=[w for w in windows if w['source_window'] in ([241,300],[301,360])];gate=bool(len(wanted)==2 and all(w['freeplay_loop_complete'] for w in wanted) and all(k in accepted for k in (240,241,300,301,360)))
 report={'scope':'C03 ACTIVE/freeplay qualification; no B/C speedup, no direct phase-flag capture, no exact presentation binding','active_camera_frames':{'first':min(accepted) if accepted else None,'last':max(accepted) if accepted else None,'unique_source_ticks':len(accepted)},'camera_rejections':rejected,'phase_source':'Frozen src/game/game.cpp: Player/ObjMgr.move/CameraMove stamps only in gameMainLoop (Rno0==3); tick_log.cpp third count omitted only when label count equals entire block n','postload_windows':wanted,'C_active_camera_freeplay_gate':gate,'predeclared_possible_comparison_window':[241,360],'target_ticks_observed':len(set(accepted)&set(range(241,361))),'boundary_samples':{str(k):accepted.get(k,[]) for k in (240,241,300,301,360)},'minimum_header_witnesses_in_active_samples':witnesses,'input_sha256':{n:hashlib.sha256((a.cap/n).read_bytes()).hexdigest() for n in ('typed-observer.jsonl','typed-observer-summary.json','run-output.txt')},'remaining_B_gate':'Same source/program/overlays/gameplay/input, strict active camera/player/health equality at matched source boundaries; coherent drive edges; source/phase windows must match. Any missing/mismatch keeps comparison pending.'}
 with a.out.open('x') as f:json.dump(report,f,indent=2);f.write('\n')
 print(json.dumps({k:report[k] for k in ('C_active_camera_freeplay_gate','active_camera_frames','camera_rejections','target_ticks_observed')}))
if __name__=='__main__':main()
