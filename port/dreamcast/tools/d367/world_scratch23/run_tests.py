"""Small host controls; no game build, guest or assets."""
from pathlib import Path
import importlib.util, subprocess, tempfile
T=Path(__file__).resolve().parent; D=T.parents[2]; G=D/'game'
def run(args,**kwargs):return subprocess.check_output(list(map(str,args)),text=True,**kwargs)
def main():
 with tempfile.TemporaryDirectory(prefix='world-scratch23-') as tmp:
  o=Path(tmp)
  flags=['-std=c++17','-O2','-Wall','-Wextra','-Werror','-DRE4DC_WORLD_SCRATCH=1','-DRE4DC_WORLD_SCRATCH_HOST=1','-I'+str(G),'-I'+str(D/'room'),'-I'+str(G/'platform/include'),'-I'+str(T/'stubs')]
  print(run(['g++',*flags,G/'world_scratch.cpp',T/'test_scratch.cpp','-o',o/'host']).strip());print(run([o/'host']).strip())
  print(run(['g++',*flags,G/'world_scratch.cpp',T/'test_selector.cpp','-o',o/'selector']).strip());run([o/'selector'])
  runtime_flags=[x for x in flags if x!='-DRE4DC_WORLD_SCRATCH_HOST=1']+['-DRE4DC_WORLD_SCRATCH_RUNTIME_TEST=1','-DRE4DC_DBG_WARP=1']
  run(['g++',*runtime_flags,G/'world_scratch.cpp',T/'test_runtime.cpp','-o',o/'runtime']);run([o/'runtime'])
  for arm in range(5):run([o/'runtime',arm])
  run([o/'runtime','stale']);run([o/'runtime','admit'])
  for scenario in ('A','B','C','cancel','room','owner','mode','borrow'):run([o/'runtime','meter-'+scenario])
  run(['g++',*flags,T/'test_meter.cpp','-o',o/'meter']);run([o/'meter'])
  # Compile actual neutral getter bodies, including the current-room/tick predicate.
  bridge=(G/'dbgwarp_bridge.cpp').read_text()
  def body(name):
   start=bridge.index(name);left=bridge.index('{',start);depth=1;right=left+1
   while depth:
    depth += (bridge[right]=='{')-(bridge[right]=='}');right+=1
   return bridge[start:right]
  getter='#include <cassert>\nstruct Game {unsigned room_id,Frame_cnt;};\nstruct Warp {bool has_late;unsigned late_room,late_tick;};\nGame game{},*pG=nullptr;Warp wp{true,0x109,166};\n'+body('int re4dc_warp_late_open(void)')+'\n'+body('unsigned re4dc_warp_late_room(void)')+'\nint main(){assert(re4dc_warp_late_room()==0);pG=&game;game={0x109,165};assert(!re4dc_warp_late_room());game.Frame_cnt=166;assert(re4dc_warp_late_room()==0x109);game.room_id=0x101;assert(!re4dc_warp_late_room());game.room_id=0x109;wp.has_late=false;assert(!re4dc_warp_late_room());wp.has_late=true;assert(re4dc_warp_late_room()==0x109);}\n'
  (o/'getter.cpp').write_text(getter);run(['g++','-std=c++17','-O2',o/'getter.cpp','-o',o/'getter']);run([o/'getter'])
  (o/'getter-off.cpp').write_text('#include "warp_late.h"\nstatic_assert(RE4DC_WARP_LATE_ROOM()==0u);\n')
  run(['g++','-std=c++17','-O2','-I'+str(G/'platform/include'),'-c',o/'getter-off.cpp','-o',o/'getter-off.o'])
  assert not run(['nm',o/'getter-off.o']).strip()
  for define,name in [([], 'default'),(['-DRE4DC_WORLD_SCRATCH=0'],'zero')]:
   run(['g++','-std=c++17','-O2',*define,'-c',G/'world_scratch.cpp','-o',o/(name+'.o')])
  assert (o/'default.o').read_bytes()==(o/'zero.o').read_bytes()
  assert not run(['nm',o/'default.o']).strip()
  # Old and successor default-off runtime objects are identical. Historical
  # 2158 address/ELF-pinned readers still require fresh addresses in a NEW image.
  old_cpp=run(['git','-C',G.parents[2],'show','2158baff82e0812e5cf9ed3186e27e22d753d045:port/dreamcast/game/world_scratch.cpp'])
  (o/'world_scratch.cpp').write_text(old_cpp)
  run(['g++','-std=c++17','-O2','-I'+str(G),'-c',o/'world_scratch.cpp','-o',o/'old.o'])
  assert (o/'old.o').read_bytes()==(o/'default.o').read_bytes()
  # Compile the actual private Diagnostics formatter without KOS/UI machinery.
  ui=(G/'platform/native_ui.cpp').read_text();qa=(G/'qa_menu.cpp').read_text()
  for name,skip in [('re4dc_ui_begin',0),('re4dc_ui_begin_skip',1)]:
   start=ui.index('extern "C" void '+name+'(){')
   first=ui[start:ui.index('#endif',start)+6]
   assert 're4dc_world_scratch_boundary('+str(skip)+',re4dc_ps2_mesh_room());' in first
  start=qa.index('int scratch_rows(');left=qa.index('{',start);depth=1;right=left+1
  while depth:depth+=(qa[right]=='{')-(qa[right]=='}');right+=1
  formatter='#include "world_scratch.h"\n#include <cassert>\n#include <cstdarg>\n#include <cstdio>\n#include <cstring>\nchar text[2048]{};\nint addf(int at,const char* f,...){va_list a;va_start(a,f);const int n=vsnprintf(text+at,sizeof(text)-at,f,a);va_end(a);return at+n;}\nextern "C" int re4dc_world_scratch_meter_read(re4dc::world_scratch::MeterSnapshot* s){*s={};s->version=1;s->kind=1;s->target=600;s->phase=3;s->complete=1;s->arm=2;s->window_serial=1;s->periods=600;s->drawn=300;s->skipped=300;s->ccr=0x105;s->restored=1;s->wall_us_lo=600000;s->max_us_lo=1000;return 1;}\n'+qa[start:right]+'\nint main(){scratch_rows(0);assert(strstr(text,"COMPLETE C"));assert(strstr(text,"avg=1.000 ms"));assert(strstr(text,"CCR=105 restored=1"));assert(strstr(text,"INCLUDED IN WALL"));assert(!strstr(text,"ACTIVE C"));}\n'
  (o/'format.cpp').write_text(formatter);run(['g++','-std=c++17','-O2','-DRE4DC_WORLD_SCRATCH=1','-I'+str(G),o/'format.cpp','-o',o/'format']);run([o/'format'])
  # Exercise BOTH actual production completion-log calls with UINT_MAX/u64max
  # through mem.cpp's real256-byte vsnprintf contract, not the QA formatter.
  cpp=(G/'world_scratch.cpp').read_text();start=cpp.index('if(meter_complete_published && !meter_logged)')
  calls=cpp[cpp.index('re4dc_log(',start):cpp.index('\n    }',start)]
  assert calls.count('re4dc_log(')==2 and calls.count('serial=1 completed_arm=%u room=%x')==2
  width_test='#include "world_scratch.h"\n#include <cassert>\n#include <cstdarg>\n#include <cstdio>\n#include <cstring>\n#include <climits>\nusing namespace re4dc::world_scratch;\nunsigned nlog=0;\nvoid re4dc_log(const char* fmt,...) __attribute__((format(printf,1,2)));\nvoid re4dc_log(const char* fmt,...){char line[256];va_list args;va_start(args,fmt);const int n=vsnprintf(line,sizeof(line),fmt,args);va_end(args);assert(n>0 && n<256 && std::strlen(line)==unsigned(n) && line[n-1]==char(10));assert(std::strstr(line,"serial=1 completed_arm=4294967295 room=ffffffff"));assert(std::strstr(line,nlog?"WS23 wall-state ":"WS23 wall-time "));assert(n==int(nlog?170:252));++nlog;}\nint main(){const unsigned selected_arm=UINT_MAX,selected_room=UINT_MAX,mode=UINT_MAX;MeterTotals t{};t.periods=t.drawn=t.skipped=UINT_MAX;t.wall_us=t.draw_us=t.skip_us=t.max_us=ULLONG_MAX;Stats st{};st.entries=st.exits=st.borrows=UINT_MAX;Snapshot value{};value.faults=value.restored=UINT_MAX;\n'+calls+'\nassert(nlog==2);}\n'
  (o/'log_width.cpp').write_text(width_test);run(['g++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-DRE4DC_WORLD_SCRATCH=1','-I'+str(G),o/'log_width.cpp','-o',o/'log_width']);run([o/'log_width'])
  # Actual old/new Diagnostics preprocessing is identical with scratch off;
  # the empty KOS/QR declarations are sufficient for preprocessing only.
  for name in ('kos.h','dc/maple.h','dc/maple/controller.h','dc/video.h','arch/timer.h','third_party/qrcodegen/qrcodegen.h'):
   stub=o/'preprocess-stubs'/name;stub.parent.mkdir(parents=True,exist_ok=True);stub.write_text('')
  old_qa=run(['git','-C',G.parents[2],'show','bb41fe683:port/dreamcast/game/qa_menu.cpp'])
  (o/'qa_menu.cpp').write_text(old_qa)
  for world_meter in (0,1):
   pp=['g++','-E','-P','-I'+str(o/'preprocess-stubs'),'-DRE4DC_WORLD_METER='+str(world_meter),'-DRE4DC_QA_NAME="QA"']
   (o/'qa_menu_new.cpp').write_text((G/'qa_menu.cpp').read_text())  # same directory: same relative include lookup
   assert run(pp+[o/'qa_menu.cpp']).split()==run(pp+[o/'qa_menu_new.cpp']).split()  # tokens (live-arm macros expand empty)
 spec=importlib.util.spec_from_file_location('audit_image',T/'audit_image.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 assert m.section(' 28 .ocram 00002000 7c001000 7c001000 00000964 2**5')['bytes']==8192
 for size,address,align in [('00002100','7c001000','5'),('00002000','7dfff000','5'),('00002000','7c001000','2')]:
  try:m.section(f' 28 .ocram {size} {address} 7c001000 00000964 2**{align}')
  except ValueError:pass
  else:raise AssertionError('accepted bad final section')
 assert 'projected_records' in m.check_symbols('7c001000 00002000 d (anonymous namespace)::projected_records')
 for symbols in ['7c001000 00002000 d foreign','7c001000 00001000 d projected_records','7c001000 00002000 d projected_records\n7c001020 00000020 d peer']:
  try:m.check_symbols(symbols)
  except ValueError:pass
  else:raise AssertionError('accepted conflicting owner')
 # Evaluate actual make fragment, target-specific flags and object dependency.
 text='TARGET=sample.elf\nOBJDIR=obj\nPLATFORM_OBJS=\ninclude '+str(G/'worldscratch.mk')+'\n.PHONY: inspect\ninspect:\n\t@echo objects=$(PLATFORM_OBJS)\nobj/platform/native_ui.o:\n\t@echo flags=$(PLATFORM_CPPFLAGS)\nobj/qa_menu.o:\n\t@echo qa_flags=$(PLATFORM_CPPFLAGS)\n'
 with tempfile.TemporaryDirectory(prefix='world-scratch-make-') as tmp:
  p=Path(tmp)/'Makefile';p.write_text(text)
  base=['make','--no-print-directory','-f',p,'inspect']
  assert 'world_scratch.o' not in run(base)
  cfg=['WORLD_SCRATCH=1','PS2_WORLD_DRAW=1','PS2_WORLD_MESH=1','MESH_FASTPATH=1','MESH_DIRECT=1','PVR_STREAM=1','CPU_BACKFACE=0','NATIVE_STATIC=1','NATIVE_MESH=1','D349_RENDERER_STACK=1']
  assert 'obj/world_scratch.o' in run(base+cfg)
  qa_cmd=['make','--no-print-directory','-f',p,'-n','obj/qa_menu.o']
  assert 'RE4DC_WORLD_SCRATCH' not in run(qa_cmd)
  # The QA source is compiled with PLATFORM_CPPFLAGS in qamenu.mk.
  assert '-DRE4DC_WORLD_SCRATCH=1' in run(qa_cmd+cfg,cwd=G)
  for bad in [['WORLD_SCRATCH=2'],cfg+['CPU_BACKFACE=1'],cfg+['MESH_FASTPATH=0']]:
   assert subprocess.run(base+bad,stdout=subprocess.PIPE,stderr=subprocess.PIPE).returncode!=0
 print('PASS: exact A/B/C whole wall periods, tail/restore included once, draw/skip and invalidation controls; original100B ABI, default-off object identity, Diagnostics, actual completion logs252/170bytes and Make admission')
if __name__=='__main__':main()
