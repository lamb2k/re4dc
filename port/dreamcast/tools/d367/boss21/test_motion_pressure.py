#!/usr/bin/env python3
"""Compile actual native_motion.cpp with host KOS transport stubs and synthetic FCVs."""
import os,subprocess,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
repo=HERE.parents[4]
with tempfile.TemporaryDirectory(prefix='re4-motion-pressure-')as name:
    root=Path(name);(root/'kos').mkdir()
    (root/'kos.h').write_text('#pragma once\n#include <cstdint>\ninline void* thd_current=(void*)4;\ninline int irq_disable(){return 0;}\ninline void irq_restore(int){}\ninline unsigned long long timer_us_gettime64(){static unsigned long long t;return ++t;}\ninline void thd_pass(){}\ninline void thd_sleep(unsigned){}\n')
    (root/'kos/fs.h').write_text('#pragma once\nusing file_t=int;\n')
    (root/'kos/mutex.h').write_text('#pragma once\nusing mutex_t=int;\n#define MUTEX_INITIALIZER 0\ninline void mutex_lock(mutex_t*){}\ninline void mutex_unlock(mutex_t*){}\n')
    (root/'kos/net.h').write_text('#pragma once\ninline unsigned net_crc32le(const unsigned char*p,unsigned n){unsigned c=~0U;while(n--){c^=*p++;for(int i=0;i<8;++i)c=(c>>1)^(0xedb88320U&-(c&1));}return ~c;}\n')
    flags=['-std=c++17','-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer',
           '-DRE4DC_MOTION_PRESSURE_BYTES=262144','-DRE4DC_MOTION_RESERVE=1','-DRE4DC_MOTION_BOUNDED_R11F=1',
           '-DRE4DC_SUBSCREEN=1','-DRE4DC_MOTION_OOM_EVICT=1','-DRE4DC_MOVIE_HEAP_EVICT=1',
           '-DRE4DC_MOTION_COLD_POOL=262144','-DRE4DC_MOTION_RESERVE_SPILL=524288',
           '-I'+str(root),'-I'+str(repo/'port/dreamcast/game/platform/include')]
    for mode,lean,pack,resume in [(0,0,0,0),(1,0,0,0),(1,1,0,0),(1,0,1,0),(1,1,1,0),(1,0,1,1),(1,1,1,1)]:
        binary=root/('test'+str(mode)+'lean'+str(lean)+'pack'+str(pack)+'resume'+str(resume))
        subprocess.run([os.environ.get('CXX','g++'),*flags,'-DRE4DC_MOTION_PRESSURE_BACKING='+str(mode),'-DRE4DC_MOTION_LEASE_LEAN='+str(lean),'-DRE4DC_MOTION_RESERVE_PACK='+str(pack),'-DRE4DC_MOTION_RESUME='+str(resume),str(HERE/'motion_pressure_host.cpp'),'-o',str(binary)],check=True)
        subprocess.run([str(binary)],check=True,env={**os.environ,'ASAN_OPTIONS':'detect_leaks=1'})
