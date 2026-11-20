// Effect equivalence check (lane eng-e2): the two sides' interfaces for the driver (check_main.cpp).
#ifndef FX_CHECK_H
#define FX_CHECK_H
#define ORIG_POOL 512
#define ORIG_GENS 64
// original side (check_orig.cpp + orig_fx.cpp)
void orig_init();
void orig_data_load(const void* effdata, unsigned owner);
void orig_est_start(u32 owner, int id, int parts, const Vec* pos, const Vec* rot, u32 seed);
void orig_tick();
void orig_bind_archive(const void* base, unsigned bytes);
cEsp* orig_slot(unsigned i);
extern unsigned orig_uid[ORIG_POOL];
extern unsigned orig_log_count, orig_efm, orig_kind1;
// native side (fx.cpp built with FX_HOST_CHECK; entry points renamed native_*)
extern "C" int native_EspDataLoad(u32 addr, u32 owner, int mode);
extern "C" void native_EstSet(int a, int b, Vec* pos, Vec* rot, int c, int d, int e, int f, u32 g, void* h);
#endif
