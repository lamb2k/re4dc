// hostref: cEmMgr::construct for the player only. The original (em.cpp) places the class for any id:
// the player, partners, every enemy module and the 17 object classes; the E1 reference hosts Leon, so
// id 0 with pl_type 0 builds cPlLeon exactly as the original does, and the tail (serial, emset_no,
// be_flag 0x40 | 0x02000000, subArc2) is the original's. Any other id is a logged refusal.
#include "hostref.h"
#include "em.h"
#include "player.h"
#include "global.h"

int cEmMgr::construct(cEm* p, u32 id)
{
    if (id != 0 || pG->pl_type != 0) {
        host_stub_hit("cEmMgr::construct(other)");
        return 0;
    }
    p = new (p) cPlLeon;
    p->serial = Guid;
    Guid++;
    p->emset_no = 0xFF;
    p->be_flag |= 0x40;
    p->id = id;
    p->be_flag |= 0x02000000;
    p->subArc2 = p->subArc;
    return 1;
}

// cObjMgr::construct (obj.cpp) for the classes a module registers in ObjInitFunc (the held weapon:
// 0x21 cObjRuger, 0x27 cObjMauser from the wep02 module), the original's default branch and tail.
// The 30 built-in object classes of the original switch are outside the E1 reference: refused, logged.
#include "obj.h"
#include "wep_mod.h"
int cObjMgr::construct(cObj* p, int id)
{
    if (id > 0x3F || !ObjInitFunc[id]) {
        host_stub_hit("cObjMgr::construct(other)");
        return 0;
    }
    ObjInitFunc[id](p);
    p->serial = Guid;
    Guid++;
    p->id = id;
    return 1;
}
int cObjMgr::construct(cObj* p, u32 id)
{
    return construct(p, (int) id);
}
// cManager<T>::destroyNow (objRocket.cpp, the original's template, instantiated there for cObj).
template <class T>
void cManager<T>::destroyNow(T* p)
{
    u8 f = flag;

    flag = 0;
    destroy(p);
    flag = f;
}
template void cManager<cObj>::destroyNow(cObj* p);

cObjMgr ObjMgr;
cEmMgr EmMgr;   // em.cpp


// include/atari_init.h declares cAtariInfo::init's link name with the seven float parameters first
// (atariInitF): on the PowerPC, and on the SH-4, int and float arguments travel in separate register
// files, so the order of the two groups does not matter there. On the i386 every argument is on the
// stack in declaration order, so the declared name gets a body that passes them on in init's order.
#include "atari_init.h"
void atariInitF(cAtariInfo* at, f32 x, f32 y, f32 z, f32 rx, f32 rz, f32 w, f32 h, int parts, int flags, int cnt)
{
    at->init(parts, flags, cnt, x, y, z, rx, rz, w, h);
}
