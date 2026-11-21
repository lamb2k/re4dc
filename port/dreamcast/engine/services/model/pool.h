// pool.h: the engine's record pools (lane eng-svc4; docs/engine/SERVICES.md sections 27 and 41). One set of routines
// for the fixed pools the services own (parts, model infos, collision pieces, the character table, lights): the first
// free slot, the last free slot (createBack), a given slot, the alive list (newest first, or appended), destruction
// now (flag 0) or marked for the manager's sweep (flags 1 and 2), the peak count. The record tables underneath
// (workAt, prepareWork, arrayAlloc) are the engine's (services/managers.cpp); the record types keep their own alive
// test (cSat adds its active flag). A service gives a record type these bodies with ENG_POOL(T) (explicit
// specializations of the manager's entry points, so every caller reaches them); ENG_POOL_BACK(T) adds createBack.
//
// The pool refuses (lane eng-e1h): a create on a full table (0, counted in eng_pool_full) and a destroy of a record
// that is not alive by the record's base test, be_flag & 0x201 == 1 (already dead, or already marked for the sweep:
// counted in eng_pool_bad_free, nothing written). The original manager went on to mark such a record, which raised a
// dead slot back to "in use" for the sweep to destroy a second time.
//
// traits<T> (lane eng-e1h) is how the pool reaches a manager's own hooks: log, the record clear and the destructor
// call. The default is the manager's virtual functions, as before; a table with no manager object behind it (the
// lights: LightMgr is storage with no vtable in the engine images) specializes it.
#pragma once
#include "cManager.h"

extern "C" __attribute__((weak)) u32 eng_pool_full;       // create calls that found no free slot (every pool)
__attribute__((weak)) u32 eng_pool_full;
extern "C" __attribute__((weak)) u32 eng_pool_bad_free;   // destroy calls refused: the record was not alive
__attribute__((weak)) u32 eng_pool_bad_free;
// Control (test builds only, never a default): 1 = the destroy refusal off (the original's marking path), 2 = the
// full-table refusal off (create takes slot 0 even when it is in use). pooltest must FAIL with either.
extern "C" __attribute__((weak)) u32 eng_pool_control;
__attribute__((weak)) u32 eng_pool_control;

namespace eng_pool {

constexpr u32 kUsed = 0x601;   // be_flag: slot in use (alive, or marked for deletion)

inline bool in_ram(const void* p) { return (u32) p >= RE4_MEM_LO && (u32) p <= RE4_MEM_HI; }
// The base alive test (cUnit::isAlive), whatever the record type hides it with.
inline bool base_alive(const cUnit* p) { return (p->be_flag & 0x201) == 1; }

template <class T> struct traits {
    template <class... A> static void log(cManager<T>* m, const char* fmt, A... a) { m->log(fmt, a...); }
    static void clear(cManager<T>* m, T* p) { m->memClear(p, m->size); }
    static void dtor(T* p) { p->~T(); }
};

template <class T> void list_front(cManager<T>* m, T* p)
{
    for (T* q = m->pAlive; q; q = (T*) q->pNext) {
        if (q == p) {
            traits<T>::log(m, "%s::addListFront() ERROR SET x2 0x%08X", m->name, p);
            return;
        }
    }
    p->pNext = m->pAlive;
    m->pAlive = p;
}

// The original addListBack: refused when already listed, else appended (pNext cleared).
template <class T> void list_back(cManager<T>* m, T* p)
{
    T* q;
    for (q = m->pAlive; q; q = (T*) q->pNext) {
        if (q == p) {
            traits<T>::log(m, "%s::addListBack() ERROR 0x%08X", m->name, p);
            return;
        }
    }
    q = m->pAlive;
    if (q == 0) {
        m->pAlive = p;
        return;
    }
    while (q->pNext) q = (T*) q->pNext;
    q->pNext = p;
    p->pNext = 0;
}

template <class T> int list_remove(cManager<T>* m, T* p)
{
    if (!p->isAlive()) {
        traits<T>::log(m, "%s::deleteList() WORK IS ALREADY DEAD 0x%08X", m->name, p);
        return 0;
    }
    if (m->pAlive == p) {
        m->pAlive = (T*) p->pNext;
        p->pNext = 0;
        return 1;
    }
    for (T* q = m->pAlive; q && q->pNext; q = (T*) q->pNext) {
        if (q->pNext == p) {
            q->pNext = p->pNext;
            p->pNext = 0;
            return 1;
        }
    }
    traits<T>::log(m, "%s::deleteList() WORK CANT FOUND 0x%08X", m->name, p);
    return 0;
}

template <class T> u32 count(cManager<T>* m)
{
    u32 n = 0;
    for (u32 i = 0; i < m->nArray; i++) {
        T* p = m->workAt(i);
        if (p && (p->be_flag & kUsed)) n++;
    }
    if (n > m->maxAlive) m->maxAlive = n;
    if (m->warnDiv && m->nArray - n < m->nArray / m->warnDiv)
        traits<T>::log(m, "countActiveWork() warning, %s work remain under 1/%d", m->name, m->warnDiv);
    return n;
}

// Slot i made ready and constructed: 0 when the table cannot back it or the construction fails.
template <class T> T* build(cManager<T>* m, int id, u32 i)
{
    T* p;
    if (!m->prepareWork(i, 1) || !(p = m->workAt(i))) return 0;
    traits<T>::clear(m, p);
    if (m->construct(p, id) == 0) {
        traits<T>::log(m, "create()->construct() failed. %s id:%d", m->name, id);
        return 0;
    }
    return p;
}

// The first free slot.
template <class T> T* create(cManager<T>* m, int id)
{
    for (u32 i = 0; i < m->nArray; i++) {
        T* p = m->workAt(i);
        if (p && (p->be_flag & kUsed) && eng_pool_control != 2) continue;
        if (!(p = build(m, id, i))) return 0;
        list_front(m, p);
        count(m);
        return p;
    }
    eng_pool_full++;
    traits<T>::log(m, "create() failed. %s work is full id:%d", m->name, id);
    return 0;
}

// The last free slot, appended to the alive list (the original createBack: the partners take the table's top).
template <class T> T* create_back(cManager<T>* m, int id)
{
    for (int i = (int) m->nArray - 1; i >= 0; i--) {
        T* p = m->workAt(i);
        if (p && (p->be_flag & kUsed) && eng_pool_control != 2) continue;
        if (!(p = build(m, id, (u32) i))) return 0;
        list_back(m, p);
        count(m);
        return p;
    }
    eng_pool_full++;
    traits<T>::log(m, "create() failed. %s work is full id:%d", m->name, id);
    return 0;
}

// Slot `no`, which must be free.
template <class T> T* create_at(cManager<T>* m, int id, u32 no)
{
    if (no >= m->nArray || !m->prepareWork(no, 1)) return 0;
    T* p = m->workAt(no);
    if (!p) return 0;
    if (p->be_flag & kUsed) {
        eng_pool_full++;
        traits<T>::log(m, "create() failed %s id:%d", m->name, id);
        return 0;
    }
    traits<T>::clear(m, p);
    m->construct(p, id);
    list_front(m, p);
    count(m);
    return p;
}

// Off the alive list, then destroyed (flag 0) or marked for the sweep (flag 1: 0x600, flag 2: 0x200). A record that
// is not alive is refused (see the head of this file).
template <class T> void destroy(cManager<T>* m, T* p)
{
    if (!in_ram(p)) {
        if (p != 0) traits<T>::log(m, "%s::destroy() ERROR, INVALID  PTR %08X", m->name, p);
        return;
    }
    if (!base_alive(p) && eng_pool_control != 1) {
        eng_pool_bad_free++;
        traits<T>::log(m, "%s::destroy() refused, not alive 0x%08X", m->name, p);
        return;
    }
    list_remove(m, p);
    switch (m->flag) {
    case 0:
        if (!p->isAlive()) {
            traits<T>::log(m, "%s::destroy() delete but not alive", m->name);
            return;
        }
        traits<T>::dtor(p);
        p->be_flag = 0;
        break;
    case 1: p->be_flag |= 0x600; break;
    case 2: p->be_flag |= 0x200; break;
    default: traits<T>::log(m, "%s::destroy() INVALID ID %d", m->name, m->flag); break;
    }
}

}   // namespace eng_pool

#define ENG_POOL(T)                                                                                              \
    template <> T* cManager<T>::create(int id) { return eng_pool::create(this, id); }                            \
    template <> T* cManager<T>::create() { return eng_pool::create(this, 0); }                                   \
    template <> T* cManager<T>::create(int id, u32 no) { return eng_pool::create_at(this, id, no); }             \
    template <> u32 cManager<T>::countActiveWork() { return eng_pool::count(this); }                             \
    template <> void cManager<T>::destroy(T* p) { eng_pool::destroy(this, p); }
#define ENG_POOL_BACK(T) \
    template <> T* cManager<T>::createBack(int id) { return eng_pool::create_back(this, id); }
