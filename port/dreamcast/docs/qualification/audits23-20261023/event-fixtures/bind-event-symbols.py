"""Bind main symbols to an existing completed aud23/off-control ELF; read-only, no SDK build."""
import argparse,hashlib,json,pathlib,subprocess

def digest(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for block in iter(lambda:f.read(1<<20),b''):h.update(block)
 return h.hexdigest()
def bind(elf,source,repo,out):
 stat=elf.stat();actual_source=(elf.parent/'stack.txt').read_text().splitlines()[0].strip()
 if actual_source!=source:raise ValueError('programme source mismatch')
 nm='/opt/toolchains/dc/sh-elf/bin/sh-elf-nm';table={}
 for line in subprocess.check_output([nm,'-n',str(elf)],text=True).splitlines():
  parts=line.split()
  if len(parts)==3 and parts[2] in ['pPL','pG','_RoomData','_EmMgr']:
   if parts[2] in table or parts[1] not in ['B','D','b','d']:raise ValueError('ambiguous/non-data symbol')
   table[parts[2]]={'address':hex(int(parts[0],16)),'type':parts[1],'storage':'pointer_global' if parts[2] in ['pPL','pG'] else 'direct_object'}
 if set(table)!=set(['pPL','pG','_RoomData','_EmMgr']):raise ValueError('required exact main symbol absent')
 for row in table.values():
  addr=int(row['address'],16)
  if addr%4 or not 0x8c000000<=addr<0x8d000000:raise ValueError('symbol outside aligned Dreamcast main RAM')
 hashes={}
 for name in ['include/cManager.h','include/room_data.h','include/model.h','include/em.h','include/global.h','src/game/roomdata.cpp','include/flag_rsf.h','src/st1/r117.cpp','src/st1/r10c.cpp','port/dreamcast/tools/d367/fullplay/fp_run.py']:
  hashes[name]=hashlib.sha256(subprocess.check_output(['git','-C',str(repo),'show',source+':'+name])).hexdigest()
 elf_sha=digest(elf);after=elf.stat()
 if (stat.st_size,stat.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):raise ValueError('ELF changed during binding')
 knobs={}
 for line in (elf.parent/'resolved-knobs.txt').read_text().splitlines():
  if line.startswith(tuple(k+'=' for k in ['STAT_ROUTINE_BYTES','ESP_POOL_RECYCLE','R117_EFFECT_FAILURE_SAFE','KOS_CACHE_P2','R10C_SPAWN_LIVE_GUARD','ISSUE52_ACTOR_DIAG','VRAM_ROOM_ARENA','VRAM_ROOM_ARENA_NO_TOP','CACHE_LINEWISE'])):
   k,v=line.split('=',1);knobs[k]=v
 backend=pathlib.Path(__file__).with_name('stat_owned_ram.py')
 data={'schema':1,'source':source,'program_elf':str(elf),'program_elf_windows':subprocess.check_output(['wslpath','-w',str(elf)],text=True).strip(),'program_elf_sha256':elf_sha,'program_elf_bytes':stat.st_size,'programme_symbols':table,'source_sha256':hashes,'resolved_knobs':knobs,'ram_backend_sha256':digest(backend),'overlay_work_phase_claim':'omitted: no authenticated current overlay binding supplied; all work/phase fields remain unknown'}
 with out.open('x') as f:json.dump(data,f,indent=2);f.write('\n')
 print(json.dumps({'out':str(out),'source':source,'elf_sha256':elf_sha,'symbols':table},indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--elf',type=pathlib.Path,required=True);p.add_argument('--source',required=True);p.add_argument('--repo',type=pathlib.Path,required=True);p.add_argument('--out',type=pathlib.Path,required=True);a=p.parse_args();bind(a.elf,a.source,a.repo,a.out)
