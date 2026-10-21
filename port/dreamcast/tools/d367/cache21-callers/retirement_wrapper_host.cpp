#include "retirement_forward_base.cpp"
static unsigned module_frees,motion_unbinds,effect_unbinds,ui_enemy_unbinds,ui_player_unbinds,ui_weapon_unbinds;
static unsigned heap_destroys,heap_creates,heap_selects,room_enters,room_retires,weapon_heap_frees;
static bool retire_callback;
static void retirement_free(void*p){assert(re4dc_cabin_carrier_before_free(p));++module_frees;}
static void re4dc_motion_unbind(void*){++motion_unbinds;}
static void re4dc_effect_unbind(void*){++effect_unbinds;}
static void re4dc_ui_unbind_enemy(void*){++ui_enemy_unbinds;}
static void re4dc_ui_unbind_player(){++ui_player_unbinds;}
static void re4dc_ui_unbind_weapon(){++ui_weapon_unbinds;}
static void DLL_Unlink(OSModuleHeader*){if(retire_callback){++carrier_event_readers;retire_callback=false;}}
static ReadModule PlReadModule,WepReadModule;
static int oldWepId;static void*wepHeap4;
struct HeapProjection{int handle;u32 start,end;};static HeapProjection Heap[14];
struct OSHeapDescriptor{void*allocated;};static OSHeapDescriptor HeapHead[4];
#define MEM_HEAP_NUM 14
static void*cell_main,*cell_game,*cell_stage,*cell_dll;static int CurrentHeap=4;
static void OSFreeToHeap(int,void*){++weapon_heap_frees;}
#define Mem_free retirement_free
#include "retirement_module_memfree.inc"
#undef Mem_free
#define Mem_free ModuleMemFree
#define RE4DC_WEAPON_HEAP4 1
#include "retirement_read_methods.inc"
#undef RE4DC_WEAPON_HEAP4
#undef Mem_free
static int retirement_source_free(void*p,unsigned bytes,int heap){
    assert(p==backing()&&bytes==27456&&heap==backing_heap&&backing_active);backing_active=false;return 1;
}
#include "retirement_native_methods.inc"
#define ARAM_FREE_BASE 0x00200000
#include "retirement_unit_reset.inc"
static int memCheckHeapActive(int){return 1;}
static void MemSignalHeap(int){std::abort();}
static int re4dc_movie_world_before_heap_change(const void*p,unsigned bytes){return re4dc_cabin_carriers_before_heap(p,bytes);}
static void OSDestroyHeap(int){++heap_destroys;}
static u32 MemCheckHeapEnd(int heap){return Heap[heap].start;}
static int MemCreateHeap(int heap,u32 start,u32 end){++heap_creates;Heap[heap]={heap,start,end};return 1;}
#include "retirement_heap_methods.inc"
static void MemSetCurrentHeap(int heap){++heap_selects;CurrentHeap=heap;}
static void re4dc_motion_retire_all(){++room_retires;}
static void re4dc_effect_retire_room(){++room_retires;}
static void re4dc_ui_retire_room(){++room_retires;}
static void re4dc_room_enter(){++room_enters;}
#define RE4DC_TRACE_OWNER_RELEASE(x) ((void)0)
#define U32Set(value,n) ((value)=(n))
#include "retirement_room_method.inc"
struct SysProjection{u32 flags,language,region,unlock_flg,merc_stage[4],merc_rank[2];}sys_projection,*pSys=&sys_projection;
struct KeepProjection{u32 sys_flags,language,region,game_language,sys_unlock_flg,g_flags_54,sys_merc_stage[4],sys_merc_rank[2],card_checked,valid;}keep_projection,*pRK=&keep_projection;
static unsigned common_calls,reset_services,cancel_calls;static int SubScreenWk;
static void SubScreenExitCore(void*){++common_calls;}static void TaskAllClear(){++common_calls;}
struct RoomProjection{void stopRelData(){++common_calls;}}RoomData;
#define U8Set(value,n) ((value)=(n))
#define U32SetOfs(value,offset,n) (std::memcpy(reinterpret_cast<u8*>(value)+(offset),&(n),4))
static void systemVISetBlack(int){++reset_services;}static void VIFlush(){++reset_services;}static void VIWaitForRetrace(){++reset_services;}static void GXDrawDone(){++reset_services;}
static void retirement_cancel_dvd(){++cancel_calls;}static void retirement_cancel_aram(){++cancel_calls;}
static void SndSoftReset(){++reset_services;}static void DbmenuModuleInit(){++reset_services;}static void ResetDebugAlloc(){++reset_services;}static void SndSystemReset(){++reset_services;}static void RomFontSetting(){++reset_services;}
#include "retirement_system_methods.inc"
static void reset_controls(){
    module_frees=motion_unbinds=effect_unbinds=ui_enemy_unbinds=ui_player_unbinds=ui_weapon_unbinds=0;
    heap_destroys=heap_creates=heap_selects=room_enters=room_retires=weapon_heap_frees=0;retire_callback=false;
    PlReadModule={};WepReadModule={};wepHeap4=nullptr;oldWepId=4;
    CurrentHeap=4;for(unsigned i=0;i<14;++i)Heap[i]={int(i),0x90000000,0x90040000};
}
static void setup_carrier(){
    for(auto&m:EmReadModule)std::memset(&m,0,sizeof(m));prepare(false,1);exchange_module.id=0x13;exchange_module.flag=4;
    assert(SearchEmModule(0x13)==&EmReadModule[1]);
    int out=0;assert(EvtMgr.EvtReadMram(file_name,0x13,&out,0,0));
    assert(re4dc_cabin_source_module(arena,27456)==&EmReadModule[1]);
    assert(carriers[0].module==&EmReadModule[1]&&carriers[0].state==CarrierReady&&carriers[0].role==1);
    assert(!re4dc_cabin_carrier_before_free(arena));reset_controls();
}
int main(){
    std::cout<<std::unitbuf;
    arena=static_cast<unsigned char*>(mmap(reinterpret_cast<void*>(0x90000000),0x40000,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS|MAP_FIXED_NOREPLACE,-1,0));assert(arena==reinterpret_cast<void*>(0x90000000));
    unsigned cases=0;
    setup_carrier();const auto original=exchange_module;auto unit=loaded;auto carrier=carriers[0];
    InitModule(&exchange_module);assert(!std::memcmp(&exchange_module,&original,sizeof(original))&&!module_frees&&!motion_unbinds);++cases;
    assert(!re4dc_cabin_carriers_reset());assert(!std::memcmp(&loaded,&unit,sizeof(unit))&&!std::memcmp(&carriers[0],&carrier,sizeof(carrier)));++cases;
    DC.m_aram_free=77;DC.m_data_ctrl_flag=9;DC.retirement_sort_calls=DC.retirement_dummy_calls=0;
    DC.initDataUnit();assert(DC.m_aram_free==77&&DC.m_data_ctrl_flag==9&&!DC.retirement_sort_calls&&!DC.retirement_dummy_calls&&!std::memcmp(&loaded,&unit,sizeof(unit)));++cases;
    EmReadModule[0]={};EmReadModule[0].id=0x11;EmReadModule[0].pArc=arena+0x31000;EmReadModule[0].flag=4;
    EmReadModule[2]={};EmReadModule[2].id=0x14;EmReadModule[2].pArc=arena+0x32000;EmReadModule[2].flag=4;
    EmReadInit();assert(module_frees==2&&EmReadModule[0].pArc==nullptr&&EmReadModule[2].pArc==nullptr&&!std::memcmp(&exchange_module,&original,sizeof(original)));++cases;
    dma_calls=0;MemorySwap(arena,0x1000,27456);assert(carriers[0].role==2&&re4dc_cabin_carrier_before_free(arena));
    InitModule(&exchange_module);assert(!exchange_module.pArc&&module_frees==3);assert(re4dc_cabin_carriers_reset()&&!carriers[0].state&&!backing_active);++cases;
    DC.initDataUnit();assert(DC.m_aram_free==ARAM_FREE_BASE&&DC.m_data_ctrl_flag==1&&DC.retirement_sort_calls==1&&DC.retirement_dummy_calls==1);
    for(auto&u:actual_units){cDataUnit zero{};assert(!std::memcmp(&u,&zero,sizeof(u)));}++cases;
    std::cout<<"REAL_ENEMY13 module_refusal/reset_refusal/EmReadInit_partial/reverse_retry PASS\n";
    setup_carrier();PlReadModule={};PlReadModule.pArc=arena+0x31000;PlReadModule.flag=4;
    assert(!re4dc_cabin_source_module(PlReadModule.pArc,27456)&&re4dc_cabin_carrier_before_free(PlReadModule.pArc));
    ReleasePlData();assert(!PlReadModule.pArc&&module_frees==1&&ui_player_unbinds==1);++cases;
    WepReadModule={};WepReadModule.pArc=arena+0x32000;WepReadModule.flag=4;global.weapon_no_old=4;wepHeap4=arena+0x33000;
    assert(!re4dc_cabin_source_module(WepReadModule.pArc,27456)&&re4dc_cabin_carrier_before_free(WepReadModule.pArc));
    ReleaseWepData();assert(!WepReadModule.pArc&&global.weapon_no_old==0xff&&oldWepId==0xff&&!wepHeap4&&weapon_heap_frees==1&&module_frees==2);++cases;
    std::cout<<"DISJOINT_PLAYER_WEAPON real_carrier_no_refusal PASS\n";
    setup_carrier();PlReadModule={};PlReadModule.pArc=arena;PlReadModule.flag=4;
    assert(re4dc_cabin_source_module(PlReadModule.pArc,27456)==&EmReadModule[1]);ReleasePlData();
    assert(!PlReadModule.pArc&&!module_frees&&ui_player_unbinds==1&&exchange_module.pArc==arena);++cases;
    setup_carrier();WepReadModule={};WepReadModule.pArc=arena;WepReadModule.flag=4;global.weapon_no_old=4;wepHeap4=arena;
    ReleaseWepData();assert(WepReadModule.pArc==arena&&global.weapon_no_old==0xff&&oldWepId==0xff&&!wepHeap4&&weapon_heap_frees==1&&!module_frees);++cases;
    std::cout<<"SYNTHETIC_PLAYER_WEAPON_ALIAS wrapper_loss_unreachable_without_alias PASS\n";
    setup_carrier();auto before=Heap[4];assert(!MemDestroyHeap(4));assert(!heap_destroys&&Heap[4].handle==before.handle);++cases;
    assert(!MemReplaceHeap(3,4)&&!heap_destroys&&!heap_creates);++cases;
    std::memset(global.pad_16C,0x5a,sizeof(global.pad_16C));global.Status_flg[0]=global.Status_flg[1]=global.Status_flg[2]=0x1234;
    gameRoomMemInit();assert(!heap_destroys&&!heap_creates&&heap_selects==1&&room_enters==1&&room_retires==3);
    for(auto v:global.pad_16C)assert(!v);assert(!global.Status_flg[0]&&!global.Status_flg[1]&&!global.Status_flg[2]);
    assert(carriers[0].state==CarrierReady&&carriers[0].role==1&&exchange_module.pArc==arena);++cases;
    std::cout<<"REAL_HEAP_REFUSAL no_OS_destroy_but_room_wrapper_continues_global_reset PASS\n";
    setup_carrier();dma_calls=0;MemorySwap(arena,0x1000,27456);assert(re4dc_cabin_carriers_reset());
    assert(MemReplaceHeap(3,4)&&heap_destroys==1&&heap_creates==1);++cases;
    std::cout<<"REAL_RETIREMENT_THEN_HEAP_RETRY PASS\n";
    setup_carrier();auto*other=&EmReadModule[0];*other={};other->pArc=arena+0x31000;other->pModule=reinterpret_cast<OSModuleHeader*>(arena+0x33000);other->flag=6;retire_callback=true;
    InitModule(other);assert(!other->pArc&&module_frees==1&&carrier_event_readers==1);assert(!re4dc_cabin_carriers_reset());++cases;
    std::cout<<"CONTROLLED_UNLINK_CALLBACK new_reader_refuses_later_reset_without_rolling_back_other_module PASS\n";
    setup_carrier();auto retained=exchange_module;keep_projection={};sys_projection={};common_calls=reset_services=cancel_calls=0;global.IsMessageInit=1;
    MemClearAllHeap();assert(!heap_destroys&&!heap_creates&&exchange_module.pArc==arena);++cases;
    systemSoftReset();assert(!heap_destroys&&!heap_creates&&!std::memcmp(&exchange_module,&retained,sizeof(retained)));
    assert(pRK->valid==1&&common_calls==3&&reset_services==9&&cancel_calls==2&&!global.IsMessageInit);++cases;
    std::cout<<"REAL_ALL_HEAP_REFUSAL soft_reset_still_publishes_common_keep_valid_and_message_reset PASS\n";
    for(auto&m:EmReadModule)std::memset(&m,0,sizeof(m));prepare(false,1);exchange_module.id=0x13;exchange_module.flag=4;reset_controls();failure_mode=7;
    int partial_out=123;assert(!EvtMgr.EvtReadMram(file_name,0x13,&partial_out,0,0)&&!partial_out);
    assert(carriers[0].state==CarrierFailed&&carriers[0].role==1&&carriers[0].phase==2&&carriers[0].readers==1);
    auto partial_module=exchange_module;auto partial_carrier=carriers[0];auto partial_request=carrier_dma[0];
    InitModule(&exchange_module);assert(!module_frees&&!std::memcmp(&exchange_module,&partial_module,sizeof(partial_module)));++cases;
    assert(!re4dc_cabin_carriers_reset()&&!std::memcmp(&carriers[0],&partial_carrier,sizeof(partial_carrier))&&!std::memcmp(&carrier_dma[0],&partial_request,sizeof(partial_request))&&bytes_are(backing(),0x11));++cases;
    std::cout<<"REAL_PARTIAL_DMA module_and_reset_refuse_preserving_displaced_bytes PASS\n";
    setup_carrier();auto strict_module=exchange_module;retirement_stop_on_diagnostic=true;bool stopped=false;
    try{InitModule(&exchange_module);}catch(const RetirementDiagnosticStop&){stopped=true;}
    assert(stopped&&!module_frees&&!std::memcmp(&exchange_module,&strict_module,sizeof(strict_module)));retirement_stop_on_diagnostic=false;++cases;
    setup_carrier();EmReadModule[0]={};EmReadModule[0].id=0x11;EmReadModule[0].pArc=arena+0x31000;EmReadModule[0].flag=4;
    retirement_stop_on_diagnostic=true;stopped=false;try{EmReadInit();}catch(const RetirementDiagnosticStop&){stopped=true;}
    assert(stopped&&module_frees==1&&!EmReadModule[0].pArc&&exchange_module.pArc==arena);retirement_stop_on_diagnostic=false;++cases;
    setup_carrier();auto strict_unit=loaded;DC.m_aram_free=77;retirement_stop_on_diagnostic=true;stopped=false;
    try{DC.initDataUnit();}catch(const RetirementDiagnosticStop&){stopped=true;}
    assert(stopped&&DC.m_aram_free==77&&!std::memcmp(&loaded,&strict_unit,sizeof(strict_unit)));retirement_stop_on_diagnostic=false;++cases;
    setup_carrier();std::memset(global.pad_16C,0x5a,sizeof(global.pad_16C));retirement_stop_on_diagnostic=true;stopped=false;
    try{gameRoomMemInit();}catch(const RetirementDiagnosticStop&){stopped=true;}
    assert(stopped&&!heap_destroys&&!heap_selects&&!room_enters&&room_retires==3);for(auto v:global.pad_16C)assert(v==0x5a);retirement_stop_on_diagnostic=false;++cases;
    setup_carrier();keep_projection={};common_calls=reset_services=cancel_calls=0;global.IsMessageInit=1;retirement_stop_on_diagnostic=true;stopped=false;
    try{systemSoftReset();}catch(const RetirementDiagnosticStop&){stopped=true;}
    assert(stopped&&!heap_destroys&&!keep_projection.valid&&!common_calls&&reset_services==7&&cancel_calls==2&&global.IsMessageInit==1);retirement_stop_on_diagnostic=false;++cases;
    std::cout<<"STRICT_DIAGNOSTIC_STOP module/unit/room/soft_reset_do_not_continue_after_refusal PASS\n";
    std::cout<<"RETIREMENT_WRAPPER_CASES="<<cases<<" PASS\n";
    munmap(arena,0x40000);
}
