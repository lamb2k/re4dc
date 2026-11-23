// skchain_kind.cpp (lane eng-skel1): the chain object's kind (0x1D) in the object pool of re4ref's svc builds. The
// reference has no obj.cpp construct for it (host_em.cpp constructs the kinds registered in ObjInitFunc): odump registers
// game/obj1d.cpp's class here; native builds have services/cloth/chain.cpp's, which registers itself first.
#include "obj.h"
#include <new>

class cObjChain : public cObj {
public:
    virtual void move();
    virtual ~cObjChain() {}
};
extern void (*ObjInitFunc[0x40])(cObj*);
static void chain_init(cObj* p) { new (p) cObjChain(); }
extern "C" void skchain_kind_register(void)
{
    if (!ObjInitFunc[0x1D]) ObjInitFunc[0x1D] = chain_init;
}
