#!/usr/bin/env python3
"""Compile actual hand-cache namespace/public entrypoints; omit only untouched renderer glue."""
from pathlib import Path
import argparse,os,subprocess,tempfile
HERE=Path(__file__).resolve().parent;repo=HERE.parents[4]
p=argparse.ArgumentParser();p.add_argument('--control-ref');args=p.parse_args()
with tempfile.TemporaryDirectory(prefix='re4-hands-')as name:
 root=Path(name)
 for d in['kos','dc/sound','dc','arch']: (root/d).mkdir(parents=True,exist_ok=True)
 (root/'kos.h').write_text('#pragma once\n#include <sys/types.h>\n#include <cstddef>\n#include <cstdint>\n')
 (root/'kos/fs.h').write_text('#pragma once\n#include <sys/types.h>\nusing file_t=int;\nconstexpr int FILEHND_INVALID=-1;\nfile_t fs_open(const char*,int);int fs_close(file_t);off_t fs_seek(file_t,off_t,int);ssize_t fs_read(file_t,void*,size_t);\n')
 (root/'dc/spu.h').write_text('#pragma once\nvoid spu_memload(unsigned,const void*,unsigned);void spu_memread(void*,unsigned,unsigned);\n')
 (root/'dc/sound/sound.h').write_text('#pragma once\nunsigned snd_mem_malloc(unsigned);void snd_mem_free(unsigned);\n')
 (root/'arch/timer.h').write_text('#pragma once\nunsigned long long timer_us_gettime64();\n')
 (root/'kos/thread.h').write_text('#pragma once\nstruct kthread_t {void*(*fn)(void*);void* arg;bool ran;};\nstruct kthread_attr_t {void* stack_ptr;unsigned stack_size;int prio;const char* label;};\nconstexpr int PRIO_DEFAULT=10;\nkthread_t* thd_create_ex(const kthread_attr_t*,void*(*)(void*),void*);int thd_join(kthread_t*,void**);\n')
 (root/'kos/mutex.h').write_text('#pragma once\nusing mutex_t=int;\n#define MUTEX_INITIALIZER 0\ninline void mutex_lock(mutex_t*){}\ninline void mutex_unlock(mutex_t*){}\ninline int mutex_trylock(mutex_t*){return 0;}\n')
 source=repo/'port/dreamcast/game/coarse_actor_leon_hands.inc'
 cases=[('fixed',source.read_text(),1),('off',source.read_text(),0)]
 if args.control_ref:cases.append(('control',subprocess.check_output(['git','-C',str(repo),'show',args.control_ref+':port/dreamcast/game/coarse_actor_leon_hands.inc'],text=True),0))
 preprocessed={}
 for label,text,fixed in cases:
  first='\nnamespace {\nunsigned leon_hand_asset';last='// Room load (ui_bridge.cpp, with the pl08 package)'
  assert text.count(first)==1 and text.count(last)==1
  # Keep every line of the cache namespace and its actual public lifecycle/API.
  # Only unedited ChunkInput/render-plan glue between these unique markers is excluded.
  (root/'source-under-test.inc').write_text(text[:text.index(first)]+text[text.index(last):])
  exe=root/label
  cmd=[os.environ.get('CXX','g++'),'-std=c++17','-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-DTEST_FIXED='+str(fixed),'-DRE4DC_LEON_HAND_RETAIN='+str(fixed),'-I'+str(root),'-I'+str(HERE),str(HERE/'leon_hand_cache_host.cpp'),'-o',str(exe)]
  if not fixed:preprocessed[label]=subprocess.check_output([os.environ.get('CXX','g++'),'-std=c++17','-E','-P','-x','c++','-DRE4DC_LEON_HAND_RETAIN=0','-I'+str(root),str(root/'source-under-test.inc')],text=True)
  subprocess.run(cmd,check=True);subprocess.run([str(exe)],check=True,env={**os.environ,'ASAN_OPTIONS':'detect_leaks=1'})
 if args.control_ref:
  assert preprocessed['off']==preprocessed['control'],'OFF preprocessed loader/public entrypoints differ from prior control'
  print('hand retain OFF actual-source preprocessing identity PASS')
