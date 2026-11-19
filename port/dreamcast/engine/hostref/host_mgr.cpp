// hostref: the work pools of the managers whose slot lookup the Dreamcast port moved out of line
// (include/cManager.h declares the specializations for non-PowerPC builds; the port defines them in
// parts_bridge.cpp with demand-backed pages). The reference uses the GameCube's own layout: one dense
// array of `size` byte works, slot n at pArray + size * n, as the generic cManager<T> does.
#include "hostref.h"
#include "model.h"
#include "obj.h"
#include "em.h"
#include "global.h"
#include "main_mem.h"
#include <string.h>

namespace {
template<class T> int array_free(cManager<T>* m)
{
    if (!m->pArray) return 0;
    m->memFree(m->pArray);
    m->pArray = 0;
    return 1;
}
template<class T> int array_alloc(cManager<T>* m, u32 n)
{
    array_free(m);
    m->nArray = n;
    m->pArray = (T*) m->memAlloc(m->size * n);
    if (n && m->pArray) memset(m->pArray, 0, m->size * n);
    return !n || m->pArray != 0;
}
template<class T> T* work_at(cManager<T>* m, u32 no)
{
    if (!m->pArray || no >= m->nArray) return 0;
    return (T*) ((u8*) m->pArray + m->size * no);
}
template<class T> bool prepare_work(cManager<T>* m, u32 first, u32 count)
{
    return m->pArray && count && first < m->nArray && count <= m->nArray - first;
}
template<class T> T* previous_work(cManager<T>* m, T* p)
{
    if (!m->pArray || !p) return 0;
    for (u32 i = 1; i < m->nArray; ++i)
        if (work_at(m, i) == p) return work_at(m, i - 1);
    return 0;
}
}

#define HOST_POOL(T)                                                                        \
    template<> int cManager<T>::arrayAlloc(u32 n) { return array_alloc(this, n); }          \
    template<> int cManager<T>::arrayFree() { return array_free(this); }                    \
    template<> T* cManager<T>::workAt(u32 n) { return work_at(this, n); }                   \
    template<> bool cManager<T>::prepareWork(u32 i, u32 n) { return prepare_work(this, i, n); } \
    template<> T* cManager<T>::getPrevWork(T* p) { return previous_work(this, p); }
HOST_POOL(cParts)
HOST_POOL(cModelInfo)
HOST_POOL(cObj)
HOST_POOL(cEm)
