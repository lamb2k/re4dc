// Transport completion is a boundary. Actual EvtReadSub, command dispatch and
// wait/usable/load checks execute; no Event start or release result is mocked.
static unsigned transport_calls;
static bool transport_refuse;
static bool transport_other_flags;
#if defined(RE4DC_READ_ADMISSION_CHARACTERIZE)
static unsigned admission_source_errors;
struct AdmissionLogger{void err(int,int,const char*,...){++admission_source_errors;}} admission_logger;
static void re4dc_missing(const char*);
#if defined(RE4DC_FORWARD_ACTUAL)
extern "C" int re4dc_cabin_carrier_unit_available(const void*);
#else
static int re4dc_cabin_carrier_unit_available(const void*){return 1;}
#endif
#define HALT() std::abort()
#define pLog (&admission_logger)
#include "admission_controller_methods.inc"
#undef pLog
#undef HALT
#else
cDataUnit* Controller::setData(char*){return &loaded;}
#endif
#if defined(RE4DC_ARAM_ACTUAL)
static void* Debug_alloc(unsigned bytes,int flag){return aram_actual_alloc(bytes,flag,13);}
static int MemGetCurrentHeap(){return 4;}static int MemGetCurrentDbgHeap(){return 7;}
static int DvdReadN(const char*,void*,u32,u32,u32,int,const char*,int){std::abort();}
#if defined(RE4DC_FORWARD_ACTUAL)
static void DCFlushRange(void*,u32){}
static void re4dc_missing(const char*);
#else
static void DCFlushRange(void*,u32){std::abort();}
static void re4dc_missing(const char*){std::abort();}
#endif
static int re4dc_event_file_install(const char*,u32,void*){std::abort();}
static int re4dc_aram_file_read(const char*,void*,u32){std::abort();}
void cDataUnit::checkLoadToMram(){std::abort();}void cDataUnit::checkLoadToAram(){std::abort();}
void cDataUnit::checkAramToMram(){std::abort();}void cDataUnit::checkMramToAram(){std::abort();}
void cDataUnit::checkAramToAram(){std::abort();}void cDataUnit::checkMramToMram(){std::abort();}
#else
void cDataUnit::setLoadToMram(){
    ++transport_calls;
    if(transport_other_flags){global.Status_flg[2]|=0x20;global.System_flg|=0x4000000;}
    if(transport_refuse){m_err=1;return;}
    assert(m_condition==0||m_condition==2||m_condition==4);
    m_addr=m_malloc_addr=arena;m_malloc_heap=4;m_be_flag|=3;
    m_condition=2;m_command=0;m_err=0;
}
#endif
