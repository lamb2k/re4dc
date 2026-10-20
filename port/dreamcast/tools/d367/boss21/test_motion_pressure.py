#!/usr/bin/env python3
"""Compile actual native_motion.cpp with host KOS transport stubs and synthetic FCVs."""
import os,subprocess,tempfile,argparse
from pathlib import Path
HERE=Path(__file__).resolve().parent
repo=HERE.parents[4]
parser=argparse.ArgumentParser();parser.add_argument('--control-ref',help='Also run the three-key fragmentation regression against this prior actual native source')
options=parser.parse_args()
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
    cases=[(0,0,0,False,False),(1,0,0,False,False),(1,1,0,False,False),(1,0,1,False,False),(1,1,1,False,False),(1,0,1,False,True)]
    if options.control_ref:
        source=root/'control/port/dreamcast/game/platform';source.mkdir(parents=True)
        (source/'native_motion.cpp').write_bytes(subprocess.check_output(['git','-C',str(repo),'show',options.control_ref+':port/dreamcast/game/platform/native_motion.cpp']))
        (source/'native_motion_r11f_profiles.inc').symlink_to(repo/'port/dreamcast/game/platform/native_motion_r11f_profiles.inc')
        (source.parent.parent/'room').symlink_to(repo/'port/dreamcast/room',target_is_directory=True)
        harness=(HERE/'motion_pressure_host.cpp').read_text().replace('#include "../../../game/platform/native_motion.cpp"','#include "'+str(source/'native_motion.cpp')+'"')
        (root/'control-host.cpp').write_text(harness);cases.append((1,0,1,True,False))
    for mode,lean,pack,control,query_absent in cases:
        binary=root/('test'+str(mode)+'lean'+str(lean)+'pack'+str(pack)+'control'+str(int(control))+'queryAbsent'+str(int(query_absent)))
        chosen=root/'control-host.cpp'if control else HERE/'motion_pressure_host.cpp'
        subprocess.run([os.environ.get('CXX','g++'),*flags,'-DRE4DC_MOTION_PRESSURE_BACKING='+str(mode),'-DRE4DC_MOTION_LEASE_LEAN='+str(lean),'-DRE4DC_MOTION_RESERVE_PACK='+str(pack),'-DRE4DC_TEST_EXPECT_REGION='+str(int(not control and not query_absent)),'-DRE4DC_TEST_QUERY_ABSENT='+str(int(query_absent)),str(chosen),'-o',str(binary)],check=True)
        subprocess.run([str(binary)],check=True,env={**os.environ,'ASAN_OPTIONS':'detect_leaks=1'})
