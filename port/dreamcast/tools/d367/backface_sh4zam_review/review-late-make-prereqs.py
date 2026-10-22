"""GNU Make dry-run only. No compiler, filesystem recipe or target commands execute."""
from pathlib import Path
import subprocess,json,hashlib
T=Path('/root/probe/codex-backface-sh4zam-review');TIP='cd5f1be0c2d614b0704c692dfe54caf5c9e59f77'
g=lambda *a:subprocess.check_output(['git','-C',str(T),*a])
path='port/dreamcast/game/backface.mk';new=g('show',TIP+':'+path).decode();old=g('show',TIP+'^:'+path).decode()
full=g('show',TIP+':port/dreamcast/game/Makefile').decode()
assert full.index('$(TARGET): $(KOS_BASE)/lib/')<full.index('include backface.mk')
prefix="""OBJDIR := review-objects
TARGET := review-target.elf
PLATFORM_OBJS := $(OBJDIR)/base.o
OBJS = $(PLATFORM_OBJS)
.DEFAULT_GOAL := $(TARGET)
$(TARGET): $(OBJS)
\t@echo LINK_OBJS $(OBJS)
$(OBJDIR)/base.o:
\t@echo BASE_PLACEHOLDER
platform/backface_sh4.S:
\t@echo SOURCE_PLACEHOLDER
$(OBJDIR)/platform/backface_sh4_trace.o:
\t@echo TRACE_PLACEHOLDER
"""
rows=[]
for rev,src in [('before',old),('fixed',new)]:
 for label,args,wantasm,wanttrace,ok in [
  ('default',['TA_HASH=0'],False,False,True),
  ('cpu0',['CPU_BACKFACE=0','TA_HASH=1'],False,False,True),
  ('cpu1',['CPU_BACKFACE=1','TA_HASH=1'],False,False,True),
  ('cpu2-hash0',['CPU_BACKFACE=2','TA_HASH=0'],True,False,True),
  ('cpu2-hash1',['CPU_BACKFACE=2','TA_HASH=1'],True,True,True),
  ('cpu2-hash4',['CPU_BACKFACE=2','TA_HASH=4'],True,False,True),
  ('cpu2-nosh4',['CPU_BACKFACE=2','GAME_SH4ZAM=0'],False,False,False),
  ('invalid',['CPU_BACKFACE=3'],False,False,False)]:
  run=subprocess.run(['make','--no-print-directory','-nrR','-f','-','GAME_SH4ZAM=1',*args,'review-target.elf'],input=prefix+src,text=True,capture_output=True)
  assert(run.returncode==0)==ok,(rev,label,run.stderr)
  sawasm='kos-cc 'in run.stdout
  sawtrace='TRACE_PLACEHOLDER'in run.stdout
  if ok:
   assert sawasm==(wantasm and rev=='fixed'),(rev,label,run.stdout)
   assert sawtrace==(wanttrace and rev=='fixed'),(rev,label,run.stdout)
   if wantasm:assert 'platform/backface_sh4.o'in run.stdout.split('LINK_OBJS')[-1]
  rows.append({'revision':rev,'case':label,'returncode':run.returncode,'asm_build_recipe_selected':sawasm,'trace_build_recipe_selected':sawtrace,'stdout':run.stdout,'stderr':run.stderr})
out={'scope':'actual backface.mk before/after inserted after early linkprereqs in GNU make -n only; dummy source/base/trace targets; no command executed','tip':TIP,'main_Makefile_sha256':hashlib.sha256(full.encode()).hexdigest(),'fixed_block_sha256':hashlib.sha256(new.encode()).hexdigest(),'TARGET_explicitly_defined':True,'parse_order_verified':True,'controls':rows,'fixed_make_dependency_gate':True,'not_proved':'full production Make/resource/source/header/object/linked programme or OFF identity'}
D=T/'port/dreamcast/tools/d367/backface_sh4zam_review';P=D/'LATE-MAKE-PREREQS.json';assert not P.exists();P.write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({'controls':len(rows),'fix_dependency_gate':True,'receipt_sha256':hashlib.sha256(P.read_bytes()).hexdigest()}))

