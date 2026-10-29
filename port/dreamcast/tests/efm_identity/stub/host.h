#ifndef RE4DC_EFM_IDENTITY_HOST_H
#define RE4DC_EFM_IDENTITY_HOST_H

#include <cstddef>
#include <cstdarg>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <climits>
#include <new>

// The production manager uses source words for pointer parking. On this 64-bit host,
// unsigned long holds the pointer; the production SH-4 build retains its 32-bit types.
#define TYPES_H
typedef signed char s8;
typedef signed short s16;
typedef signed long s32;
typedef signed long long s64;
typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned long u32;
typedef unsigned long long u64;
typedef float f32;
typedef double f64;
typedef int BOOL;
#define RE4_MEM_LO 0UL
#define RE4_MEM_HI ULONG_MAX
#define PLACEMENT_NEW_DEFINED
#define RE4DC_OBJECT_DEMAND 1
#define RE4DC_ENEMY_DEMAND 1
#define RE4DC_PARTS_DEMAND 0
#define RE4DC_MODELINFO_DEMAND 0
#define RE4DC_SUBSCREEN 0
#define RE4DC_HEAP4_PARTS_RESERVE 0
#define RE4DC_PS2_WORLD_SOURCE_OWNER 0
#define RE4DC_PS2_WORLD_R11F_OWNER 0
// The host's 64-bit Pool header is larger than the SH-4's +64 slot offset, so use
// the production bridge's out-of-line workAt. The test source enables the EFM index
// only after including this header; the index's ordered behavior is independent of lookup ABI.
#define RE4DC_WORKAT_INLINE 0
#define RE4DC_ATCHK_LIST 1
#ifndef RE4DC_EFM_CLASS_IDENTITY
#define RE4DC_EFM_CLASS_IDENTITY 1
#endif

void* Debug_alloc(u32 size, int);
void Debug_free(void*);
#include "cManager.h"

struct cModel {};
struct EfmCore { u16 flg; u8 kind; cModel* pEm; };
struct EfmWork { EfmCore core; };
typedef EfmWork Efm04Work;
typedef EfmWork Efm05Work;
typedef EfmWork Efm09Work;
class cParts : public cUnit {};
class cModelInfo : public cUnit {};
class cEm : public cUnit {};
class cObj : public cUnit {
public:
    u32 id;
    EfmWork efm04, efm05, efm09;
    cObj() : id(0) { be_flag = 1; pNext = 0; }
    virtual ~cObj() {}
    void push();
};
class cObjMgr : public cManager<cObj> {
public:
    bool fail_construct;
    cObjMgr();
    virtual void* memAlloc(u32 size);
    virtual void memFree(void* p);
    virtual void memClear(cObj* p, u32 size);
    virtual void log(const char* fmt, ...);
    virtual void destroy(cObj* p);
    virtual int construct(cObj* p, u32 id);
};
extern cObjMgr ObjMgr;

struct EfmHostGame { u32 Debug_flg[4]; u8 stage_no, room_no; };
extern EfmHostGame* pG;
struct EfmHostHeap { int handle; };
extern EfmHostHeap Heap[16];
enum { MEM_HEAP_CURRENT = 0 };
int MemGetCurrentHeap();
void* mem_alloc(u32 bytes, const char*, int, int, int);
void memclr_asm(void* p, u32 bytes);
extern "C" void re4dc_log(const char*, ...);
extern "C" void re4dc_missing(const char*);
extern "C" void OSFreeToHeap(int, void*);

#endif
