
#include <cassert>
#include <cstring>
#include <cstdint>
using u8=unsigned char;using s32=int;using u32=std::uintptr_t;
struct Pend{void(*dvd)(s32,void*);void(*arq)(u32);void*obj;s32 res;};Pend g_pend[8];u32 g_pendN;unsigned irq_on=1;
int irq_disable(){int old=irq_on;irq_on=0;return old;}void irq_restore(int old){irq_on=old;}
void pend_push(const Pend& p)
{
    int old = irq_disable();
    bool ok = g_pendN < 8;
    if (ok) g_pend[g_pendN++] = p;
    irq_restore(old);
    if (!ok) {   // cannot happen with 4 stream works (one read + one DMA each): complete now
        if (p.dvd) p.dvd(p.res, p.obj);
        else p.arq((u32) p.obj);
    }
}
void re4dc_audio_pend_run(void)
{
    Pend run[8];
    int old = irq_disable();
    u32 n = g_pendN;
    memcpy(run, g_pend, n * sizeof(Pend));
    g_pendN = 0;
    irq_restore(old);
    for (u32 i = 0; i < n; i++) {
        if (run[i].dvd) {
            u8* fi = (u8*) run[i].obj;
            *(s32*) (fi + 0x0C) = 0;             // DVD_STATE_END
            *(u32*) (fi + 0x20) = (u32) run[i].res;
            run[i].dvd(run[i].res, run[i].obj);
        } else {
            run[i].arq((u32) run[i].obj);
        }
    }
}
unsigned completed;bool requeue=true,empty_while_executing,inline_overflow;
void child(u32){assert(irq_on);++completed;empty_while_executing|=g_pendN==0;}
void parent(u32){assert(irq_on&&g_pendN==0);empty_while_executing=true;++completed;if(requeue){requeue=false;pend_push(Pend{nullptr,child,nullptr,0});}}
void overflow(u32){assert(irq_on&&g_pendN==8);inline_overflow=true;}
int main(){pend_push(Pend{nullptr,parent,nullptr,0});assert(g_pendN==1);re4dc_audio_pend_run();assert(completed==1&&empty_while_executing&&g_pendN==1);re4dc_audio_pend_run();assert(completed==2&&!g_pendN);
for(unsigned i=0;i<8;++i)pend_push(Pend{nullptr,child,nullptr,0});pend_push(Pend{nullptr,overflow,nullptr,0});assert(inline_overflow&&g_pendN==8);re4dc_audio_pend_run();assert(completed==10&&!g_pendN);}
