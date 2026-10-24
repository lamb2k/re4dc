#!/usr/bin/env python3
"""Exercise the real VRAM allocator without dereferencing simulated VRAM."""
from pathlib import Path
import subprocess, tempfile

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'game/platform/vram_pages.cpp'
PROGRAM = r'''
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstdarg>
extern "C" {
void pvr_mem_initialize(void*, size_t);
void pvr_mem_reset();
void* pvr_mem_malloc(size_t);
void pvr_mem_free(void*);
size_t pvr_mem_available();
extern volatile unsigned re4dc_vram_arena_class;
void re4dc_log(const char*, ...) {}
}
static uintptr_t alloc(unsigned cls, size_t n) {
    re4dc_vram_arena_class=cls;
    auto p=reinterpret_cast<uintptr_t>(pvr_mem_malloc(n));
    re4dc_vram_arena_class=0;
    return p;
}
int main() {
    constexpr uintptr_t base=0xa4600000, limit=0xa47f2000, end=0xa4800000;
    constexpr unsigned pool=end-base;
    pvr_mem_initialize(reinterpret_cast<void*>(base),pool);pvr_mem_reset();
    auto glyph=alloc(2,8192);
#if NO_TOP
    assert(glyph==base);
#else
    assert(glyph==end-8192);
#endif
    auto room=alloc(1,2048);assert(room && room!=glyph);
    auto core=alloc(2,8224);assert(core && !(core&2047));
#if NO_TOP
    assert(core+8224<=limit);
#endif
    pvr_mem_free(reinterpret_cast<void*>(glyph));
    pvr_mem_free(reinterpret_cast<void*>(core));
    pvr_mem_free(reinterpret_cast<void*>(room));assert(pvr_mem_available()==pool);
    // Fill everything below the cutoff: only the final 56 KiB remains free.
    auto fill=alloc(1,limit-base);assert(fill==base);
    auto tail=alloc(2,32);
#if NO_TOP
    assert(!tail);assert(pvr_mem_available()==end-limit);
#else
    assert(tail==end-32);pvr_mem_free(reinterpret_cast<void*>(tail));
#endif
    // The experiment must not reserve/discard that tail for room or dynamic use.
    auto dynamic=alloc(0,2048);assert(dynamic==limit);
    auto room2=alloc(1,2048);assert(room2==limit+2048);
    pvr_mem_free(reinterpret_cast<void*>(dynamic));
    pvr_mem_free(reinterpret_cast<void*>(room2));
    pvr_mem_free(reinterpret_cast<void*>(fill));assert(pvr_mem_available()==pool);
    // Repeated room turnover preserves the surviving core and reuses all room bytes.
    core=alloc(2,8192);auto free_before=pvr_mem_available();
    for(unsigned r=0;r<20;++r){
        uintptr_t blocks[80];
        for(unsigned i=0;i<80;++i){blocks[i]=alloc(1,32+(i%13)*320);assert(blocks[i]);}
        for(unsigned i=0;i<80;++i)pvr_mem_free(reinterpret_cast<void*>(blocks[(i*37)%80]));
        assert(pvr_mem_available()==free_before);
    }
    pvr_mem_free(reinterpret_cast<void*>(core));assert(pvr_mem_available()==pool);
    puts("allocator placement, hard cutoff, tail access and 20 room turnovers PASS");
}
'''

def run():
    with tempfile.TemporaryDirectory(prefix='arena23-host-') as td:
        tmp=Path(td);(tmp/'dc').mkdir()
        (tmp/'kos.h').write_text('#include <cstddef>\n#define irq_disable_scoped() ((void)0)\n')
        (tmp/'dc/pvr.h').write_text('typedef void* pvr_ptr_t;\n')
        (tmp/'re4dc_platform.h').write_text('extern "C" void re4dc_log(const char*, ...);\n')
        (tmp/'driver.cpp').write_text(PROGRAM)
        for no_top in (0,1):
            for vq in (0,1):
                out=tmp/f'allocator-{no_top}-{vq}'
                subprocess.run(['g++','-std=c++17','-O2','-Wall','-Wextra',
                    f'-I{tmp}','-DRE4DC_VRAM_PAGES=1','-DRE4DC_VRAM_ROOM_ARENA=1',
                    f'-DRE4DC_VRAM_ROOM_ARENA_NO_TOP={no_top}',
                    f'-DRE4DC_VRAM_PAGES_VQ_ONLY={vq}', f'-DNO_TOP={no_top}',
                    str(SOURCE),str(tmp/'driver.cpp'),'-o',str(out)],check=True)
                subprocess.run([str(out)],check=True)
                print(f'NO_TOP={no_top} VQ_ONLY={vq} PASS',flush=True)
if __name__=='__main__':run()