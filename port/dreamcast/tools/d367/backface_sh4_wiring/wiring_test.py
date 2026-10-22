"""Exercise the real Make include, including its late link dependencies."""
from pathlib import Path
import subprocess
GAME=Path(__file__).resolve().parents[3]/'game'
MAKE="""OBJDIR := /tmp/backface-wiring-probe
TARGET := backface-probe.elf
.DEFAULT_GOAL := probe
$(TARGET): early.o
include backface.mk
.PHONY: probe /tmp/backface-wiring-probe/platform/native_static.o
probe: /tmp/backface-wiring-probe/platform/native_static.o
/tmp/backface-wiring-probe/platform/native_static.o:
	@echo flags=$(PLATFORM_CPPFLAGS)
	@echo objs=$(PLATFORM_OBJS)
"""
CASES=[
([],0,'flags=','backface_sh4.o'),
(['CPU_BACKFACE=0'],0,'flags=','backface_sh4.o'),
(['CPU_BACKFACE=1','ACTOR_BACKFACE=1'],0,'-DRE4DC_CPU_BACKFACE=1','backface_sh4.o'),
(['CPU_BACKFACE=2','GAME_SH4ZAM=1','ACTOR_BACKFACE=1'],0,'-DRE4DC_CPU_BACKFACE=2','backface_sh4_trace.o'),
(['CPU_BACKFACE=2','GAME_SH4ZAM=1','TA_HASH=1'],0,'backface_sh4_trace.o',None),
(['CPU_BACKFACE=2','GAME_SH4ZAM=1','TA_HASH=4'],0,'backface_sh4.o','backface_sh4_trace.o'),
(['CPU_BACKFACE=2'],2,'needs GAME_SH4ZAM=1',None),
(['ACTOR_BACKFACE=1'],2,'needs CPU_BACKFACE=1 or 2',None),
(['CPU_BACKFACE=3'],2,'must be 0, 1 or 2',None)]
for knobs,rc,required,absent in CASES:
 p=subprocess.run(['make','--no-print-directory','-f','-','probe',*knobs],cwd=GAME,input=MAKE,text=True,capture_output=True)
 out=p.stdout+p.stderr
 assert p.returncode==rc and required in out,(knobs,out)
 assert absent is None or absent not in out,(knobs,out)
for cpu,ta in [(0,0),(1,0),(2,0),(2,1),(2,4)]:
 p=subprocess.run(['make','--no-print-directory','-p','-f','-','probe',f'CPU_BACKFACE={cpu}',f'TA_HASH={ta}','GAME_SH4ZAM=1'],cwd=GAME,input=MAKE,text=True,capture_output=True)
 assert p.returncode==0,p.stderr
 row=next(l for l in p.stdout.splitlines() if l.startswith('backface-probe.elf:'))
 assert ('/platform/backface_sh4.o' in row)==(cpu==2),row
 assert ('/platform/backface_sh4_trace.o' in row)==(cpu==2 and ta==1),row
print('PASS9 selector and5 late-link prerequisite controls (Make only)')
