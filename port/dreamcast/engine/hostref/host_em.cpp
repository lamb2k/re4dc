// hostref: cEmMgr::construct for the hosted characters. The original (em.cpp) places the class for any id:
// the player, partners, every enemy module and the 17 object classes. The reference hosts Leon (id 0 with
// pl_type 0: cPlLeon), and since lane eng-host2 the module characters: ids 1..0xE (the partners) and
// 0xF..0x3F (the enemy modules) take the module's archive from EmReadSearch and run the init function it
// registered, as the original's case 1..0xE and default branch do (host_actors.cpp serves the hosted
// modules and refuses the others). The id switch and the tail (serial, emset_no, be_flag 0x40 |
// 0x02000000, the id, subArc2) are the original's. The object classes (0x40..0x51, 0xFF) are refused, logged.
#include "hostref.h"
#include "em.h"
#include "player.h"
#include "global.h"

extern void (*EmInitFunc)(cEm* em);   // em.cpp
extern "C" void* EmReadSearch(u8 id, int a, int b);   // host_actors.cpp (read.cpp)

int cEmMgr::construct(cEm* p, u32 id)
{
    if (id == 0) {
        if (pG->pl_type != 0) {
            host_stub_hit("cEmMgr::construct(other player)");
            return 0;
        }
        p = new (p) cPlLeon;
    } else if (id <= 0x3F) {
        p->subArc = (PlArc*) EmReadSearch((u8) id, 0, 0);
        if (p->subArc == 0) return 0;
        EmInitFunc(p);
    } else {
        host_stub_hit("cEmMgr::construct(other)");
        return 0;
    }
    switch (p->id) {
    case 0x10: case 0x11: case 0x12: case 0x13: case 0x14: case 0x15: case 0x16: case 0x17: case 0x18:
    case 0x19: case 0x1A: case 0x1B: case 0x1C: case 0x1D: case 0x1E: case 0x1F: case 0x20:
        p->id = 0x10;
        break;
    }
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
