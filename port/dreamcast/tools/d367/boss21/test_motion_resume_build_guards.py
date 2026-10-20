#!/usr/bin/env python3
"""Dry-run actual Makefile controls; accepts the normal baseline make arguments on argv."""
from pathlib import Path
import tempfile,subprocess,sys
r=Path(__file__).resolve().parents[5];g=r/'port/dreamcast/game'
base=['make','-n','-C',str(g),*sys.argv[1:],'OBJDIR=/tmp/boss21-resume-guard','NATIVE_STATIC=1','D349_RENDERER_STACK=1','PVR_PIPELINE=2','MOTION_RESERVE=1','MOTION_PRESSURE_BYTES=262144','MOTION_PRESSURE_BACKING=1','MOTION_BOUNDED_R11F=1','ROUTE_CH23=1','ROUTE_CH21=1','ROUTE_OVL=1','EM10_SHARED=1','WORLD_STAGE_MODULES=0','MOTION_RESERVE_SPILL=524288','MOTION_COLD_POOL=262144','SUBSCREEN=1','MOTION_OOM_EVICT=1','MOVIE_HEAP_EVICT=1','ROUTE_MOVIES=1','MOTION_FAST_READ=1','MOTION_LEASE_LEAN=1','GAME_MOTION_INDEX=1']
for target in ['platform/native_motion.o','platform/native_movie.o','route_movie_bridge.o']:
 cmd=[*base,'MOTION_RESUME=1','/tmp/boss21-resume-guard/'+target]
 q=subprocess.run(cmd,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);assert q.returncode==0,q.stdout
 lines=[x for x in q.stdout.splitlines()if x.startswith('kos-c++ ')];assert len(lines)==1,(target,q.stdout)
 assert '-DRE4DC_MOTION_RESUME=1'in lines[0],lines[0]
for override,expected in [('MOTION_RESUME=2','MOTION_RESUME must be 0 or 1'),('MOTION_PRESSURE_BACKING=0','MOTION_RESUME needs MOTION_PRESSURE_BACKING=1'),('MOVIE_HEAP_EVICT=0','MOTION_RESUME needs MOVIE_HEAP_EVICT=1'),('ROUTE_MOVIES=0','needs MOTION_OOM_EVICT=1 ROUTE_MOVIES=1')]:
 q=subprocess.run([*base,'MOTION_RESUME=1',override,'/tmp/boss21-resume-guard/platform/native_motion.o'],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 assert q.returncode!=0 and expected in q.stdout,(override,q.stdout)
print('resume actual Makefile guards PASS: all three target flags + four rejected invalid controls; dry run only')