#ifndef CMANAGER_H
#define CMANAGER_H

#include "types.h"

// Placement new for the managers' construct(): the work is constructed in place.
#ifndef PLACEMENT_NEW_DEFINED
#define PLACEMENT_NEW_DEFINED
inline void* operator new(unsigned int, void* p) { return p; }
#endif

// Base of every managed work object (cLight, cEsp, cObj, cEm, ...).
// GCC 2.95 places the vptr after the fields of the class that introduces it.
class cUnit {
public:
    u32 be_flag;  // 0x0  bit0: alive, bit9/10: reserved-alive bits (0x601 = in use)
    cUnit* pNext;  // 0x4  active list link
    // 0x8 vptr

    cUnit() {}
    // Event::Event stores be_flag before its vptr and member constructors: only a base-class
    // initializer runs there.
    cUnit(u32 flag) { be_flag = flag; }
    virtual ~cUnit() { be_flag &= ~0x601; }
    virtual void beginEvent() {}
    virtual void endEvent() {}
    // Works are pool-managed: `delete work` only runs the destructor (be_flag cleared).
    // size_t is `unsigned int` for this compiler; with u32 (unsigned long) GCC 2.95 would not
    // treat this as the usual deallocation function.
    void operator delete(void*, unsigned int) {}
    // addListBack's `p->next = 0` goes through this: the argument copy gives the zero register a
    // lifetime of 2 luids, which is what makes loop.c hoist `li rN, 0` out of createBack's loop
    void setNext(cUnit* n) { pNext = n; }
    // deleteList / destroy test the work through this (a derived class may hide it with its own
    // test: cSat adds its active flag, which is why cManager<cSat>::destroy's check differs)
    int isAlive() { return (be_flag & 0x201) == 1; }
};

// Event slot storage exists before construction and after destruction. Byte access
// requires currently allocated pool storage; this is not stale-pointer validation.
#if !defined(__PPC__) && defined(RE4DC_EVENT_MANAGER_STORAGE_FLAGS) && RE4DC_EVENT_MANAGER_STORAGE_FLAGS
class Event;
struct re4dcEventStorageFlags {
    enum { offset = __builtin_offsetof(cUnit, be_flag) };
    typedef char FlagWidthMustBeFour[(sizeof(u32) == 4) ? 1 : -1];
    static u32 load(const Event* p) {
        u32 value;
        __builtin_memcpy(&value, (const unsigned char*)p + offset, sizeof(value));
        return value;
    }
    static void store(Event* p, u32 value) {
        __builtin_memcpy((unsigned char*)p + offset, &value, sizeof(value));
    }
    static void set(Event* p, u32 mask) { store(p, load(p) | mask); }
    static int alive(const Event* p) { return (load(p) & 0x201) == 1; }
};
template<class T> struct re4dcManagerStorageFlags {
    static u32 load(T* p) { return p->be_flag; }
    static void store(T* p, u32 value) { p->be_flag = value; }
    static void set(T* p, u32 mask) { p->be_flag |= mask; }
    static int alive(T* p) { return p->isAlive(); }
};
template<> struct re4dcManagerStorageFlags<Event> : re4dcEventStorageFlags {};
#define RE4DC_MANAGER_FLAG_LOAD(p) re4dcManagerStorageFlags<T>::load(p)
#define RE4DC_MANAGER_FLAG_STORE(p, value) re4dcManagerStorageFlags<T>::store(p, value)
#define RE4DC_MANAGER_FLAG_SET(p, mask) re4dcManagerStorageFlags<T>::set(p, mask)
#define RE4DC_MANAGER_IS_ALIVE(p) re4dcManagerStorageFlags<T>::alive(p)
#define RE4DC_EVENT_IS_ALIVE(p) re4dcEventStorageFlags::alive(p)
#else
#define RE4DC_MANAGER_FLAG_LOAD(p) p->be_flag
#define RE4DC_MANAGER_FLAG_STORE(p, value) p->be_flag = value
#define RE4DC_MANAGER_FLAG_SET(p, mask) p->be_flag |= mask
#define RE4DC_MANAGER_IS_ALIVE(p) p->isAlive()
#define RE4DC_EVENT_IS_ALIVE(p) p->isAlive()
#endif

// GAME_ATCHK_LIST (game30.mk): every change of an alive list (and of the work array under it)
// bumps a generation, so EmAtCheck can keep the list's order in an array and trust it until the
// next change. One global array defined in at_mod.cpp (slot 1 cEm, 2 cObj, 0 every other type): a
// template static member would not do, since the room modules link their own private copy of a
// weak template static. The manager's layout is unchanged.
#if defined(RE4DC_ATCHK_LIST) && RE4DC_ATCHK_LIST
extern "C" u32 re4dc_alive_gen[4];
class cEm;
class cObj;
template <class T> struct re4dcAliveSlot { enum { v = 0 }; };
template <> struct re4dcAliveSlot<cEm> { enum { v = 1 }; };
template <> struct re4dcAliveSlot<cObj> { enum { v = 2 }; };
#define RE4DC_ALIVE_BUMP() (++re4dc_alive_gen[re4dcAliveSlot<T>::v])
#else
#define RE4DC_ALIVE_BUMP() ((void) 0)
#endif

// EfmDelete indexes mapped object slots by class, including dead slots. Its token must change
// when a slot is (re)constructed or its mapping changes, not when an alive-list link changes.
// Keep this separate from re4dc_alive_gen: collision and other list readers still need every
// add/delete notification. The object lives in esp_efm.cpp; no manager layout or ABI changes.
#if !defined(__PPC__) && defined(RE4DC_EFM_CLASS_IDENTITY) && RE4DC_EFM_CLASS_IDENTITY
extern "C" u32 re4dc_obj_class_gen;
class cObj;
template <class T> struct re4dcEfmClassSlot { static void bump() {} };
template <> struct re4dcEfmClassSlot<cObj> {
    static void bump() { if (re4dc_obj_class_gen != ~u32(0)) ++re4dc_obj_class_gen; }
};
#define RE4DC_EFM_CLASS_BUMP() re4dcEfmClassSlot<T>::bump();
#else
#define RE4DC_EFM_CLASS_BUMP()
#endif

// Fixed array work manager. Element stride is the runtime field `size`
// (derived work classes share the manager of their base type).
template <class T>
class cManager {
public:
    T* pArray;         // 0x00 work array
    u32 nArray;        // 0x04 number of works
    u32 size;          // 0x08 sizeof one work
    u8 flag;           // 0x0C
    T* pAlive;         // 0x10 head of active list (cUnit::next)
    u32 pAlivePush;     // 0x14  arrayPush (light.cpp keeps its own inSscrn globals): the room's pAlive while a debug tool works on its own array
    u32 pArrayPush;     // 0x18  arrayPush: the room's pArray (0 = not pushed)
    u32 nArrayPush;     // 0x1C  arrayPush: the room's nArray
    u32 maxAlive;      // 0x20 peak active count
    const char* name;  // 0x24
    u32 warnDiv;       // 0x28 countActiveWork() warns when free works < nArray / warnDiv
    void (**funcTbl)(T*);  // 0x2C per-type move handlers, set by init() (cLight::move calls funcTbl[type])
    // 0x30 vptr

    cManager(u32 size, u8 flag);
    // in-class: an out-of-class template definition is instantiated by the derived constructors'
    // base cleanup and lands before setName in light.cpp; the DOL has it after the destructors
    virtual ~cManager() {}
    virtual void* memAlloc(u32 size) = 0;
    virtual void memFree(void* p) = 0;
    virtual void memClear(T* p, u32 size) = 0;
    virtual void log(const char* fmt, ...);
    virtual void destroy(T* p);
    virtual int construct(T* p, u32 id) = 0;  // the id switch trees compare unsigned (cLightMgr, cCtrlMgr)

    void setName(const char* n);
    int roomInit();
    void init(void (**tbl)(T*));
    u32 countActiveWork();
    T* create(int id);
    T* create();
    T* create(int id, u32 no);
    T* createBack(int id);
    void destroyNow(T* p);   // objRocket.cpp instantiates it (pl_wep weaponRelease)
    T* getPrevWork(T* p);
    int dieCheck();
#if !defined(__PPC__)
    // Native reviewed managers preserve logical slots with demand backing.
    // Other managers keep their original contiguous arrays.
    T* workAt(u32 no) { return (T*)((u8*)pArray + size * no); }
    bool prepareWork(u32 no, u32 count) { return no < nArray && count <= nArray - no; }
#endif
    int arrayAlloc(u32 n);   // memFree + memAlloc(size * n) + memClear (em.cpp, game.cpp instantiate them)
    int arrayFree();         // 1 when there was an array
    // Debug print "alive/peak/total" (each minus `sub`) at (x, y) in colour `col`; returns the alive
    // count, 0 with an invalid array (game.cpp gameMainLoop's manager table).
    int dispWorkNum(int x, int y, int col, int sub);
    // Event brackets of every alive work (defined in sce_com.cpp, the only unit instantiating them).
    void beginEvent(int mode);
    void endEvent(int mode);
    // destroy() every alive work (debug tools: db_light LitLoadWork, Sscrn ss_main)
    void destroyAll();
    // Debug tools (tools.cpp ToolArrayPush/ToolWorkPop): park the room's array in pArrayPush/pAlivePush/nArrayPush and work
    // on a fresh Debug_alloc'd one of `n` works; arrayPop frees it and restores the room's. Both
    // return 1 when they did something.
    int arrayPush(int n);
    int arrayPop();

    int deleteList(T* p) {
        T* q;
        RE4DC_ALIVE_BUMP();
        if (!RE4DC_MANAGER_IS_ALIVE(p)) {
            log("%s::deleteList() WORK IS ALREADY DEAD 0x%08X", name, p);
            return 0;
        }
        q = pAlive;
        if (q == p) {
            pAlive = (T*)p->pNext;
            p->pNext = 0;
            return 1;
        }
        for (; q->pNext; q = (T*)q->pNext) {
            if (q->pNext == p) {
                q->pNext = p->pNext;
                p->pNext = 0;
                return 1;
            }
        }
        log("%s::deleteList() WORK CANT FOUND 0x%08X", name, p);
        return 0;
    }
    void addListFront(T* p) {
        T* q;
        RE4DC_ALIVE_BUMP();
        for (q = pAlive; q; q = (T*)q->pNext) {
            if (q == p) {
                log("%s::addListFront() ERROR SET x2 0x%08X", name, p);
                return;
            }
        }
        p->pNext = pAlive;
        pAlive = p;
    }
    void addListBack(T* p) {
        T* q;
        RE4DC_ALIVE_BUMP();
        for (q = pAlive; q; q = (T*)q->pNext) {
            if (q == p) {
                log("%s::addListBack() ERROR 0x%08X", name, p);
                return;
            }
        }
        q = pAlive;
        if (q == 0) {
            pAlive = p;
            return;
        }
        while (q->pNext) {
            q = (T*)q->pNext;
        }
        q->pNext = p;
        p->setNext(0);
    }
};

#if !defined(__PPC__)
class cParts;
template<> int cManager<cParts>::arrayAlloc(u32 n);
template<> int cManager<cParts>::arrayFree();
template<> cParts* cManager<cParts>::workAt(u32 no);
template<> bool cManager<cParts>::prepareWork(u32 no, u32 count);
template<> cParts* cManager<cParts>::getPrevWork(cParts* p);
class cModelInfo;
template<> int cManager<cModelInfo>::arrayAlloc(u32 n);
template<> int cManager<cModelInfo>::arrayFree();
template<> cModelInfo* cManager<cModelInfo>::workAt(u32 no);
template<> bool cManager<cModelInfo>::prepareWork(u32 no, u32 count);
template<> cModelInfo* cManager<cModelInfo>::getPrevWork(cModelInfo* p);
class cObj;
template<> int cManager<cObj>::arrayAlloc(u32 n);
template<> int cManager<cObj>::arrayFree();
#if defined(RE4DC_WORKAT_INLINE) && RE4DC_WORKAT_INLINE
// GAME_WORKAT_INLINE (game30.mk; port overhead, exact): the demand-backed managers' lookup inline
// when no pool is frozen for the sub screen (re4dc_frozen_pools), the array is the room's own (no
// debug push) and the index is in range: the slot table after the 64-byte pool header, as
// parts_bridge.cpp work_at reads it. Every other case takes the bridge (re4dc_work_at_*).
extern "C" u32 re4dc_frozen_pools;
cObj* re4dc_work_at_obj(cManager<cObj>* m, u32 no);
template<> inline cObj* cManager<cObj>::workAt(u32 no)
{
    if (__builtin_expect(!re4dc_frozen_pools && !pArrayPush && no < nArray && pArray != 0, 1)) {
        return ((cObj**) ((u8*) pArray + 64))[no];
    }
    return re4dc_work_at_obj(this, no);
}
#else
template<> cObj* cManager<cObj>::workAt(u32 no);
#endif
template<> bool cManager<cObj>::prepareWork(u32 no, u32 count);
template<> cObj* cManager<cObj>::getPrevWork(cObj* p);
class cEm;
template<> int cManager<cEm>::arrayAlloc(u32 n);
template<> int cManager<cEm>::arrayFree();
#if defined(RE4DC_WORKAT_INLINE) && RE4DC_WORKAT_INLINE
cEm* re4dc_work_at_em(cManager<cEm>* m, u32 no);
template<> inline cEm* cManager<cEm>::workAt(u32 no)
{
    if (__builtin_expect(!re4dc_frozen_pools && !pArrayPush && no < nArray && pArray != 0, 1)) {
        return ((cEm**) ((u8*) pArray + 64))[no];
    }
    return re4dc_work_at_em(this, no);
}
#else
template<> cEm* cManager<cEm>::workAt(u32 no);
#endif
template<> bool cManager<cEm>::prepareWork(u32 no, u32 count);
template<> cEm* cManager<cEm>::getPrevWork(cEm* p);
#endif

// Member initializer list, in this order: the stores come out in this order (body assignments
// would be rescheduled: the last use of the zero register first).
template <class T>
cManager<T>::cManager(u32 size, u8 flag)
    : size(size), flag(flag), maxAlive(0), name("Mgr"), warnDiv(10), pArray(0), nArray(0), pAlive(0), pAlivePush(0), pArrayPush(0), nArrayPush(0)
{
}

template <class T>
void cManager<T>::log(const char* fmt, ...)
{
}

template <class T>
void cManager<T>::setName(const char* n)
{
    name = n;
}

template <class T>
int cManager<T>::roomInit()
{
    #if defined(RE4DC_EFM_CLASS_IDENTITY) && RE4DC_EFM_CLASS_IDENTITY && !defined(__PPC__)
    RE4DC_EFM_CLASS_BUMP()
    #endif
    RE4DC_ALIVE_BUMP();
    pArray = 0;
    nArray = 0;
    pAlive = 0;
    pAlivePush = 0;
    pArrayPush = 0;
    nArrayPush = 0;
    maxAlive = 0;
    return 1;
}

template <class T>
void cManager<T>::init(void (**tbl)(T*))
{
    funcTbl = tbl;
    roomInit();
}

template <class T>
int cManager<T>::arrayFree()
{
    int ret;
    #if defined(RE4DC_EFM_CLASS_IDENTITY) && RE4DC_EFM_CLASS_IDENTITY && !defined(__PPC__)
    RE4DC_EFM_CLASS_BUMP()
    #endif
    RE4DC_ALIVE_BUMP();

    if (pArray) {
        memFree(pArray);
        pArray = 0;
        ret = 1;
    } else {
        ret = 0;
    }
    return ret;
}

template <class T>
int cManager<T>::arrayAlloc(u32 n)
{
    #if defined(RE4DC_EFM_CLASS_IDENTITY) && RE4DC_EFM_CLASS_IDENTITY && !defined(__PPC__)
    RE4DC_EFM_CLASS_BUMP()
    #endif
    RE4DC_ALIVE_BUMP();
    arrayFree();
    pArray = (T*) memAlloc(size * n);
    nArray = n;
    if (n) {
        memClear(pArray, size * n);
    }
    return 1;
}

// Works marked for deletion (flag 1 / 2 destroy): bit 0x400 deletes this frame, 0x200 arms 0x400.
template <class T>
int cManager<T>::dieCheck()
{
    u32 i;
    for (i = 0; i < nArray; i++) {
#if !defined(__PPC__)
        T* p = workAt(i);
#else
        T* p = (T*)((u8*)pArray + size * i);
#endif
#if !defined(__PPC__)
        if (!p) continue;
#endif
        if (RE4DC_MANAGER_FLAG_LOAD(p) & 0x601) {
            if (RE4DC_MANAGER_FLAG_LOAD(p) & 0x400) {
                delete p;
                RE4DC_MANAGER_FLAG_STORE(p, 0);
            } else if (RE4DC_MANAGER_FLAG_LOAD(p) & 0x200) {
                RE4DC_MANAGER_FLAG_SET(p, 0x400);
            }
        }
    }
    return 1;
}

template <class T>
u32 cManager<T>::countActiveWork()
{
    u32 n = 0;
    u32 i;
    for (i = 0; i < nArray; i++) {
#if !defined(__PPC__)
        T* p = workAt(i);
#else
        T* p = (T*)((u8*)pArray + size * i);
#endif
#if !defined(__PPC__)
        if (!p) continue;
#endif
        if (RE4DC_MANAGER_FLAG_LOAD(p) & 0x601) {
            n++;
        }
    }
    if (n > maxAlive) {
        maxAlive = n;
    }
    if (nArray - n < nArray / warnDiv) {
        log("countActiveWork() warning, %s work remain under 1/%d", name, warnDiv);
    }
    return n;
}

template <class T>
T* cManager<T>::create(int id)
{
    u32 i;
    for (i = 0; i < nArray; i++) {
#if !defined(__PPC__)
        T* p = workAt(i);
#else
        T* p = (T*)((u8*)pArray + size * i);
#endif
#if !defined(__PPC__)
        if (!p || !(RE4DC_MANAGER_FLAG_LOAD(p) & 0x601)) {
            if (!prepareWork(i, 1) || !(p = workAt(i))) return 0;
#else
        if (!(RE4DC_MANAGER_FLAG_LOAD(p) & 0x601)) {
#endif
            #if defined(RE4DC_EFM_CLASS_IDENTITY) && RE4DC_EFM_CLASS_IDENTITY && !defined(__PPC__)
            RE4DC_EFM_CLASS_BUMP()
            #endif
            memClear(p, size);
#if defined(RE4DC_EFM_CLASS_IDENTITY) && RE4DC_EFM_CLASS_IDENTITY && !defined(__PPC__)
            const int built = construct(p, id);
            #if defined(RE4DC_EFM_CLASS_IDENTITY) && RE4DC_EFM_CLASS_IDENTITY && !defined(__PPC__)
            RE4DC_EFM_CLASS_BUMP()
            #endif
            if (built == 0) {
#else
            if (construct(p, id) == 0) {
#endif
                log("create()->construct() failed. %s id:%d", name, id);
                return 0;
            }
            addListFront(p);
            countActiveWork();
            return p;
        }
    }
    log("create() failed. %s work is full id:%d", name, id);
    return 0;
}

template <class T>
T* cManager<T>::create()
{
    return create(0);
}

template <class T>
T* cManager<T>::create(int id, u32 no)
{
    if (no >= nArray) {
        return 0;
    }
#if !defined(__PPC__)
    if (!prepareWork(no, 1)) return 0;
    T* p = workAt(no);
    if (!p) return 0;
#else
    T* p = (T*)((u8*)pArray + size * no);
#endif
    if (RE4DC_MANAGER_FLAG_LOAD(p) & 0x601) {
        log("create() failed %s id:%d", name, id);
        return 0;
    }
    #if defined(RE4DC_EFM_CLASS_IDENTITY) && RE4DC_EFM_CLASS_IDENTITY && !defined(__PPC__)
    RE4DC_EFM_CLASS_BUMP()
    #endif
    memClear(p, size);
    construct(p, id);
    #if defined(RE4DC_EFM_CLASS_IDENTITY) && RE4DC_EFM_CLASS_IDENTITY && !defined(__PPC__)
    RE4DC_EFM_CLASS_BUMP()
    #endif
    addListFront(p);
    countActiveWork();
    return p;
}

template <class T>
int cManager<T>::arrayPush(int n)
{
    // `if (busy) return 0;` first: the `li r3,0` stays out of line after the body (an `if (free) {..;
    // return 1;} return 0;` gets it hoisted above the branch)
    if (pArrayPush != 0) {
        return 0;
    }
    #if defined(RE4DC_EFM_CLASS_IDENTITY) && RE4DC_EFM_CLASS_IDENTITY && !defined(__PPC__)
    RE4DC_EFM_CLASS_BUMP()
    #endif
    RE4DC_ALIVE_BUMP();
    pArrayPush = (u32) pArray;
    pArray = (T*) Debug_alloc(size * n, 1);
    nArrayPush = nArray;
    nArray = n;
    pAlivePush = (u32) pAlive;
    pAlive = 0;
    return 1;
}

template <class T>
int cManager<T>::arrayPop()
{
    if (pArrayPush == 0) {
        return 0;
    }
    #if defined(RE4DC_EFM_CLASS_IDENTITY) && RE4DC_EFM_CLASS_IDENTITY && !defined(__PPC__)
    RE4DC_EFM_CLASS_BUMP()
    #endif
    RE4DC_ALIVE_BUMP();
    Debug_free(pArray);
    // statement order found by brute force (zero stores last in the schedule, pAlive restored last)
    pArray = (T*) pArrayPush;
    nArray = nArrayPush;
    pArrayPush = 0;
    nArrayPush = 0;
    pAlive = (T*) pAlivePush;
    return 1;
}

template <class T>
void cManager<T>::destroyAll()
{
    u32 i;
    for (i = 0; i < nArray; i++) {
#if !defined(__PPC__)
        T* p = workAt(i);
#else
        T* p = (T*)((u8*)pArray + size * i);
#endif
#if !defined(__PPC__)
        if (!p) continue;
#endif
        if (RE4DC_MANAGER_IS_ALIVE(p)) {
            destroy(p);
        }
    }
}

// Release a work: unlink it from the active list, then run its destructor (flag 0) or only
// mark it (flag 1/2). Called on the manager object itself, so GCC inlines it.
template <class T>
inline void cManager<T>::destroy(T* p)
{
    if ((u32)p < RE4_MEM_LO || (u32)p > RE4_MEM_HI) {
        if (p != 0) {
            log("%s::destroy() ERROR, INVALID  PTR %08X", name, p);
        }
        return;
    }
    deleteList(p);
    switch (flag) {
    case 0:
        if (!RE4DC_MANAGER_IS_ALIVE(p)) {
            log("%s::destroy() delete but not alive", name);
            return;
        }
        delete p;
        RE4DC_MANAGER_FLAG_STORE(p, 0);
        break;
    case 1:
        RE4DC_MANAGER_FLAG_SET(p, 0x600);
        break;
    case 2:
        RE4DC_MANAGER_FLAG_SET(p, 0x200);
        break;
    default:
        log("%s::destroy() INVALID ID %d", name, flag);
        break;
    }
}

// The work in front of `p` in the array, or 0 at the front (scroll groups chain works this way).
template <class T>
T* cManager<T>::getPrevWork(T* p)
{
    p = (T*)((u8*)p - size);
    if ((u32)p < (u32)pArray || (u32)p >= (u32)pArray + size * (nArray - 1)) {
        return 0;
    }
    return p;
}

#if defined(RE4DC_GAME) && !defined(__PPC__)
extern "C" void re4dc_log(const char* fmt, ...);
#endif

template <class T>
T* cManager<T>::createBack(int id)
{
    int i;
#if !defined(__PPC__)
    // Port, demand-backed pools (parts_bridge.cpp): the source takes the highest free slot, and the
    // GameCube allocates the whole array with the room, so that choice never fails for memory. It is
    // kept whenever its page can be backed (the same slot index as the GameCube). Only when backing it
    // fails (heap 4 exhausted, as after the r100 post-house ambush) does the scan go on to the highest
    // free slot in a page that is already backed, instead of failing the create. Unbacked pages below
    // the failed one are never smaller, so they are not retried.
    int unbacked = -1;
#endif
    for (i = nArray - 1; i >= 0; i--) {
#if !defined(__PPC__)
        T* p = workAt(i);
#else
        T* p = (T*)((u8*)pArray + size * i);
#endif
#if !defined(__PPC__)
        if (!p || !(RE4DC_MANAGER_FLAG_LOAD(p) & 0x601)) {
            if (!p && unbacked >= 0) continue;
            if (!prepareWork(i, 1) || !(p = workAt(i))) {
                unbacked = i;
                continue;
            }
#else
        if (!(RE4DC_MANAGER_FLAG_LOAD(p) & 0x601)) {
#endif
            #if defined(RE4DC_EFM_CLASS_IDENTITY) && RE4DC_EFM_CLASS_IDENTITY && !defined(__PPC__)
            RE4DC_EFM_CLASS_BUMP()
            #endif
            memClear(p, size);
#if defined(RE4DC_EFM_CLASS_IDENTITY) && RE4DC_EFM_CLASS_IDENTITY && !defined(__PPC__)
            const int built = construct(p, id);
            #if defined(RE4DC_EFM_CLASS_IDENTITY) && RE4DC_EFM_CLASS_IDENTITY && !defined(__PPC__)
            RE4DC_EFM_CLASS_BUMP()
            #endif
            if (built == 0) {
#else
            if (construct(p, id) == 0) {
#endif
                log("create()->construct() failed. %s id:%d", name, id);
                return 0;
            }
            addListBack(p);
            countActiveWork();
#if defined(RE4DC_GAME) && !defined(__PPC__)
            if (unbacked >= 0) {
                re4dc_log("createBack: %s id 0x%x slot %d not backed (heap), took backed slot %d\n", name, id,
                          unbacked, i);
            }
#endif
            return p;
        }
    }
#if !defined(__PPC__)
    if (unbacked >= 0) return 0;  // backing failed and no backed slot was free: as before
#endif
    log("create() failed. %s work is full id:%d", name, id);
    return 0;
}

#endif
