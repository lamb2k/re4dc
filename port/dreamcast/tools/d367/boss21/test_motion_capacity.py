#!/usr/bin/env python3
"""Actual motion/bridge/main_mem/SDK allocator capacity and reclamation regression."""
import argparse,contextlib,hashlib,importlib.util,json,os,re,subprocess,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[4]
def function(text,marker):
    start=text.index(marker);brace=text.index('{',start)
    return text[start:text.index('\n}',brace)+2]
def source_contract():
    table=json.loads((HERE/'motion-capacity-source-contract.json').read_text())
    leases=0
    for row in table['rows']:
        body=function((REPO/row['path']).read_text(),row['marker'])
        start=body.find('Re4dcMotionLease keys(')
        if start>=0:leases+=1;body=body[start:]
        assert hashlib.sha256(body.encode()).hexdigest()==row['sha256'],('Renew allocation/lock review for changed scope',row['path'],row['marker'])
    assert leases==7,leases
    print('Pinned source scopes PASS: seven evaluators plus reviewed direct helpers/callbacks; not whole-program closure')
def run(out,mode,lean=0,resume=0):
    out.mkdir(parents=True)
    (out/'kos').mkdir();(out/'dolphin/os').mkdir(parents=True)
    (out/'kos.h').write_text(r'''#pragma once
#include <cstdint>
#include <mutex>
#include <thread>
#include <chrono>
extern std::recursive_mutex host_irq;
extern thread_local unsigned host_irq_depth;
inline thread_local unsigned char host_thread;
#define thd_current ((void*)&host_thread)
inline int irq_disable(){unsigned old=host_irq_depth;host_irq.lock();++host_irq_depth;return old?0xf0:0;}
inline void irq_restore(int){--host_irq_depth;host_irq.unlock();}
inline int irq_inside_int(){return 0;}
inline unsigned long long timer_us_gettime64(){return std::chrono::duration_cast<std::chrono::microseconds>(std::chrono::steady_clock::now().time_since_epoch()).count();}
inline void thd_pass(){std::this_thread::yield();}
inline void thd_sleep(unsigned n){std::this_thread::sleep_for(std::chrono::milliseconds(n));}
''')
    (out/'kos/fs.h').write_text('#pragma once\nusing file_t=int;\n')
    (out/'kos/mutex.h').write_text('#pragma once\n#include <mutex>\nusing mutex_t=std::mutex;\n#define MUTEX_INITIALIZER {}\ninline void mutex_lock(mutex_t*m){m->lock();}\ninline void mutex_unlock(mutex_t*m){m->unlock();}\ninline int mutex_trylock(mutex_t*m){return m->try_lock()?0:-1;}\n')
    (out/'kos/net.h').write_text('#pragma once\ninline unsigned net_crc32le(const unsigned char*p,unsigned n){unsigned c=~0U;while(n--){c^=*p++;for(int i=0;i<8;++i)c=(c>>1)^(0xedb88320U&-(c&1));}return ~c;}\n')
    spec=importlib.util.spec_from_file_location('sdk_fixture',REPO/'port/dreamcast/tests/test_source_world_retained.py')
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);mod.generate(out)
    types=(out/'source_world_actual_memory_types.inc').read_text()
    (out/'main_mem.h').write_text('#pragma once\n#include <cstdint>\nusing u32=uint32_t;using s32=int32_t;using u8=uint8_t;\n'+types+'\n#define MEM_HEAP_NUM 13\n#define MEM_HEAP_CURRENT 13\nextern MemHeap Heap[13];\nvoid* mem_alloc(u32,const char*,int,int,int);\nu8 MemGetCurrentHeap();\n')
    (out/'dolphin/os/OSAlloc.h').write_text('#pragma once\nextern "C" {void* OSAllocFromHeap(int,unsigned);void OSFreeToHeap(int,void*);int OSCheckHeap(int);int OSDisableInterrupts();int OSRestoreInterrupts(int); }\n')
    source=(REPO/'src/game/main_mem.cpp').read_text()
    bodies='\n'.join(function(source,x) for x in ('int memGetHeapSattus(','int memCheckHeapActive(','void* mem_alloc(','void* Debug_alloc('))
    (out/'capacity_actual_memory.inc').write_text(bodies+'\n')
    flags=['-O1','-g','-fsanitize=address,undefined','-fno-sanitize-recover=all','-fno-omit-frame-pointer','-fno-pie','-no-pie','-pthread']
    defs=['-DRE4DC_MOTION_CAPACITY='+str(mode),'-DRE4DC_MOTION_LEASE_LEAN='+str(lean),'-DRE4DC_MOTION_RESUME='+str(resume)]
    prelude=(out/'source_world_actual_osalloc.c').read_text()
    prelude='int OSDisableInterrupts(void);int OSRestoreInterrupts(int);\n'+prelude
    (out/'source_world_actual_osalloc.c').write_text(prelude)
    subprocess.run([os.environ.get('CC','gcc'),'-std=gnu11',*flags,*defs,'-w','-c',str(out/'source_world_actual_osalloc.c'),'-o',str(out/'osalloc.o')],check=True)
    defs+=['-DRE4DC_MOTION_PRESSURE_BYTES=262144','-DRE4DC_MOTION_RESERVE=1','-DRE4DC_MOTION_RESERVE_PACK=1','-DRE4DC_MOTION_PRESSURE_BACKING=1','-DRE4DC_MOTION_BOUNDED_R11F=1','-DRE4DC_SUBSCREEN=1','-DRE4DC_MOTION_OOM_EVICT=1','-DRE4DC_MOVIE_HEAP_EVICT=1','-DRE4DC_MOTION_COLD_POOL=262144','-DRE4DC_MOTION_RESERVE_SPILL=524288']
    argv=[os.environ.get('CXX','g++'),'-std=c++17',*flags,*defs,'-Wall','-Wextra','-fpermissive','-Wno-misleading-indentation','-I'+str(out),'-I'+str(REPO/'port/dreamcast/game/platform/include'),str(HERE/'motion_capacity_host.cpp'),str(out/'osalloc.o'),'-o',str(out/'test')]
    (out/'command.json').write_text(json.dumps(argv,indent=2)+'\n')
    cp=subprocess.run(argv,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(out/'compile.txt').write_text(cp.stdout)
    if cp.returncode:print(cp.stdout[-12000:]);cp.check_returncode()
    cp=subprocess.run([str(out/'test')],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=25);(out/'run.txt').write_text(cp.stdout);print(cp.stdout,end='');cp.check_returncode()
    return {'capacity':mode,'lease_lean':lean,'resume':resume,'output':cp.stdout}
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path);args=parser.parse_args()
    source_contract()
    with contextlib.nullcontext(args.out) if args.out else tempfile.TemporaryDirectory(prefix='re4-capacity-') as path:
        out=Path(path)
        rows=[]
        for mode,lean,resume in ((0,0,0),(1,0,0),(1,1,0),(1,1,1)):rows.append(run(out/('capacity-'+str(mode)+'-lean'+str(lean)+'-resume'+str(resume)),mode,lean,resume))
        inputs=['src/lib/OSAlloc.c','src/game/main_mem.cpp','port/dreamcast/game/platform/native_motion.cpp','port/dreamcast/game/motion_bridge.cpp','port/dreamcast/game/ui_bridge.cpp','port/dreamcast/game/game30.mk','port/dreamcast/game/platform/include/native_motion.h']
        proof={'scope':'Actual-source/SDK allocator host tests only; no whole-program/guest/hardware acceptance','variants':rows,'source_sha256':{name:hashlib.sha256((REPO/name).read_bytes()).hexdigest()for name in inputs}}
        (out/'receipt.json').write_text(json.dumps(proof,indent=2)+'\n')
