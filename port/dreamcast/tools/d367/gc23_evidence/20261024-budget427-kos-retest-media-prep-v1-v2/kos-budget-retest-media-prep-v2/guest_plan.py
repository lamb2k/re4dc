"""Emit exact four-case proposal only. This tool never launches a guest."""
from pathlib import Path
import json,sys,types
HERE=Path(__file__).resolve().parent
def main():
 assert sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
 p=HERE/'core.py';k=types.ModuleType('core');k.__file__=str(p);sys.modules['core']=k;exec(compile(p.read_bytes(),str(p),'exec'),k.__dict__)
 binding=k.validate_binding(k.read(HERE/'BINDING.json'));old=k.read(HERE.parent/'qa-memory-media-prep/FUTURE-GUEST-COMMANDS.json')['KOS4']
 def win(p):
  p=Path(p);s=str(p)
  if s.startswith('/mnt/c/'):return 'C:\\'+s[7:].replace('/','\\')
  return '\\\\wsl.localhost\\Ubuntu-24.04'+s.replace('/','\\')
 pillow=HERE.parent/'pillow-isolated-prep-v1';cases=[]
 for frag in [0,1]:
  for arm in ['off','on']:
   original=next(x for x in old if x['name']=='kos-'+arm+'-49152-'+str(frag));argv=list(original['argv']);name='corrected427-'+arm+'-49152-'+str(frag)
   cap=k.FINAL/'captures'/name;cache=k.FINAL/'cache'/name
   assert not cap.exists() and not cache.exists() and cache.is_absolute()
   argv[argv.index('--base')+1]=win(k.OFF if arm=='off' else k.FINAL/'on');argv[argv.index('--cap')+1]=win(cap)
   symbols=binding['arms'][arm]['symbols'];argv[argv.index('--syms')+1]=' '.join(hex(symbols[n]-0x8c000000) for n in ['_re4dc_logbuf','_re4dc_log_head','_re4dc_stage'])
   argv[argv.index('--name')+1]=name;argv[argv.index('--period')+1]='25'
   # Remove original post_slot.py/kos. The new root controller must implement
   # equivalent post-slot admission + explicit new grant/cumulative-cap checks.
   # The bounded wrapper remains the unchanged exact55s census wrapper.
   argv[5:7]=['-I','-S','-B','-X','pycache_prefix='+win(cache),win(pillow/'pillow_launcher.py'),'--',r'C:\Game Dev\Emulators\codex-lanes\stat-bytes23\census-bound-run.py']
   cases.append(dict(name=name,arm=arm,fragment=frag,held=49152,argv=argv,cache_WSL=str(cache),cache_must_be_absent_before_Python_start=True,cap_WSL=str(cap),original_requirements=original['requirements'],harness_seconds=45,exact_child_seconds=55,serial=True,requires_new_root_controller_and_guest_grant=True))
 k.fresh(HERE/'GUEST-PROPOSAL.json',dict(status='PROPOSAL_ONLY_NO_EXECUTION',source=k.SOURCE,cases=cases,stage_prerequisite='PAIR-STAGE-COMPLETE plus independent all-file readback CLEAR',environment={'RE4DC_EMU':'console','FP_NOLIMIT':'1','RE4DC_MAX_FLYCASTS':'16','TRACE_SLOTS':'16','STAT_GUEST_SLOTS':'3'},actual_config_prePopen_required={'aica.LimitFPS':'no'},locks='stat root3 slot then trace global16; exact owned55s child',H2='HELD_NOT_AUTHORIZED',caps=dict(new_delta=k.DELTA,aggregate=k.AGG),warnings=['No guest controller or new guest grant is provided by this proposal. Do not run argv directly; root must insert the exact new post-slot admission/controller before Pillow Python starts.','Paired pass requires actual held49152+correctfrag,routegoal,minimum headroom>=4096,noOOM/HALT/MISSING and no deadline fired; old4000/4016 failures remain immutable.','Screenshots evidence only; use pinned Pillow3bcff1c5 with fresh absent absolute-X before Python. No performance/hardware acceptance.']))
if __name__=='__main__':main()
