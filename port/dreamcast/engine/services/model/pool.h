// pool.h: the engine's record pools (lane eng-svc4; docs/engine/SERVICES.md section 27). One set of routines for the
// fixed pools the services own (parts, model infos, collision pieces): the first free slot, a given slot, the alive
// list (newest first), destruction now (flag 0) or marked for the manager's sweep (flags 1 and 2), the peak count.
// The record tables underneath (workAt, prepareWork, arrayAlloc) are the engine's (services/managers.cpp); the
// record types keep their own alive test (cSat adds its active flag). A service gives a record type these bodies with
// ENG_POOL(T) (explicit specializations of the manager's entry points, so every caller reaches them).
#pragma once
#include "cManager.h"

extern "C" __attribute__((weak)) u32 eng_pool_full;   // create calls that found no free slot (every pool)
__attribute__((weak)) u32 eng_pool_full;

namespace eng_pool {

constexpr u32 kUsed = 0x601;   // be_flag: slot in use (alive, or marked for deletion)

inline bool in_ram(const void* p) { return (u32) p >= RE4_MEM_LO && (u32) p <= RE4_MEM_HI; }

template <class T> void list_front(cManager<T>* m, T* p)
{
    for (T* q = m->pAlive; q; q = (T*) q->pNext) {
        if (q == p) {
            m->log("%s::addListFront() ERROR SET x2 0x%08X", m->name, p);
            return;
        }
    }
    p->pNext = m->pAlive;
    m->pAlive = p;
}

template <class T> int list_remove(cManager<T>* m, T* p)
{
    if (!p->isAlive()) {
        m->log("%s::deleteList() WORK IS ALREADY DEAD 0x%08X", m->name, p);
        return 0;
    }
    if (m->pAlive == p) {
        m->pAlive = (T*) p->pNext;
        p->pNext = 0;
        return 1;
    }
    for (T* q = m->pAlive; q->pNext; q = (T*) q->pNext) {
        if (q->pNext == p) {
            q->pNext = p->pNext;
            p->pNext = 0;
            return 1;
        }
    }
    m->log("%s::deleteList() WORK CANT FOUND 0x%08X", m->name, p);
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
    if (m->nArray - n < m->nArray / m->warnDiv)
        m->log("countActiveWork() warning, %s work remain under 1/%d", m->name, m->warnDiv);
    return n;
}

// The first free slot.
template <class T> T* create(cManager<T>* m, int id)
{
    for (u32 i = 0; i < m->nArray; i++) {
        T* p = m->workAt(i);
        if (p && (p->be_flag & kUsed)) continue;
        if (!m->prepareWork(i, 1) || !(p = m->workAt(i))) return 0;
        m->memClear(p, m->size);
        if (m->construct(p, id) == 0) {
            m->log("create()->construct() failed. %s id:%d", m->name, id);
            return 0;
        }
        list_front(m, p);
        count(m);
        return p;
    }
    eng_pool_full++;
    m->log("create() failed. %s work is full id:%d", m->name, id);
    return 0;
}

// Slot `no`, which must be free.
template <class T> T* create_at(cManager<T>* m, int id, u32 no)
{
    if (no >= m->nArray || !m->prepareWork(no, 1)) return 0;
    T* p = m->workAt(no);
    if (!p) return 0;
    if (p->be_flag & kUsed) {
        m->log("create() failed %s id:%d", m->name, id);
        return 0;
    }
    m->memClear(p, m->size);
    m->construct(p, id);
    list_front(m, p);
    count(m);
    return p;
}

// Off the alive list, then destroyed (flag 0) or marked for the sweep (flag 1: 0x600, flag 2: 0x200).
template <class T> void destroy(cManager<T>* m, T* p)
{
    if (!in_ram(p)) {
        if (p != 0) m->log("%s::destroy() ERROR, INVALID  PTR %08X", m->name, p);
        return;
    }
    list_remove(m, p);
    switch (m->flag) {
    case 0:
        if (!p->isAlive()) {
            m->log("%s::destroy() delete but not alive", m->name);
            return;
        }
        p->~T();
        p->be_flag = 0;
        break;
    case 1: p->be_flag |= 0x600; break;
    case 2: p->be_flag |= 0x200; break;
    default: m->log("%s::destroy() INVALID ID %d", m->name, m->flag); break;
    }
}

}   // namespace eng_pool

#define ENG_POOL(T)                                                                                              \
    template <> T* cManager<T>::create(int id) { return eng_pool::create(this, id); }                            \
    template <> T* cManager<T>::create() { return eng_pool::create(this, 0); }                                   \
    template <> T* cManager<T>::create(int id, u32 no) { return eng_pool::create_at(this, id, no); }             \
    template <> u32 cManager<T>::countActiveWork() { return eng_pool::count(this); }                             \
    template <> void cManager<T>::destroy(T* p) { eng_pool::destroy(this, p); }
