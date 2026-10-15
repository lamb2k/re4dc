// game/item_model: item pick-up models (D:/Bio4/Prog/item_model.cpp). The room's "ITM" block packs
// bin/tpl model pairs per item id; cItmSys (g_pItemModelSys, 0x100 entries) registers them and the
// item objects (obj16 etc.) fetch them with ItemGetBinTplAddr.
#include "item_model.h"
#include "main_mem.h"
#if RE4DC_ITEMS_CENSUS
extern "C" void re4dc_items_census_model(const char* kind, u32 owner, u32 id, const void* model); // eff_sys.cpp
#endif

cItmSys* g_pItemModelSys;

// Item model pack: offsets from the pack start to the id table, the model table and the
// texture table.
struct ItemModelPack {
    u32 x0;      // 0x00
    u32 ofsId;   // 0x04
    u32 ofsBin;  // 0x08
    u32 ofsTpl;  // 0x0C
};

struct ItemModelId {
    u16 id;      // 0x00
    u16 pad_2;
    u32 pad_4;
};

struct ItemModelIdTbl {
    u32 num;            // 0x00
    ItemModelId id[1];  // 0x04
};

// model / texture tables: offsets from the table start
struct ItemModelOfsTbl {
    u32 num;     // 0x00
    u32 ofs[1];  // 0x04
};

// Boot: same as the room init.
void ItemModelInit()
{
    ItemModelRoomInit();
}

// Room init: allocates a fresh (empty) item model table.
void ItemModelRoomInit()
{
    cItmSys* sys;

#line 94 "D:/Bio4/Prog/item_model.cpp"
    sys = (cItmSys*) MEM_ALLOC(sizeof(cItmSys), 1, 13);
    g_pItemModelSys = sys;
    sys->Init();
}

// Registers every model of the room's ITM pack.
int ItemModelDataLoad(void* data)
{
    return g_pItemModelSys->DataLoad((u32) data);
}

// Model binary of item `no`; 0 when the room has none.
int ItemGetBinAddr(u8 no, void** pAddr)
{
    return g_pItemModelSys->GetBinAddr(no, pAddr);
}

// Texture palette of item `no`; 0 when the room has none.
int ItemGetTplAddr(u8 no, void** pAddr)
{
    return g_pItemModelSys->GetTplAddr(no, pAddr);
}

// Both model files of item `no`; 0 when either is missing.
int ItemGetBinTplAddr(u8 no, void** pBin, void** pTpl)
{
    if (ItemGetBinAddr(no, pBin) == 0) {
        return 0;
    }
    if (ItemGetTplAddr(no, pTpl) == 0) {
        return 0;
    }
    return 1;
}

// Clears the 0x100 bin/tpl entries.
void cItmSys::WorkClear()
{
    int i;

    for (i = 0; i < 0x100; i++) {
        work[i].bin = 0;
        work[i].tpl = 0;
    }
}

// Clears the table.
void cItmSys::Init()
{
    WorkClear();
}

// Walks the pack's id / bin offset / tpl offset tables and registers each item id.
int cItmSys::DataLoad(u32 addr)
{
    ItemModelPack* pack = (ItemModelPack*) addr;
    ItemModelIdTbl* idTbl = (ItemModelIdTbl*) (addr + pack->ofsId);
    ItemModelOfsTbl* binTbl = (ItemModelOfsTbl*) (addr + pack->ofsBin);
    ItemModelOfsTbl* tplTbl = (ItemModelOfsTbl*) (addr + pack->ofsTpl);
    u32 i;

    for (i = 0; i < idTbl->num; i++) {
        u16 id = idTbl->id[i].id;

#if RE4DC_ITEMS_CENSUS
        re4dc_items_census_model("itm", 0, id, (u8*) binTbl + binTbl->ofs[i]);
#endif
        g_pItemModelSys->ItmRegist((u8*) binTbl + binTbl->ofs[i], (u8*) tplTbl + tplTbl->ofs[i], id);
    }
    return 1;
}

// Stores the model pair for item `no`.
int cItmSys::ItmRegist(void* bin, void* tpl, u8 no)
{
    work[no].bin = bin;
    work[no].tpl = tpl;
    return 1;
}

// Registered binary of item `no` (1 when present).
int cItmSys::GetBinAddr(u8 no, void** pAddr)
{
    *pAddr = work[no].bin;
    if (*pAddr != 0) {
        return 1;
    }
    return 0;
}

// Registered tpl of item `no` (1 when present).
int cItmSys::GetTplAddr(u8 no, void** pAddr)
{
    *pAddr = work[no].tpl;
    if (*pAddr != 0) {
        return 1;
    }
    return 0;
}
