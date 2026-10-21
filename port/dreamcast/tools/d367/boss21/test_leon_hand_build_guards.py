#!/usr/bin/env python3
"""Actual Makefile dry-run checks; pass the normal baseline make arguments on argv."""
from pathlib import Path
import subprocess,sys
repo=Path(__file__).resolve().parents[5];g=repo/'port/dreamcast/game';out='/tmp/boss21-hand-build-guards'
base=['make','-n','-C',str(g),*sys.argv[1:],'OBJDIR='+out,'LEON_HAND_POSES=1','PS2_LEON=1','ACTOR_PL08=1','LEON_HAND_PACK=1','LEON_HAND_DIR=','PS2_LEON_DIR=/root/probe/lanes-20261011/pl08/assets/arm-a']
for retain in[0,1]:
 q=subprocess.run([*base,'LEON_HAND_RETAIN='+str(retain),out+'/coarse_actor.o'],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 assert q.returncode==0,q.stdout
 cmd=next(x for x in q.stdout.splitlines()if x.startswith('kos-c++ ')and 'coarse_actor.cpp'in x)
 assert ('-DRE4DC_LEON_HAND_RETAIN=1'in cmd)==bool(retain),cmd
for flags,error in[(['LEON_HAND_RETAIN=2'],'LEON_HAND_RETAIN must be 0 or 1'),(['LEON_HAND_RETAIN=1','LEON_HAND_PACK=0'],'LEON_HAND_RETAIN needs LEON_HAND_PACK=1')]:
 q=subprocess.run([*base,*flags,out+'/coarse_actor.o'],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 assert q.returncode!=0 and error in q.stdout,q.stdout
print('actual hand Makefile flags/default/dependency guards PASS; dry run only')
