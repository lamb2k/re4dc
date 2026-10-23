
"""Exact source wrapper/context/neutral getters; no native Render or guest claim.
Usage: build_readiness_host.py SDK CERT OUTPUT. Nonblocking shared+tree lease.
"""
from pathlib import Path
import subprocess,fcntl,sys,json,shutil
t=Path(__file__).resolve().parent;g=t.parents[1];r=g.parents[2];sdk,cert,o=map(Path,sys.argv[1:]);assert shutil.disk_usage('/mnt/c').free>19394461696+1073741824+8*1024**2
slot=None
for p in ['/root/probe/d367-build.lock','/root/probe/d367-build2.lock']:
 f=open(p,'a')
 try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);slot=f;break
 except BlockingIOError:f.close()
if slot is None:raise SystemExit('slots busy; skip')
lease=open(r/'actor23-tree.lock','a');fcntl.flock(lease,fcntl.LOCK_EX|fcntl.LOCK_NB);o.mkdir(exist_ok=False)
def function(s,signature):
 a=s.rindex(signature);b=s.index('{',a)+1;depth=1
 while depth:depth+=(s[b]=='{')-(s[b]=='}');b+=1
 return s[a:b]+'\n'
native=(g/'platform/native_actor_fast.cpp').read_text();assert 're4dc_actor_visibility23_bind(frame_serial+1U,memory && (bytes & ~31U),stats.position_transforms);' in native
helper=(g/'platform/actor_visibility23.cc').read_text();world=(g/'platform/native_static.cpp').read_text();warp=(g/'dbgwarp_bridge.cpp').read_text()
parts=[]
for signature in ['unsigned re4dc_warp_late(void)','int re4dc_warp_late_open(void)','unsigned re4dc_warp_late_room(void)']:parts.append('extern "C" '+function(warp,signature))
parts.append(function(world,'std::uint32_t ps2_crc32('))
for signature in ['extern "C" int re4dc_actor_visibility23_set(','extern "C" void re4dc_actor_visibility23_metadata_check(']:parts.append(function(helper,signature))
parts.append(function(world,'extern "C" int re4dc_actor_world23_context('))
a=helper.index('namespace {\nactor_visibility23::Window fixture23;');b=helper.index('extern "C" void re4dc_actor_visibility23_frame(',a);parts.append(helper[a:b])
for signature in ['extern "C" void re4dc_actor_visibility23_frame(','extern "C" void re4dc_actor_visibility23_bind(']:parts.append(function(helper,signature))
(o/'actual_readiness.inc').write_text('\n'.join(parts))
cmd=['g++','-std=c++17','-O2','-DRE4DC_ACTOR_VISIBILITY23=1','-DRE4DC_DBG_WARP=1','-include',str(g/'platform/include/warp_late.h'),'-I'+str(sdk/'include'),'-I'+str(cert),'-I'+str(g/'platform/include'),'-I'+str(o),str(t/'host_readiness.cpp'),'-o',str(o/'test')]
p=subprocess.run(cmd,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(o/'build.log').write_text(p.stdout);p.check_returncode()
results=[]
for bits in [0,32,64,96,128,256,512,0xffffffff]:
 for scenario in (range(9) if bits in [0,32,64] else [0]):
  if scenario==7 and bits==32:continue
  p=subprocess.run([str(o/'test'),str(cert/'OCCL.bin'),str(bits),str(scenario)],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);results.append({'mask':bits,'scenario':scenario,'code':p.returncode,'output':p.stdout});(o/'results.json').write_text(json.dumps(results,indent=2));print(p.stdout,end='');p.check_returncode()
print('actual wrapper/context cases PASS',len(results))
