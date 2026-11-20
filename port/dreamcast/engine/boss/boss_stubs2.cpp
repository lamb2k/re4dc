// E2 boss slice (lane eng-boss): stubs of the objects and systems the hosted El Gigante code names but this slice does
// not host (the parasite object, chains and rocks of the other El Gigante forms, items, rides, the texture-render
// controller) and the oba collision object's constructor. Each logs its first calls and counts every call.
#include "global.h"
#include "model.h"
#include "em.h"
#include "obj.h"
#include "obj16.h"
#include "emrock.h"
#include "objBull.h"
// cObjTrolley as em_sub.cpp declares it (its own view of the trolley object)
class cObjTrolley : public cObj { public: int ckTrolleyRide(Vec* pos, u8* partsNo, Vec* out); };
#include "objYagura.h"
#include "ctrl.h"
#include "item.h"
#include "sce_at.h"
#include "pl_npc.h"
#include "pl_cloth.h"
#include "esp.h"
#include "etc_model.h"
#include "foot_shadow.h"
#include "e1_engine.h"
#include "e1_core.h"
#include <new>

#define STUB(name) e1_stub_hit(name, 0)

// The oba collision object (obj20.cpp, hosted): the engine object table constructs it (obj.cpp's case 0x20).
class cObjObaModel : public cObj {
public:
    virtual void move();
};
extern void (*ObjInitFunc[0x40])(cObj*);
static void oba_init(cObj* p) { new (p) cObjObaModel(); }
__attribute__((constructor)) static void e2_obj_kinds() { ObjInitFunc[0x20] = oba_init; }

// El Gigante's foot shadow table (drawing reads it; the engine draws no foot shadows in this slice)
FootShadowTbl Em2b_fs_tbl;

// ---- the parasite object (obj16) ----
extern "C" cObj* SetObj16(void*, void*, cModel*, cModel*, int, u8, Vec*, Vec*) { STUB("SetObj16"); return 0; }
extern "C" void MotSetObj16(cObj*, void*, int, int) { STUB("MotSetObj16"); }
void cObj16::clearLostWait() { STUB("cObj16::clearLostWait"); }
void cObj16::setScale(Vec*) { STUB("cObj16::setScale"); }
// ---- chains and rocks (the chained form, r11e) ----
cObjChain* SetChain(void*, void*, Vec*, Vec*) { STUB("SetChain"); return 0; }
void cObjChain::setChain(PenCloth*) { STUB("cObjChain::setChain"); }
void cObjChain::setParent(cModel*, int, Vec*, int) { STUB("cObjChain::setParent"); }
void cObjChain::setParent2(cModel*, int, Vec*, int, Vec*, int) { STUB("cObjChain::setParent2"); }
cEmRock* SetRock(void*, void*, Vec*, Vec*, u8) { STUB("SetRock"); return 0; }
void cEmRock::setSeFall(u8, u8, u8) { STUB("cEmRock::setSeFall"); }
void cEmRock::setEffFall(u8, u8) { STUB("cEmRock::setEffFall"); }
void cEmRock::setThrow(Vec*, EmAtkInfo*) { STUB("cEmRock::setThrow"); }
void cEmRock::setParent(cEm*, int, int) { STUB("cEmRock::setParent"); }
void cEmRock::setFall(EmAtkInfo*) { STUB("cEmRock::setFall"); }
void cEmRock::setBreakR11E() { STUB("cEmRock::setBreakR11E"); }
// ---- items, item areas ----
int cItemMgr::num(int) { STUB("cItemMgr::num"); return 0; }
// Engine form of the armed weapon's magazine (item.cpp trigger / reload for the handgun, new-game inventory as the
// reference fixture's "inv default": 10 rounds loaded; the spare count is this slice's assumption, see the lane doc).
static int mag = 10, spare = 50;
int cItemMgr::bulletNumTotal(int) { return mag + spare; }
u16 cItemMgr::bulletNum() { return (u16) mag; }
u32 cItemMgr::bulletNumCurrent() { return (u32) mag; }
int cItemMgr::trigger() { if (mag <= 0) return 0; mag--; return 1; }
int cItemMgr::reloadable() { return spare > 0 && mag < 10; }
int cItemMgr::reload() { int n = 10 - mag; if (n > spare) n = spare; mag += n; spare -= n; e1_stub_hit("cItemMgr::reload", n); return n > 0; }
int SceAtCreateItemAt(Vec*, u16, int, int, int, cModel*, int) { STUB("SceAtCreateItemAt"); return 0; }
void SceAtReserveItemAt(int, Vec*, u16, int, int, int) { STUB("SceAtReserveItemAt"); }
void SceAtCancelItemAt(int) { STUB("SceAtCancelItemAt"); }
int SceAtCheckSystemItemSet(u32, int*, int*, Vec*, Vec*) { STUB("SceAtCheckSystemItemSet"); return 0; }
void SceAtItemFlgOn(u16, u16) { STUB("SceAtItemFlgOn"); }
int SceAtItemFlgCk(u16, u16) { STUB("SceAtItemFlgCk"); return 0; }
// ---- other objects, the partner, ETC flags, the texture-render controller ----
static u16 etc_flag_word;
u16* GetEtcFlgPtr(int, int) { STUB("GetEtcFlgPtr"); return &etc_flag_word; }
void cSubChar::endDamage() { STUB("cSubChar::endDamage"); }
void cObjYagura::setVib() { STUB("cObjYagura::setVib"); }
int cObjTrolley::ckTrolleyRide(Vec*, u8*, Vec*) { return 0; }
int cObjBull::ckBullRide(Vec*, u8*, Vec*) { return 0; }
cCtrl* GetCtrlCtrl12() { STUB("GetCtrlCtrl12"); return 0; }
TexRenderMng* Ctrl12GetTexRenderEm2b(cCtrl*) { STUB("Ctrl12GetTexRenderEm2b"); return 0; }
u8 EspPullCoreKind() { static u8 kind = 0x45; return kind++; }   // the next effect kind (esp_app.cpp CoreKindTop)
