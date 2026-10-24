"""Bounded original KOS48 semantic gate; capture completion is a separate fact."""
from pathlib import Path
import re
WATCH=re.compile(r'kos watch: frame=(\d+) free=(\d+) used=(\d+) break=(\d+) headroom=(\d+) min=(\d+) top=(\d+) holes=(\d+)')
SQUEEZE=re.compile(r'kos squeeze: held=(\d+) requested=(\d+) frag=(\d+) pieces=(\d+)')
def judge(path,fragment):
 assert fragment in [0,1];watch={};squeeze=set();goal=False;bad=[];malformed=False
 with Path(path).open(errors='replace') as f:
  for line in f:
   if re.search(r'\b(?:OOM|HALT|MISSING)\b',line):bad.append(line.strip()[:300])
   if 'warp: alert at room frame 30 (entry 1)' in line:goal=True
   m=SQUEEZE.search(line)
   if m:squeeze.add(tuple(map(int,m.groups())))
   m=WATCH.search(line)
   if m:
    v=tuple(map(int,m.groups()));watch[v]=True
    frame,free,used,brk,head,mn,top,holes=v
    if head!=free+brk or head!=top+holes or mn>head:malformed=True
   elif 'kos watch:' in line:malformed=True
 expected={(49152,49152,fragment,1 if fragment==0 else 12)}
 minimum=min((min(v[4],v[5]) for v in watch),default=None);last=max((v[0] for v in watch),default=None)
 observed=bool(watch) and squeeze==expected and goal and last>=960 and not malformed
 return dict(status='PASS_BOUNDED_KOS48' if observed and minimum>=4096 and not bad else ('FAIL_BOUNDED_KOS48' if observed else 'UNKNOWN_INCOMPLETE_KOS_OBSERVATION'),observed=observed,minimum_headroom=minimum,required=4096,last_watch_frame=last,unique_watch_rows=len(watch),squeeze=sorted(squeeze),route_goal=goal,malformed=malformed,fatal_tokens=bad[:20],old_failures_preserved=True,hardware_or_performance_qualification=False)
