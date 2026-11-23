// data.cpp (lane eng-sched1): zeroed storage for the data objects the hosted units name and the PC check does not
// host (managers, the camera controller, the event manager, the message system, the save data). 32 KiB each, larger
// than any of their types; nothing constructs them (the stubs answer every call made on them).
#define BLOB(sym) __attribute__((aligned(32))) unsigned char sched_##sym[0x8000] asm(#sym);
BLOB(CamCtrl)
BLOB(DC)
BLOB(EatMgr)
BLOB(EmMgr)
BLOB(EvtMgr)
BLOB(GameSave)
BLOB(IdSys)
BLOB(ItemMgr)
BLOB(Key)
BLOB(cMes)
__attribute__((aligned(32))) static unsigned char sched_save[0x8000];
void* pSaveData = sched_save;
