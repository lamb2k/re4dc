"""Caller supplies owned outputs. Acquires shared nonblocking slot + own tree lease; jobs1.
Usage: build_real_host.py SDK OUTPUT CERT_DIR INPUT_DIR HEADER...
"""
from pathlib import Path
import subprocess,fcntl,json,hashlib,sys
t=Path(__file__).resolve().parent;g=t.parents[1];r=g.parents[2];sdk=Path(sys.argv[1]).resolve();o=Path(sys.argv[2]).resolve();cert=Path(sys.argv[3]).resolve();inp=Path(sys.argv[4]).resolve();o.mkdir(exist_ok=False)
slot=None
for path in ['/root/probe/d367-build.lock','/root/probe/d367-build2.lock']:
 f=open(path,'a')
 try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);slot=f;break
 except BlockingIOError:f.close()
if slot is None:raise SystemExit('slots busy; no compiler')
lease=open(r/'actor23-tree.lock','a');fcntl.flock(lease,fcntl.LOCK_EX|fcntl.LOCK_NB)
def function(text,signature):
 start=text.rindex(signature);a=text.index('{',start);depth=1;b=a+1
 while depth:
  depth+=(text[b]=='{')-(text[b]=='}');b+=1
 return text[start:b]+'\n'
static=(g/'platform/native_static.cpp').read_text();ui=(g/'platform/native_ui.cpp').read_text()
for filename,source,signature in [('placements_actual.inc',static,'extern "C" int re4dc_ps2_placements_intact('),('world_ready_actual.inc',static,'extern "C" int re4dc_actor_world23_ready('),('ui_ready_actual.inc',ui,'extern "C" unsigned re4dc_actor_world23_scene(')]:
 (o/filename).write_text(function(source,signature))
commands=[]
def run(cmd,name):
 p=subprocess.run(cmd,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(o/name).write_text(p.stdout);commands.append({'argv':cmd,'code':p.returncode});(o/'commands.json').write_text(json.dumps(commands,indent=2));print(name,p.returncode,p.stdout[-3500:]);p.check_returncode()
inc=['-I'+str(g/'platform/include'),'-I'+str(cert),'-I'+str(sdk/'include'),'-I'+str(o)]
base=['-O2','-fPIC','-fno-fast-math','-ffp-contract=off',*inc]
for source,name in [(sdk/'source/shz_bounds.c','sdk'),(g/'platform/room_occl.c','occl'),(t/'host_real_room.c','room')]:run(['gcc',*base,'-c',str(source),'-o',str(o/(name+'.o'))],name+'.log')
for source,name in [(t/'host_placement_state.cpp','placement'),(t/'host_receipt_bridge.cpp','receipt')]:run(['g++','-std=c++17',*base,'-c',str(source),'-o',str(o/(name+'.o'))],name+'.log')
run(['g++','-std=c++17',*base,'-shared','-DRE4DC_ACTOR_VISIBILITY23=1',str(g/'platform/actor_visibility23.cc'),str(t/'host_bridge.cpp'),*[str(o/(name+'.o')) for name in ['sdk','occl','room','placement','receipt']],'-o',str(o/'host.so')],'shared.log')
run(['g++','-std=c++17',*base,str(t/'test_receipt.cpp'),'-o',str(o/'receipt')],'unit-build.log');run([str(o/'receipt')],'unit.log')
assets=sys.argv[5:]
run(['python3',str(t/'test_real_cottage.py'),str(o/'host.so'),str(cert/'OCCL.bin'),*assets],'real-cottage.log')
run(['python3',str(t/'test_actual_receipt.py'),str(o/'host.so'),str(cert),str(inp)],'actual-getter.log')
print('receipt host unit, actual extracted getters and real source/panel oracle PASS')
