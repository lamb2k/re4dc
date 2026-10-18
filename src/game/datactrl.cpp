// game/datactrl: streamed room data units in MRAM/ARAM (D:/Bio4/Prog/datactrl.cpp).
// All functions byte-identical (the static-initializer trio is only named differently); .rodata and
// all section sizes match.
//  - dispDebug: `x1` is ONE function-scope variable shared by the loop's second conversion and the
//    `over` block's bar width, so the allocno's conflicts are the union of both ranges (r0/r9/r11/r10/r8
//    temps of the over block, r6 = x0, r7 = the `x1 - x0` temp) and it lands in r5; a block-scoped x1
//    in the loop conflicts with nothing and takes the r7 preference set_preference inherits from the
//    local-alloc'd `subf` temp. The loop's `x0` stays block-scoped (p=r31 via reusing `p` for the tiles).
#include "types.h"
#include "global.h"
#include "datactrl.h"
#include "dvd.h"
#include "main.h"
#include "main_mem.h"
#include "db_log.h"
#include "eprintf.h"
#include "libgpu.h"
#include "snd.h"
#if defined(RE4DC_GAME)
#include "native_event_file.h"
#endif
#if defined(RE4DC_GAME) && !defined(__PPC__)
// GD-ROM is the ARAM tier (platform/dvd.cpp): a unit's ARAM copy is its disc file.
extern "C" int re4dc_aram_file_read(const char* name, void* dst, unsigned bytes);
extern "C" void re4dc_missing(const char* name);
#endif

extern "C" {
void OSReport(const char* fmt, ...);
void* memcpy(void* dst, const void* src, unsigned int n);
void DCFlushRange(void* addr, u32 nBytes);
unsigned int strlen(const char* s);
char* strcpy(char* dst, const char* src);
}

// Not the do { } while (0) form of the other units: the OSReport stays in the caller's block and
// the preceding pLog->err argument loads are scheduled against it (setData).
#define HALT()                                                    \
    {                                                             \
        OSReport("HALT %s(%d)\n", __FILE__, __LINE__);            \
        RE4DC_HALT_STORE();                                       \
    }

// The debug bar primitive is 0x20 bytes here (tile[2] is 0x40).
struct DcTile {
    u32 tag;          // 0x00
    u32 code;         // 0x04
    GpuColor c0;      // 0x08
    s16 x0, y0;       // 0x0C
    s16 w, h;         // 0x10
    s16 z0;           // 0x14
    u8 pad_16[0xA];
};

#define ARAM_END 0xD00000

cDataCtrl DC;

#if defined(RE4DC_GAME)
extern "C" int re4dc_event_file_range(unsigned address, unsigned bytes)
{
    if (!bytes) return 0;
    for (int i = 0; i < 32; ++i) {
        const cDataUnit& u = DC.m_DataUnit[i];
        if ((u.m_be_flag & (1 | RE4DC_EVENT_FILE_FLAG)) != (1 | RE4DC_EVENT_FILE_FLAG) || u.m_condition != 4) continue;
        const unsigned base = (unsigned) (u32) u.m_addr;
        if (address >= base ? address - base < u.m_size : base - address < bytes) return 1;
    }
    return 0;
}
#if RE4DC_EVENT_SWAP_RELOAD
// EVENT_SWAP_RELOAD: the prepared (condition 4, never installed) event-file unit whose range is exactly
// [address, address + bytes): MemorySwap's ARAM side. Its name is the file the swap installs.
extern "C" const char* re4dc_event_file_unit(unsigned address, unsigned bytes)
{
    for (int i = 0; i < 32; ++i) {
        const cDataUnit& u = DC.m_DataUnit[i];
        if ((u.m_be_flag & (1 | RE4DC_EVENT_FILE_FLAG)) != (1 | RE4DC_EVENT_FILE_FLAG) || u.m_condition != 4) continue;
        if ((unsigned) (u32) u.m_addr == address && u.m_size == bytes) return u.m_name;
    }
    return 0;
}
#endif
#endif

// Stores the unit's file name (at most 31 chars; longer is a fatal error), "" for NULL.
#line 52 "D:/Bio4/Prog/datactrl.cpp"
inline void cDataUnit::setName(char* s)
{
    if (s != NULL) {
        if (strlen(s) > 0x1F) {
            pLog->err(0, 0, "DATANAME STRING OVER: %s", s);
            HALT();
        }
        strcpy(m_name, s);
    } else {
        m_name[0] = 0;
    }
}

// Queues a command (1 load to MRAM, 2 load to ARAM, 3 clear, 4 delete) with the destination
// address `arg` (0 = allocate) and the synchronous flag `wait`; executed at once unless the
// controller holds commands back (m_nblock_read_stop).
void cDataUnit::setCommand(int cmd, u32 arg, u8 wait)
{
    m_command = cmd;
    this->arg = arg;
    this->wait = wait;
    if (wait != 0 || DC.m_nblock_read_stop != 1) {
        checkCommand();
    }
}

// The pending command.
int cDataUnit::getCommand()
{
    return m_command;
}

// Sets the unit state (see the condition codes in datactrl.h).
void cDataUnit::setCondition(int c)
{
    m_condition = c;
}

// The unit state: 0 none, 1 / 2 MRAM loading / ok, 3 / 4 ARAM loading / ok, 5..8 transfers.
int cDataUnit::getCondition()
{
    return m_condition;
}

// Frees the MRAM block the unit allocated for itself (m_be_flag bit1), if any.
void cDataUnit::checkMallocRelease()
{
    if (chk(2) == 1) {
#if RE4DC_CABIN_SOURCE
        if(!re4dc_cabin_carrier_before_free(m_malloc_addr)){
            re4dc_missing("cabin unit allocation still leased");return;
        }
#endif
        if (DC.dbgHeap == 1) {
            Debug_free_h(m_malloc_addr, m_malloc_heap);
        } else {
            Mem_free_h(m_malloc_addr, m_malloc_heap);
        }
        m_be_flag &= ~2;
    }
}

// Records (on) or forgets the unit-owned allocation `p` and its heap.
void cDataUnit::setMallocInfo(int on, void* p)
{
    if (chk(2) == 1) {
        checkMallocRelease();
    }
    if (on == 1) {
        m_be_flag |= 2;
    } else {
        m_be_flag &= ~2;
    }
    m_malloc_addr = p;
    if (DC.dbgHeap == 1) {
        m_malloc_heap = MemGetCurrentDbgHeap();
    } else {
        m_malloc_heap = MemGetCurrentHeap();
    }
}

// Pins the MRAM destination: loads go to `a` instead of allocating.
void cDataUnit::fixMramAddr(u32 a)
{
    m_fix_addr = a;
}

// 1 when the data is in MRAM and usable (condition 2); 0 while idle or elsewhere.
int cDataUnit::isUseOk()
{
    if (m_condition == 0 && m_command == 0) {
        m_err = 5;
        return 0;
    }
    return getCondition() == 2;
}

// Blocks (TaskSleep) until the data is in MRAM; 0 when the unit is idle or the wait failed.
int cDataUnit::waitUseOk()
{
    if (m_condition == 0 && m_command == 0) {
        m_err = 5;
        return 0;
    }
    while (isUseOk() == 0) {
        m_wait = 1;
        checkCondition();
        if (getCondition() == 4) {
            checkCommand();
        }
        if (m_err != 0) {
            return 0;
        }
    }
    return 1;
}

// 1 when the data is resident in MRAM or ARAM (condition 2 or 4).
int cDataUnit::isLoadOk()
{
    if (m_condition == 0 && m_command == 0) {
        m_err = 5;
        return 0;
    }
    if (m_condition == 2 || m_condition == 4) {
        return 1;
    }
    return 0;
}

// Blocks until the data is resident somewhere.
int cDataUnit::waitLoadOk()
{
    if (m_condition == 0 && m_command == 0) {
        m_err = 5;
        return 0;
    }
    while (isLoadOk() == 0) {
        m_wait = 1;
        checkCondition();
        if (m_err != 0) {
            return 0;
        }
    }
    return 1;
}

// Executes "load to MRAM": from idle starts the DVD read into the fixed / given / allocated
// destination (condition 1; in dev mode a dummy.dat read is issued alongside), from ARAM starts
// the ARAM -> MRAM DMA (condition 5); already in MRAM just clears the command; transfers in
// flight are left alone.
void cDataUnit::setLoadToMram()
{
    int no;

    switch (m_condition) {
    case 1:
    case 3:
    case 5:
    case 6:
    case 7:
    case 8:
        break;
    case 0:
        if (m_fix_addr == 0) {
            if (arg == 0) {
                if (DC.dbgHeap == 1) {
                    dest = (u32) Debug_alloc(m_size, 1);
                } else {
#line 200 "D:/Bio4/Prog/datactrl.cpp"
                    dest = (u32) MEM_ALLOC(m_size, 1, 0xD);
                }
                if (dest == 0) {
                    m_err = 1;
                    return;
                }
                setMallocInfo(1, (void*) dest);
            } else {
                dest = arg;
                setMallocInfo(0, NULL);
            }
        } else {
            dest = m_fix_addr;
            setMallocInfo(0, NULL);
        }
#line 222 "D:/Bio4/Prog/datactrl.cpp"
        no = DvdReadN(m_name, (void*) dest, 0, 0, 0, wait | 0x10, __FILE__, __LINE__);
        if (pG->dev_mode == 1) {
#line 226 "D:/Bio4/Prog/datactrl.cpp"
            DC.setDummyId(DvdReadN("dummy.dat", DC.m_DummyDataMem, 0, 0, 0, wait | 0x10, __FILE__, __LINE__));
        }
        m_id = no;
        if (no >= 0) {
            m_command = 0;
            m_condition = 1;
            if (wait == 1) {
                checkLoadToMram();
            }
            OSReport("DC:%s set MRAM_LOAD\n", m_name);
        } else {
            m_err = 2;
            checkMallocRelease();
            pLog->err(0, 0, "cDataUnit::setLoadToMram command error");
        }
        break;
    case 2:
#if RE4DC_CABIN_SOURCE
        if(re4dc_cabin_carrier_mram_move(this,(void*)(m_fix_addr?m_fix_addr:(arg?arg:(u32)m_addr)))<0){
            m_err=3;m_command=0;return;
        }
#endif
        if (m_fix_addr == 0) {
            if (arg != 0 && arg != (u32) m_addr) {
                checkMallocRelease();
                memcpy((void*) arg, m_addr, m_size);
                m_addr = (void*) arg;
                DCFlushRange((void*) arg, m_size);
            }
        } else if (m_fix_addr != (u32) m_addr) {
            checkMallocRelease();
            memcpy((void*) m_fix_addr, m_addr, m_size);
            m_addr = (void*) m_fix_addr;
            DCFlushRange((void*) arg, m_size);
        }
        m_command = 0;
        OSReport("DC:%s set MRAM_TO_MRAM\n", m_name);
        break;
    case 4:
        if (m_fix_addr == 0) {
            if (arg == 0) {
                if (DC.dbgHeap == 1) {
                    dest = (u32) Debug_alloc(m_size, 1);
                } else {
#line 290 "D:/Bio4/Prog/datactrl.cpp"
                    dest = (u32) MEM_ALLOC(m_size, 1, 0xD);
                }
                if (dest == 0) {
                    m_err = 1;
                    return;
                }
                setMallocInfo(1, (void*) dest);
            } else {
                dest = arg;
                setMallocInfo(0, NULL);
            }
        } else {
            dest = m_fix_addr;
            setMallocInfo(0, NULL);
        }
#if defined(RE4DC_GAME) && RE4DC_EVENT_FILES
        if (m_be_flag & RE4DC_EVENT_FILE_FLAG) {
            // The caller's final allocation is the only complete RAM copy.
            // Failed/partial reads are never published to source consumers.
            int cabin_install = 0;
#if RE4DC_CABIN_SOURCE
            cabin_install = re4dc_cabin_carrier_install(this, (void*) dest);
#endif
            if (cabin_install < 0 || (!cabin_install && !re4dc_event_file_install(m_name, m_size, (void*) dest))) {
                m_err = 2;
                m_command = 0;
                checkMallocRelease();
                dest = 0;
                break;
            }
            m_addr = (void*) dest;
            m_condition = 2;
            m_command = 0;
            m_wait = 0;
            OSReport("DC:%s check FILE_MRAM_OK\n", m_name);
            break;
        }
#endif
#if defined(RE4DC_GAME) && !defined(__PPC__)
        // No ARAM copy exists: re-read the unit's disc file into the destination now
        // (blocking, like the source's synchronous DMA). The ARQ request below still
        // runs so condition 5 -> MRAM_OK lands on the same check as on GC.
        if (!re4dc_aram_file_read(m_name, (void*) dest, m_size)) {
            m_err = 3;
            checkMallocRelease();
            pLog->err(0, 0, "cDataUnit::setLoadToMram disc re-read error");
            re4dc_missing("ARAM_TO_MRAM disc re-read failed");
            break;
        }
        DCFlushRange((void*) dest, m_size);
#endif
        no = Aram.DmaTransReq(1, (u32) m_addr, dest, m_size, wait);
        m_id = no;
        if (no >= 0) {
            m_command = 0;
            m_condition = 5;
            if (wait == 1) {
                checkAramToMram();
            }
            OSReport("DC:%s set ARAM_TO_MRAM\n", m_name);
        } else {
            m_err = 3;
            checkMallocRelease();
            pLog->err(0, 0, "cDataUnit::setLoadToMram command error");
        }
        break;
    }
}

// Executes "load to ARAM": from idle a DVD read straight to ARAM (condition 3, address from
// getAramFree), from MRAM the MRAM -> ARAM DMA (condition 6) freeing the MRAM copy afterwards;
// already in ARAM clears the command.
void cDataUnit::setLoadToAram()
{
    int no;

    switch (m_condition) {
    case 1:
    case 3:
    case 5:
    case 6:
    case 7:
    case 8:
        break;
    case 0:
        if (arg == 0) {
            dest = DC.getAramFree(m_size);
            if (dest == 0) {
                m_err = 4;
                pLog->err(0, 0, "ARAM over: %s", m_name);
                break;
            }
        } else {
            dest = arg;
        }
#if defined(RE4DC_GAME) && RE4DC_EVENT_FILES
        if (re4dc_event_file_name(m_name)) {
            int cabin_prepare = 0;
#if RE4DC_CABIN_SOURCE
            cabin_prepare = re4dc_cabin_carrier_prepare(this, m_name, m_size, dest);
#endif
            if (cabin_prepare < 0 || (!cabin_prepare && !re4dc_event_file_prepare(m_name, m_size))) {
                m_err = 2;
                m_command = 0;
                dest = 0;
                break;
            }
            m_be_flag |= RE4DC_EVENT_FILE_FLAG;
            m_addr = (void*) dest;
            m_id = -1;
            m_condition = 4;
            m_command = 0;
            m_wait = 0;
            OSReport("DC:%s check FILE_READY bytes=%u\n", m_name, m_size);
            break;
        }
#endif
#if defined(RE4DC_GAME) && !defined(__PPC__)
        // GD-ROM is the ARAM tier: the disc file is the unit's ARAM copy. Record the ARAM
        // address and size only (no discarded read); ARAM_TO_MRAM re-reads the file.
        m_addr = (void*) dest;
        m_id = -1;
        m_condition = 4;
        m_command = 0;
        m_wait = 0;
        OSReport("DC:%s set ARAM_LOAD (disc-backed) check ARAM_OK\n", m_name);
        break;
#endif
#line 366 "D:/Bio4/Prog/datactrl.cpp"
        no = DvdReadN(m_name, NULL, dest, 0, 0, wait | 0x8, __FILE__, __LINE__);
        if (pG->dev_mode == 1) {
#line 370 "D:/Bio4/Prog/datactrl.cpp"
            DC.setDummyId(DvdReadN("dummy.dat", DC.m_DummyDataMem, 0, 0, 0, wait | 0x10, __FILE__, __LINE__));
        }
        m_id = no;
        if (no >= 0) {
            m_command = 0;
            m_condition = 3;
            if (wait == 1) {
                checkLoadToAram();
            }
            OSReport("DC:%s set ARAM_LOAD\n", m_name);
        } else {
            m_err = 2;
            checkMallocRelease();
            pLog->err(0, 0, "cDataUnit::setLoadToAram command error");
        }
        break;
    case 2:
#if defined(RE4DC_GAME) && RE4DC_EVENT_FILES
        if (m_be_flag & RE4DC_EVENT_FILE_FLAG) {
#if RE4DC_CABIN_SOURCE
            unsigned cabin_park_address=arg;
            const int cabin_park=re4dc_cabin_carrier_park(this,&cabin_park_address);
            if(cabin_park>0){
                checkMallocRelease();dest=cabin_park_address;m_addr=(void*)dest;
                m_condition=4;m_command=0;m_wait=0;break;
            }
#endif
            // After activation these bytes can contain relocated pointers and
            // mutations. Never discard them by treating the original as current.
            m_err = 3;
            m_command = 0;
            OSReport("DC:%s mutable event parking unsupported; retaining MRAM\n", m_name);
            break;
        }
#endif
        if (arg == 0) {
            dest = DC.getAramFree(m_size);
            if (dest == 0) {
                m_err = 4;
                pLog->err(0, 0, "ARAM over: %s", m_name);
                break;
            }
        } else {
            dest = arg;
        }
        no = Aram.DmaTransReq(0, (u32) m_addr, dest, m_size, wait);
        m_id = no;
        if (no >= 0) {
            m_command = 0;
            m_condition = 6;
            if (wait == 1) {
                checkMramToAram();
            }
            OSReport("DC:%s set MRAM_TO_ARAM\n", m_name);
        } else {
            m_err = 3;
            checkMallocRelease();
            pLog->err(0, 0, "cDataUnit::setLoadToAram command error");
        }
        break;
    case 4:
#if defined(RE4DC_GAME) && RE4DC_EVENT_FILES
        if (m_be_flag & RE4DC_EVENT_FILE_FLAG) {
            if (arg != 0 && arg != (u32) m_addr) {
#if RE4DC_CABIN_SOURCE
                if (re4dc_cabin_carrier_rebase(this, arg) < 0) return;
#endif
                m_addr = (void*) arg;
                dest = arg;
                re4dc_event_file_moved();
                OSReport("DC:%s FILE_REBASE addr=%08x bytes=%u\n", m_name, arg, m_size);
            }
            m_command = 0;
            break;
        }
#endif
        if (arg != 0 && arg != (u32) m_addr) {
            if (DC.dbgHeap == 1) {
                dest = (u32) Debug_alloc(m_size, 1);
            } else {
#line 452 "D:/Bio4/Prog/datactrl.cpp"
                dest = (u32) MEM_ALLOC(m_size, 0, 0xD);
            }
            if (dest != 0) {
                setMallocInfo(1, (void*) dest);
                no = Aram.DmaTransReq(1, (u32) m_addr, dest, m_size, wait);
                m_id = no;
                if (no >= 0) {
                    m_command = 0;
                    m_condition = 7;
                    OSReport("DC:%s set ARAM_TO_ARAM\n", m_name);
                } else {
                    m_err = 3;
                    checkMallocRelease();
                    pLog->err(0, 0, "cDataUnit::setLoadToAram command error");
                }
            } else {
                setClear();
                setCommand(CMND_ARAM_LOAD, 0, 0);
            }
        }
        break;
    }
}

// Executes "clear": waits out a running DVD read, frees the unit's MRAM allocation and returns
// to condition 0 (the ARAM space is reclaimed by the sort).
int cDataUnit::setClear()
{
#if RE4DC_CABIN_SOURCE
    if (!re4dc_cabin_carrier_clear(this)) return 0;
#endif
    m_command = 0;
    switch (m_condition) {
    case 5:
    case 6:
    case 7:
        Aram.DmaCancel(m_id);
        break;
    case 2:
    case 4:
    case 8:
        break;
    case 1:
    case 3:
        Dvd.ReadCancel(m_id, 0x40);
        Dvd.ReadCheck(m_id, NULL, NULL, NULL);
        break;
    case 0:
        goto clear;
    default:
        goto ret;
    }
    OSReport("DC:%s set CLEAR\n", m_name);
clear:
    checkMallocRelease();
#if defined(RE4DC_GAME)
    m_be_flag &= ~RE4DC_EVENT_FILE_FLAG;
#endif
    m_addr = NULL;
    dest = 0;
    m_condition = 0;
ret:
    return 1;
}

// Executes "delete": clear plus the unit itself is freed (m_be_flag bit0 off).
int cDataUnit::setDelete()
{
#if RE4DC_CABIN_SOURCE
    if (!setClear()) return 0;
#else
    setClear();
#endif
    m_size = 0;
    m_be_flag &= ~1;
    OSReport("DC:%s set DELETE\n", m_name);
    return 1;
}

// Condition 1 step: when the DVD read finished the data is in MRAM (condition 2).
void cDataUnit::checkLoadToMram()
{
    int ret;

    if (m_wait == 1) {
        Dvd.ReadNblk2Blk(m_id);
        m_wait = 0;
    }
    ret = Dvd.ReadCheck(m_id, NULL, NULL, NULL);
    if (ret > 0) {
        m_condition = 2;
        m_addr = (void*) dest;
        OSReport("DC:%s check MRAM_OK\n", m_name);
    } else if (ret < 0) {
        m_err = 2;
        checkMallocRelease();
        pLog->err(0, 0, "cDataUnit::checkLoadToMram command error");
    }
}

// Condition 3 step: when the DVD read finished the data is in ARAM (condition 4).
void cDataUnit::checkLoadToAram()
{
    int ret;

    if (m_wait == 1) {
        Dvd.ReadNblk2Blk(m_id);
        m_wait = 0;
    }
    ret = Dvd.ReadCheck(m_id, NULL, NULL, NULL);
    if (ret > 0) {
        m_condition = 4;
        m_addr = (void*) dest;
        OSReport("DC:%s check ARAM_OK\n", m_name);
    } else if (ret < 0) {
        m_err = 2;
        checkMallocRelease();
        pLog->err(0, 0, "cDataUnit::checkLoadToAram command error");
    }
}

// Condition 5 step: when the DMA finished the data is in MRAM (condition 2).
void cDataUnit::checkAramToMram()
{
    int done = 0;

    if (m_wait == 1) {
        while (Aram.TransCheck(m_id) != 1) {
        }
        m_wait = 0;
        done = 1;
    }
    if (Aram.TransCheck(m_id) == 1 || done == 1) {
        m_condition = 2;
        m_addr = (void*) dest;
        OSReport("DC:%s check MRAM_OK\n", m_name);
    }
}

// Condition 6 step: when the DMA finished the data is in ARAM (condition 4) and the MRAM copy is
// freed.
void cDataUnit::checkMramToAram()
{
    int done = 0;

    if (m_wait == 1) {
        while (Aram.TransCheck(m_id) != 1) {
        }
        m_wait = 0;
        done = 1;
    }
    if (Aram.TransCheck(m_id) == 1 || done == 1) {
        checkMallocRelease();
        m_condition = 4;
        m_addr = (void*) dest;
        OSReport("DC:%s check ARAM_OK\n", m_name);
    }
}

// Condition 7 step (ARAM repack through MRAM): when the ARAM -> MRAM half finished, starts the
// MRAM -> new ARAM half (condition 6).
void cDataUnit::checkAramToAram()
{
    int done = 0;

    if (m_wait == 1) {
        while (Aram.TransCheck(m_id) != 1) {
        }
        m_wait = 0;
        done = 1;
    }
    if (Aram.TransCheck(m_id) == 1 || done == 1) {
        m_addr = (void*) dest;
        m_id = Aram.DmaTransReq(0, dest, arg, m_size, wait);
        dest = arg;
        if (m_id >= 0) {
            m_condition = 6;
            OSReport("DC:%s set MRAM_TO_ARAM\n", m_name);
        } else {
            m_err = 3;
            checkMallocRelease();
            pLog->err(0, 0, "cDataUnit::checkAramToAram command error");
        }
    }
}

// Condition 8: nothing to do (MRAM moves are immediate).
void cDataUnit::checkMramToMram()
{
}

// Runs the pending command against the current condition (setLoadToMram / setLoadToAram /
// setClear / setDelete).
void cDataUnit::checkCommand()
{
    switch (getCommand()) {
    case 0:
        break;
    case 1:
        setLoadToMram();
        break;
    case 2:
        setLoadToAram();
        break;
    case 3:
        setClear();
        break;
    case 4:
        setDelete();
        break;
    }
}

// Advances the running transfer of the unit (the check* step for its condition).
void cDataUnit::checkCondition()
{
    switch (getCondition()) {
    case 0:
        break;
    case 1:
        checkLoadToMram();
        break;
    case 2:
        break;
    case 3:
        checkLoadToAram();
        break;
    case 4:
        break;
    case 5:
        checkAramToMram();
        break;
    case 6:
        checkMramToAram();
        break;
    case 7:
        checkAramToAram();
        break;
    case 8:
        checkMramToMram();
        break;
    }
}

struct AramArea {
    u32 addr;
    u32 size;
};

// An ARAM address for `size` bytes: the first gap between the resident ARAM units (sorted by
// address) that fits, else the end of the used area; 0 when it would pass ARAM_END.
u32 cDataCtrl::getAramFree(u32 size)
{
    AramArea tbl[32];
    AramArea tmp;
    int n;
    int i, j;
    u32 k;
    u32 base;
    cDataUnit* u;

    n = 0;
    for (i = 0; i < 32; i++) {
        u = &m_DataUnit[i];
        if (u->chk(1) != 0) {
#if RE4DC_CABIN_SOURCE
            const unsigned cabin_reserved=re4dc_cabin_carrier_reserved(u);
            if(cabin_reserved){
                tbl[n].addr=cabin_reserved;tbl[n].size=u->m_size;++n;continue;
            }
#endif
            switch (u->getCondition()) {
            case 7:
                tbl[n].addr = u->arg;
                tbl[n].size = u->m_size;
                n++;
                // fallthrough
            case 4:
            case 5:
                tbl[n].addr = (u32) u->m_addr;
                tbl[n].size = u->m_size;
                n++;
                break;
            case 3:
            case 6:
                tbl[n].addr = u->dest;
                tbl[n].size = u->m_size;
                n++;
                break;
            case 0:
            case 1:
            case 2:
            case 8:
                break;
            }
        }
    }
    if (n != 0) {
        for (i = 0; i < n - 1; i++) {
            for (j = i; j < n; j++) {
                if (tbl[i].addr > tbl[j].addr) {
                    tmp = tbl[j];
                    tbl[j] = tbl[i];
                    tbl[i] = tmp;
                }
            }
        }
        base = ARAM_FREE_BASE;
        for (i = 0; i < n; i++) {
            if ((int) (tbl[i].addr - base) >= (int) size) {
                for (k = 0; k < 32; k++) {
                    u = &m_DataUnit[k];
                    if (u->chk(1) != 0 && base == u->dest) {
#line 852 "D:/Bio4/Prog/datactrl.cpp"
                        HALT();
                    }
                }
                return base;
            }
            base = tbl[i].addr + tbl[i].size;
        }
        m_aram_free = base + size;
        if (m_aram_free > ARAM_END - 1) {
            return 0;
        }
        return base;
    }
    return ARAM_FREE_BASE;
}

// Boot: allocates the dummy read buffer and the debug bar tiles, resets the units and the ARAM
// allocator.
void cDataCtrl::init()
{
    initDataUnit();
    m_DummyDataMem = Debug_alloc(0x100, 1);
    dispBuf = Debug_alloc(0x400, 1);
}

// Clears all 32 units and the ARAM allocator (room start).
void cDataCtrl::initDataUnit()
{
#if RE4DC_CABIN_SOURCE
    if (!re4dc_cabin_carriers_reset()) { re4dc_missing("cabin carrier reader before unit reset"); return; }
#endif
    cDataUnit* u;
    u32 i;

    m_aram_free = ARAM_FREE_BASE;
    setAramSort(1);
    m_data_ctrl_flag = 1;
    dbgHeap = 0;
    for (i = 0; i < 32; i++) {
        u = &m_DataUnit[i];
        memclr_asm(u, sizeof(cDataUnit));
        u->m_be_flag &= ~1;
        u->setCondition(0);
        u->setCommand(0, 0, 0);
        u->m_err = 0;
        u->fixMramAddr(0);
    }
    initDummyId();
}

// Deletes every unit (frees MRAM allocations).
void cDataCtrl::deleteAll()
{
    u32 i;

    for (i = 0; i < 32; i++) {
        m_DataUnit[i].setDelete();
    }
}

// Registers file `name` as a new unit (size from the DVD file table); NULL when the file does
// not exist or the 32 units are used.
cDataUnit* cDataCtrl::setData(char* name)
{
    u32 len;
    cDataUnit* u;

    if (Dvd.FileExistCheck(name, &len) < 0) {
        pLog->err(0, 0, "cDataCtrl::setData(\"%s\") not found", name);
        return NULL;
    }
    u = getNewUnit();
    if (u != NULL) {
        OSReport("DataCtrl::setData(\"%s\") %d succeed\n", name, len);
        u->m_size = len;
        u->setName(name);
    }
    return u;
}

// The first free unit, cleared and marked in use; NULL with an error when none.
cDataUnit* cDataCtrl::getNewUnit()
{
    cDataUnit* u;
    u32 i;

    for (i = 0; i < 32; i++) {
        u = &m_DataUnit[i];
        if (u->chk(1) == 0) {
#if RE4DC_CABIN_SOURCE
            if(!re4dc_cabin_carrier_unit_available(u)){
                re4dc_missing("cabin source unit identity still owned");return NULL;
            }
#endif
            u->m_be_flag |= 1;
            u->setCondition(0);
            u->setCommand(0, 0, 0);
            u->m_err = 0;
            u->m_size = 0;
            u->m_name[0] = 0;
            u->m_addr = NULL;
            return u;
        }
    }
    pLog->err(0, 0, "cDataCtrl::setData  DC work over");
    return NULL;
}

// Requests a repack of the ARAM units (after deletions left gaps).
void cDataCtrl::setAramSort(int on)
{
    aramSort = on;
}

// Per-frame repack: when requested and no transfer is running, moves the resident ARAM units
// down to close gaps (one ARAM -> ARAM transfer per call, condition 7) and lowers m_aram_free;
// 1 while a move was started.
int cDataCtrl::checkAramSort()
{
    cDataUnit* tbl[32];
    cDataUnit* tmp;
    u8 n;
    int i, j;
    u32 base;
    cDataUnit* u;

    if (aramSort == 0) {
        return 0;
    }
    n = 0;
    for (i = 0; i < 32; i++) {
        u = &m_DataUnit[i];
        if (u->chk(1) != 0) {
            if (u->getCommand() == 0) {
                switch (u->getCondition()) {
                case 0:
                case 1:
                case 2:
                    break;
                case 4:
                    tbl[n] = u;
                    n++;
                    break;
                case 3:
                case 5:
                case 6:
                case 7:
                    return 0;
                case 8:
                    break;
                }
            } else {
                return 0;
            }
        }
    }
    if (n != 0) {
        for (i = 0; i < n - 1; i++) {
            for (j = i; j < n; j++) {
                if ((u32) tbl[i]->m_addr > (u32) tbl[j]->m_addr) {
                    tmp = tbl[j];
                    tbl[j] = tbl[i];
                    tbl[i] = tmp;
                }
            }
        }
        base = ARAM_FREE_BASE;
        for (i = 0; i < n; i++) {
            if (base < (u32) tbl[i]->m_addr) {
                tbl[i]->setCommand(CMND_ARAM_LOAD, base, 0);
                tbl[i]->setLoadToAram();
                return 1;
            }
            base += tbl[i]->m_size;
        }
        m_aram_free = base;
    }
    return 0;
}

// Debug page 0x17 "ARAM DATA DISP": a bar of the ARAM area with each resident unit's span and
// the per-unit name / condition / address list.
void cDataCtrl::dispDebug()
{
    static DcTile tile[2];
    DcTile* p;
    int over;
    int y;
    cDataUnit* u;
    u32 i;
    int x;
    u32 x1;

    dispBase = ARAM_FREE_BASE;
    dispEnd = ARAM_END;
    over = 0;
    p = NULL;
    if (dispBuf != NULL) {
        p = (DcTile*) dispBuf;
    } else {
        over = 1;
    }
    eprintf(0x28, 0x2E, 0, 0x17, "[ARAM DATA DISP]");
    y = 0x2E;
    x = 0x1F8;
    for (i = 0; i < 32; i++) {
        u = &m_DataUnit[i];
        if (u->chk(1) != 0) {
            u32 addr = 0;
            u32 size = 0;
            u32 x0;
            switch (u->getCondition()) {
            case 0:
            case 1:
            case 2:
            case 8:
                continue;
            case 3:
            case 4:
            case 5:
            case 6:
            case 7:
                addr = (u32) u->m_addr;
                size = u->m_size;
                break;
            }
            y += 0x10;
            eprintf(0x28, y, 0, 0x17, "%08x:%s", u->m_addr, u->m_name);
            x0 = (u32) ((f32) (addr - dispBase) * 400.0f / (f32) (dispEnd - dispBase));
            x1 = (u32) ((f32) (addr + size - dispBase) / (f32) (dispEnd - dispBase) * 400.0f);
            if (over == 0) {
                p->code = GPU_TILE;
                p->x0 = x;
                p->y0 = x0 + 0x1E;
                p->w = 5;
                p->h = x1 - x0;
                p->z0 = 0;
                p->c0.r = 0x90;
                p->c0.g = 0x50;
                p->c0.b = 0x50;
                p->c0.cd = 0xFF;
                AddPrim(&MainOt[1], (u32*) p);
                p++;
                if (u == &m_DataUnit[32]) {
                    over = 1;
                }
            }
        }
    }
    if (over == 1) {
        p = &tile[0];
        x1 = (u32) ((f32) (m_aram_free - dispBase) * 400.0f / (f32) (dispEnd - dispBase));
        p->code = GPU_TILE;
        p->x0 = x;
        p->y0 = 0x1E;
        p->z0 = 0;
        p->w = 5;
        p->h = x1;
        p->c0.r = 0x90;
        p->c0.g = 0x50;
        p->c0.b = 0x50;
        p->c0.cd = 0xFF;
        AddPrim(&MainOt[1], (u32*) p);
    }
    p = &tile[1];
    p->code = GPU_TILE;
    p->x0 = x;
    p->y0 = 0x1E;
    p->z0 = 0;
    p->w = 5;
    p->h = 400;
    p->c0.r = 0x20;
    p->c0.g = 0x20;
    p->c0.b = 0x20;
    p->c0.cd = 0xFF;
    AddPrim(&MainOt[1], (u32*) p);
}

// Clears the dummy.dat request slots (dev mode reads that mirror each data read).
void cDataCtrl::initDummyId()
{
    int i;

    for (i = 0; i < 32; i++) {
        m_id_dummy[i] = -1;
    }
}

// Records a dummy.dat request id to be waited on.
void cDataCtrl::setDummyId(int id)
{
    int i;

    if (pG->dev_mode != 0 && id >= 0) {
        for (i = 0; i < 32; i++) {
            if (m_id_dummy[i] == -1) {
                m_id_dummy[i] = id;
                return;
            }
        }
        pLog->err(0, 0, "cDataCtrl::setDummyId: DummyId work over!!");
    }
}

// Retires finished dummy.dat requests.
void cDataCtrl::checkDummyId()
{
    int i;
    int ret;

    if (pG->dev_mode != 0) {
        for (i = 0; i < 32; i++) {
            if (m_id_dummy[i] != -1) {
                ret = Dvd.ReadCheck(m_id_dummy[i], NULL, NULL, NULL);
                if (ret > 0) {
                    m_id_dummy[i] = -1;
                } else if (ret < 0) {
                    pLog->err(0, 0, "cDataCtrl::checkDummyId: failed");
                }
            }
        }
    }
}

// Main task, every frame: unless the sub screen owns the ARAM area or commands are held, runs
// every unit's pending command and transfer step, the dummy requests and the ARAM repack.
void cDataCtrl::check()
{
    cDataUnit* u;
    int i;

    if (m_data_ctrl_flag != 0 && m_nblock_read_stop != 1) {
        while (checkAramSort() == 1) {
        }
        for (i = 0; i < 32; i++) {
            u = &m_DataUnit[i];
            if (u->chk(1) != 0) {
                u->m_err = 0;
                u->checkCommand();
                u->checkCondition();
            }
        }
        checkDummyId();
    }
}

#if RE4DC_CABIN_SOURCE
extern "C" int re4dc_cabin_source_unit_valid(const void* address,unsigned index,unsigned logical,unsigned bytes) {
    static const char* names[]={"evd/r11cs00.evd","evd/r11cs10.evd","evd/r11cs20.evd"};
    if(index>=3)return 0;
    for(unsigned i=0;i<32;++i) {
        const cDataUnit& u=DC.m_DataUnit[i];
        if(address!=&u)continue;
        if(!(u.m_be_flag&1) || u.m_size!=bytes || strcmp(u.m_name,names[index]))return 0;
        if(u.m_condition==0)return u.dest==logical;
        if(u.m_condition==2)return u.m_addr!=NULL;
        if(u.m_condition==4 || u.m_condition==5 || u.m_condition==7)return (u32)u.m_addr==logical;
        if(u.m_condition==6)return u.dest==logical;
        return 0;
    }
    return 0;
}
extern "C" int re4dc_cabin_source_range_available(const void* unit,unsigned address,unsigned bytes) {
    if(!address || address+bytes<address)return 0;
    for(unsigned i=0;i<32;++i){
        const cDataUnit& u=DC.m_DataUnit[i];if(&u==unit || !(u.m_be_flag&1))continue;
        unsigned first=0,second=0;
        const unsigned reserved=re4dc_cabin_carrier_reserved(&u);
        if(reserved)first=reserved;
        else if(u.m_condition==4 || u.m_condition==5 || u.m_condition==7)first=(u32)u.m_addr;
        else if(u.m_condition==3 || u.m_condition==6)first=u.dest;
        if(u.m_condition==7)second=u.arg;
        const unsigned starts[]={first,second};
        for(unsigned start:starts)if(start && (start+u.m_size<start ||
           (address<start+u.m_size && start<address+bytes)))return 0;
    }
    return 1;
}
extern "C" int re4dc_cabin_source_allocation(const void*,unsigned,int*);
extern "C" int re4dc_cabin_source_free(void*,unsigned,int);
extern "C" int re4dc_cabin_source_unit_retire_ready(const void* address,unsigned index,unsigned logical,unsigned bytes,const void* mram){
    static const char* names[]={"evd/r11cs00.evd","evd/r11cs10.evd","evd/r11cs20.evd"};
    if(index>=3)return 0;
    for(unsigned i=0;i<32;++i){
        const cDataUnit& u=DC.m_DataUnit[i];if(address!=&u)continue;
        if(!(u.m_be_flag&1) || u.m_size!=bytes || strcmp(u.m_name,names[index]))return 0;
        if(u.m_condition==0){if(u.m_addr || u.dest || mram || (u.m_be_flag&2))return 0;}
        else if(u.m_condition==4){if((u32)u.m_addr!=logical || (u.m_be_flag&2))return 0;}
        else if(u.m_condition==2){if(!mram || u.m_addr!=mram)return 0;}
        else return 0;
        if(u.m_be_flag&2){
            int heap=-1;
            if(u.m_malloc_addr!=mram || !re4dc_cabin_source_allocation(mram,bytes,&heap) || heap!=u.m_malloc_heap)return 0;
        }
        return 1;
    }
    return 0;
}
extern "C" int re4dc_cabin_source_unit_release(void* address,unsigned bytes){
    for(unsigned i=0;i<32;++i)if(address==&DC.m_DataUnit[i]){
        cDataUnit& u=DC.m_DataUnit[i];
        if(u.m_be_flag&2){
            if(!re4dc_cabin_source_free(u.m_malloc_addr,bytes,u.m_malloc_heap))return 0;
            u.m_be_flag&=~2;
        }
        return 1;
    }
    return 0;
}
extern "C" int re4dc_cabin_source_unit_clear(void* address) {
    for(unsigned i=0;i<32;++i)if(address==&DC.m_DataUnit[i])return DC.m_DataUnit[i].setClear();
    return 0;
}
#endif
