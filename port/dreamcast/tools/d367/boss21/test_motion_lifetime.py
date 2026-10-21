#!/usr/bin/env python3
"""Actual release-SDK reset/unload and partial admission tests; no assets."""
import argparse,hashlib,importlib.util,json,os,re,subprocess
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[4]
sys.path.insert(0,str(HERE))
from motion_consumer_audit import fn
def function(s,marker):return fn(s,marker[:marker.index('(')].split()[-1])[0]
def sha(b):return hashlib.sha256(b).hexdigest()
def command(argv,path,timeout=45):
    cp=subprocess.run(list(map(str,argv)),text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout)
    path.with_suffix('.command.json').write_text(json.dumps(list(map(str,argv)),indent=2)+'\n');path.write_text(cp.stdout)
    if cp.returncode:print(cp.stdout[-14000:]);cp.check_returncode()
    return cp.stdout

def export_source(out,ref):
    src=out/'source';src.mkdir(parents=True)
    names=['src/game/game.cpp','src/game/snd.cpp','src/game/db_menu.cpp','port/dreamcast/game/ui_bridge.cpp','port/dreamcast/game/game30.mk','port/dreamcast/game/platform/native_motion_r11f_profiles.inc','src/lib/OSAlloc.c','src/game/main_mem.cpp','src/game/trans_ot.cpp','include/main_mem.h','include/trans_ot.h','src/game/main.cpp','src/game/read.cpp','include/read.h','src/game/event.cpp','include/event.h','port/dreamcast/game/motion_bridge.cpp','port/dreamcast/game/platform/native_motion.cpp','port/dreamcast/room/room_storage.hpp','port/dreamcast/tests/test_source_world_retained.py','port/dreamcast/tests/fixtures/source_world_allocator.inc','port/dreamcast/tests/fixtures/source_world_retained.cpp']
    names+=subprocess.check_output(['git','-C',str(REPO),'ls-tree','-r','--name-only',ref,'port/dreamcast/game/platform/include'],text=True).splitlines()
    pins={}
    for name in sorted(set(names)):
        data=subprocess.check_output(['git','-C',str(REPO),'show',ref+':'+name]);p=src/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data);pins[name]=sha(data)
    s=(src/'src/game/main.cpp').read_text();soft,line=fn(s,'systemSoftReset');common,_=fn(s,'systemResetCommon')
    assert soft.index('MemClearAllHeap();')<soft.index('systemResetCommon();')
    assert common.index('TaskAllClear();')<common.index('EmReadInit();')
    return src,pins,{'systemSoftReset_line':line,'heap_destroy_before_task_clear_and_EmReadInit':True}

def reviewed_pins(src):
    rows={'src/game/main.cpp':['systemResetCheck','systemSoftReset','systemResetCommon'],'src/game/main_mem.cpp':['MemClearAllHeap','MemDestroyHeap','memCheckHeapActive','Mem_free_h'],'src/game/read.cpp':['ModuleMemFree','InitModule','EmReadInit','readEm','pullEmModule','readEmData'],'src/lib/OSAlloc.c':['OSDestroyHeap','OSFreeToHeap'],'port/dreamcast/game/motion_bridge.cpp':['re4dc_motion_free'],'port/dreamcast/game/platform/native_motion.cpp':['release_binding','re4dc_motion_bind','re4dc_motion_unbind','re4dc_motion_retire_all'],'src/game/event.cpp':['EventMgr::SetEvd','EventMgr::SetBin','DatTbl::SetDat','DatTbl::ChkDat','Event::ExeEndEvt'],'src/game/game.cpp':['gameRoomMemInit'],'port/dreamcast/game/ui_bridge.cpp':['re4dc_room_leave'],'src/game/snd.cpp':['SndSoftReset'],'src/game/db_menu.cpp':['DbmenuModuleInit']}
    result=[]
    for path,names in rows.items():
        source=(src/path).read_text()
        for name in names:
            body,line=fn(source,name);result.append({'path':path,'name':name,'line':line,'sha256':sha(body.encode())})
    return result

def build_motion(out,src,fix):
    # Shared SDK scaffolding originated in the sealed capacity regression.
    # The exported selected source is used here; no runtime body is replaced.
    REPO=src
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

    s=(src/'src/game/main_mem.cpp').read_text()
    names=['memGetHeapSattus','memCheckHeapActive','mem_alloc','Debug_alloc','MemSignalHeap','MemDestroyHeap','MemClearAllHeap','Mem_free_h','Mem_free','Debug_free_h']
    (out/'lifetime_actual_memory.inc').write_text('\n'.join(fn(s,n)[0]for n in names)+'\n')
    (out/'actual_motion_bridge.inc').write_text((src/'port/dreamcast/game/motion_bridge.cpp').read_text())
    (out/'actual_native_motion.inc').write_text('#include "'+str(src/'port/dreamcast/game/platform/native_motion.cpp')+'"\n')
    header=(src/'include/read.h').read_text();decl=re.search(r'class ReadModule\s*\{.*?^};',header,re.S|re.M)[0]
    (out/'lifetime_read_module.inc').write_text(decl+'\n')
    s=(src/'src/game/read.cpp').read_text()
    code='#if RE4DC_RESET_HEAP_FIX\n'+fn(s,'ModuleMemFree')[0]+'\n#define Mem_free ModuleMemFree\n#endif\n'+fn(s,'InitModule')[0]+'\n#undef Mem_free\n'
    code+='\n'.join(fn(s,n)[0]for n in ['EmReadInit','pullEmModule','readEm'])+'\n'
    (out/'lifetime_actual_read.inc').write_text(code)
    flags=['-O1','-g','-fsanitize=address,undefined','-fno-sanitize-recover=all','-fno-omit-frame-pointer','-fno-pie','-no-pie','-pthread']
    defs=['-DRE4DC_GAME=1','-DRE4DC_RESET_HEAP_FIX='+str(fix),'-DRE4DC_MOTION_RESERVE=1','-DRE4DC_MOTION_RESERVE_PACK=1','-DRE4DC_MOTION_PRESSURE_BACKING=1','-DRE4DC_MOTION_PRESSURE_BYTES=262144','-DRE4DC_MOTION_BOUNDED_R11F=1','-DRE4DC_SUBSCREEN=1','-DRE4DC_MOTION_COLD_POOL=262144','-DRE4DC_MOTION_RESERVE_SPILL=524288','-DRE4DC_MOTION_OOM_EVICT=1','-DRE4DC_MOVIE_HEAP_EVICT=1']
    cmd=[os.environ.get('CXX','g++'),'-std=c++17',*flags,*defs,'-Wall','-Wextra','-fpermissive','-Wno-misleading-indentation','-I'+str(out),'-I'+str(src/'port/dreamcast/game/platform/include'),str(HERE/'motion_lifetime_host.cpp'),str(out/'osalloc.o'),'-Wl,--wrap=OSFreeToHeap','-o',str(out/'test')]
    command(cmd,out/'compile.txt')
    rows=[]
    for case in ['normal','reset','predrain-control','pin-live','pin-reset','epilog-order','slot-failure','bind-failure-retry','borrowed-header']:
        result=command([out/'test',case],out/(case+'.txt'),15);print(result,end='');rows.append({'case':case,'output':result})
    return {'reset_heap_fix':fix,'sanitizers':'ASan + UBSan','cases':rows}


def build_event(out,src):
    out.mkdir();s=(src/'src/game/event.cpp').read_text();header=(src/'include/event.h').read_text()
    decls=[]
    for name in ['DatTblEntry','EvtHeader','EvtBinEntry']:
        decls.append(re.search(r'struct '+name+r'\s*\{.*?^};',header,re.S|re.M)[0])
    (out/'event_admission_types.inc').write_text('\n'.join(decls)+'\n')
    methods=['EventMgr::SetEvd','EventMgr::SetBin','DatTbl::SetDat','DatTbl::ChkDat']
    (out/'event_admission_methods.inc').write_text('\n'.join(fn(s,n)[0]for n in methods)+'\n')
    flags=['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all','-fno-omit-frame-pointer','-fno-pie','-no-pie']
    # Release source treats 0x8... addresses as signed-negative. A fixed mmap
    # retains that real guard; ASan ShadowGap forbids this range, hence UBSan only.
    argv=[os.environ.get('CXX','g++'),'-std=c++17',*flags,'-Wall','-Wextra','-fpermissive','-I'+str(out),str(HERE/'motion_event_admission_host.cpp'),'-o',str(out/'test')]
    command(argv,out/'compile.txt');result=command([out/'test'],out/'run.txt',15);print(result,end='')
    return {'sanitizers':'UBSan only; fixed negative32-bit mmap preserves original source guard','output':result}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);p.add_argument('--source-ref',default='d4a3b31fac3362937a3f21eaa874e07be94fd061');a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=False)
    ref=subprocess.check_output(['git','-C',str(REPO),'rev-parse',a.source_ref],text=True).strip()
    src,pins,order=export_source(a.out,ref)
    rows=[build_motion(a.out/('reset-fix'+str(fix)),src,fix)for fix in [0,1]]
    event=build_event(a.out/'event',src)
    receipt={'reviewed_function_pins':reviewed_pins(src),'build_contract':{'capacity':0,'resume':0,'lease_lean':0,'release_SDK_DEBUG':0,'OSFREE_CHECK':0,'reserve':1,'reserve_pack':1,'pressure_backing':1,'pressure_bytes':262144,'reset_heap_fix':[0,1],'external_movie_cabin_actor_guards':'not executed; no overlapping external owners in host fixture'},'event_admission':event,'scope':'Actual-source release SDK host only; forced ownership boundary tests, synthetic FCVs, external DLL/effect/UI and transport boundaries; no guest, target or gameplay overlap proof','source_revision':ref,'source_sha256':pins,'reset_static_order':order,'variants':rows,'test_sha256':{p.name:sha(p.read_bytes())for p in [Path(__file__),HERE/'motion_lifetime_host.cpp',HERE/'motion_event_admission_host.cpp']}}
    (a.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
