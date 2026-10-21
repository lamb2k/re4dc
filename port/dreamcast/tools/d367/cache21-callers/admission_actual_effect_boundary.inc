// Actual owner mapping/Push/reference-count/final-dispatch execute. The five
// unrelated renderer/effect registries are exact-owner release boundaries.
struct cEspSystem{u32 ownerCnt[0xd3];} admission_effect_system,*g_pEspSys=&admission_effect_system;
static unsigned effect_release_dispatch[5];
static void espTexRelease(u32 owner){assert(owner==0x10);++effect_release_dispatch[0];}
static void estRelease(u32 owner){assert(owner==0x10);++effect_release_dispatch[1];}
static void sstRelease(u32 owner){assert(owner==0x10);++effect_release_dispatch[2];}
static void pathRelease(u32 owner){assert(owner==0x10);++effect_release_dispatch[3];}
static void efmRelease(u32 owner){assert(owner==0x10);++effect_release_dispatch[4];}
#define OWNER_ERR(owner,a,b) std::abort()
#define pLog (&admission_logger)
#include "admission_actual_effect_methods.inc"
#undef pLog
#undef OWNER_ERR
static void EspEmDataSwapPush(int em){
    assert(em==0x11||em==0x13);++swap_pushes;actual_EspEmDataSwapPush(em);
#if defined(RE4DC_FORWARD_ACTUAL)
    forward_effect_boundary(em);
#endif
}
