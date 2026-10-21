#define RE4DC_EXEC_REAL_SCENARIO 1
#define RE4DC_EXEC_REAL_TRANSPORT 1
#define RE4DC_ARAM_ACTUAL 1
#define RE4DC_FORWARD_ACTUAL 1
#define RE4DC_READ_ADMISSION_CHARACTERIZE 1
#define RE4DC_READ_ACTUAL_EFFECT 1
#include "event_start_rollback_host.cpp"

char* EventMgr::NameChange(char* name){return name;}
static void exec_create_boundary(){std::abort();}
static unsigned failure_mode,diagnostics,backing_allocations,provider_calls,dma_calls,borrow_depth;
static int module_heap,backing_heap;
static bool mram_current,backing_active;
static ReadModule alternate_module;
static std::array<DatTblEntry,8> alternate_reads,before_effect_reads;
static cDataUnit before_effect_unit;
static EvtReadEm before_effect_em;
static void admission_file_boundary(){}
static u8* backing(){return arena+0x10000;}
static u8* saved(){return arena+0x20000;}
static u8* read_buffer(){return arena+0x30000;}
static void* aram_actual_alloc(unsigned,int,int){std::abort();}
static void aram_actual_free_boundary(void*,int){std::abort();}
static void re4dc_missing(const char*){++diagnostics;}
extern "C" int re4dc_cabin_source_allocation(const void* address,unsigned bytes,int* heap){
    if(!heap||!bytes||bytes>27456||!((address==arena&&mram_current)||(address==backing()&&backing_active)))return 0;
    *heap=address==arena?module_heap:backing_heap;return 1;
}
#include "forward_source_module.inc"
extern "C" void* re4dc_cabin_source_alloc(unsigned bytes,int heap){
    assert(bytes==27456&&heap==module_heap);++backing_allocations;
    if(failure_mode==2)return nullptr;
    backing_active=true;backing_heap=heap;return backing();
}
extern "C" int re4dc_cabin_source_free(void*,unsigned,int){std::abort();}
extern "C" int re4dc_cabin_source_swap_buffer(unsigned type,unsigned address,unsigned bytes){
    return bytes==27456&&(type==0?address==u32(std::uintptr_t(saved())):type==1&&address==u32(std::uintptr_t(read_buffer())));
}
static bool run(const char* name,unsigned bytes,void* dst,unsigned certificate){
    assert(!std::strcmp(name,"evd/r11cs00.evd")&&bytes==27456&&certificate==0x71ab9c4d);
    ++provider_calls;if(!dst)return true;
    assert(dst==backing());if(failure_mode==3)return false;
    std::memset(dst,0x5a,bytes);return true;
}
static void forward_effect_boundary(int){
    std::memcpy(&before_effect_unit,&loaded,sizeof(loaded));before_effect_em=EvtMgr.readEm[0];
    std::memcpy(before_effect_reads.data(),EvtMgr.ReadTbl.pWork,sizeof(before_effect_reads));
    if(failure_mode==11)carriers[0].generation=++carrier_epoch;
    if(failure_mode==12)exchange_module.pArc=arena+0x8000;
    if(failure_mode==13)forward_module_binding=&alternate_module;
    if(failure_mode==14)exchange_module.size+=32;
    if(failure_mode==15)module_heap=5;
    if(failure_mode==16)++EvtMgr.ReadTbl.pWork[0].Count;
    if(failure_mode==17)EvtMgr.readEm[0].pad_2[0]^=1;
    if(failure_mode==18)loaded.m_id=77;
    if(failure_mode==19){alternate_reads=reads;EvtMgr.ReadTbl.pWork=alternate_reads.data();}
    if(failure_mode==20)--EvtMgr.ReadTbl.NumDatTbl;
    if(failure_mode==21)carrier_event_readers=1;
}
struct Re4dcDvdBorrowScope{Re4dcDvdBorrowScope(){++borrow_depth;}~Re4dcDvdBorrowScope(){--borrow_depth;}};
#define ALIGN32(n) (((n)+31U)&~31U)
#define DVD_BUFF saved()
#define DVD_BUFF2 read_buffer()
static int re4dc_event_file_range(unsigned,unsigned){std::abort();}
static void re4dc_event_file_reject_swap(){std::abort();}
#include "forward_actual_memoryswap.inc"

int AramBoundary::DmaTransReq(int type,u32 src,u32 dst,u32 bytes,int wait){
    assert(wait==1&&bytes==27456);++dma_calls;
    if((failure_mode==4&&dma_calls==1)||(failure_mode==6&&dma_calls==2))return -1;
    static unsigned requests[2];const void* request=&requests[dma_calls-1];
    assert(re4dc_cabin_carrier_dma_admit(request,type,src,dst,bytes)==1);
    const int token=re4dc_cabin_carrier_dma_copy(request,type,src,dst,bytes);assert(token>0);
    if((failure_mode==5&&dma_calls==1)||(failure_mode==7&&dma_calls==2))return -1;
    assert(re4dc_cabin_carrier_dma_callback(token)==request);
    assert(re4dc_cabin_carrier_dma_release(request,0)==1);
    if(dma_calls==1){
        if(failure_mode==8){carriers[0].generation=++carrier_epoch;}
        if(failure_mode==9)loaded.m_name[0]='x';
        if(failure_mode==10)mram_current=false;
    }
    if(dma_calls==2){
        if(failure_mode==22)++EvtMgr.ReadTbl.pWork[0].Count;
        if(failure_mode==23)EvtMgr.readEm[0].pad_2[0]^=1;
        if(failure_mode==24)loaded.m_id=88;
        if(failure_mode==25)forward_module_binding=&alternate_module;
        if(failure_mode==26)exchange_module.size+=32;
        if(failure_mode==27)module_heap=5;
    }
    return token;
}
static void prepare(bool fresh,unsigned effect_refs){
    std::strcpy(file_name,"event/evd/r11cs00.evd");setup();DC.m_DataUnit=actual_units;
    std::memset(actual_units,0,sizeof(actual_units));
    for(auto& c:carriers)c={};for(auto& d:carrier_dma)d={};
    carrier_epoch=40;carrier_event_readers=carrier_dma_scope=carrier_dma_epoch=0;carrier_fault=false;
    backing_active=false;mram_current=true;module_heap=backing_heap=4;
    failure_mode=diagnostics=backing_allocations=provider_calls=dma_calls=borrow_depth=0;
    swap_pushes=swap_pops=swap_calls=forward_emread_calls=0;module_missing=swap_refuse=false;
    exchange_module={arena,27456};alternate_module=exchange_module;forward_module_binding=&exchange_module;
    EvtMgr.readEm[0]={0,0,{0x55,0xaa}};
    admission_effect_system={};admission_effect_system.ownerCnt[0x10]=effect_refs;
    std::memset(effect_release_dispatch,0,sizeof(effect_release_dispatch));
    admission_file_checks=admission_source_errors=0;
    std::memset(arena,0x11,27456);std::memset(backing(),0xcc,27456);
    if(fresh){assert(EvtMgr.DelRead(file_name));}
    else{
        loaded.m_be_flag=1;loaded.m_size=27456;loaded.m_id=-1;
        std::strcpy(loaded.m_name,"evd/r11cs00.evd");
        loaded.setCommand(CMND_ARAM_LOAD,0x1000,1);
        assert(loaded.m_condition==4&&loaded.m_addr==reinterpret_cast<void*>(0x1000)&&!loaded.m_command&&loaded.m_be_flag==5);
        assert(carriers[0].generation==41&&re4dc_cabin_carrier_preload_epoch(&loaded,0x1000,27456)==41);
    }
}
static bool bytes_are(const void* p,unsigned char value){
    const auto* bytes=static_cast<const u8*>(p);for(unsigned i=0;i<27456;++i)if(bytes[i]!=value)return false;return true;
}
int main(){
    std::cout<<std::unitbuf;
    arena=static_cast<unsigned char*>(mmap(reinterpret_cast<void*>(0x90000000),0x40000,
        PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS|MAP_FIXED_NOREPLACE,-1,0));
    assert(arena==reinterpret_cast<void*>(0x90000000));unsigned cases=0;
    for(unsigned effect_refs:{1U,2U})for(bool fresh:{false,true})for(unsigned mode=0;mode<=32;++mode){
        if(fresh&&(mode==1||mode>=28))continue;
        prepare(fresh,effect_refs);++cases;
        if(mode==32){
            // Produce real native role2 by two complete exchanges. The current
            // metadata/owner is an explicit unsupported legacy control.
            MemorySwap(arena,0x1000,27456);dma_calls=0;MemorySwap(arena,0x1000,27456);
            assert(carriers[0].role==2&&carriers[0].state==CarrierReady&&!carriers[0].mram);
            swap_calls=dma_calls=0;
            assert(!re4dc_cabin_carrier_preload_epoch(&loaded,0x1000,27456));
        }
        failure_mode=mode;
        if(mode==1)carrier_event_readers=1; // Initial zero epoch stays legacy.
        if(mode==28)reads[0].Etc=1;
        if(mode==29)reads[0].FlagBe8=1;
        if(mode==30)reads[0].Count=0x8000;
        if(mode==31)reads[0].dat2=arena+0x3f000;
        int output=0x11223344;
        const bool unsupported=mode==1||mode>=28;
        const bool success=!RE4DC_EVD_FORWARD_RECEIPT||mode==0||unsupported;
        const bool stopped_before_swap=RE4DC_EVD_FORWARD_RECEIPT&&mode>=11&&mode<=21;
        const int result=EvtMgr.EvtReadMram(file_name,0x13,&output,0,0);
        assert(result==int(success));
        assert(success?u32(output)==u32(std::uintptr_t(exchange_module.pArc)):output==0);
        assert(forward_emread_calls==unsigned(fresh)&&admission_file_checks==unsigned(fresh));
        assert(EvtMgr.readEm[0].em==0x13&&EvtMgr.readEm[0].swapped==unsigned(success));
        assert(swap_pushes==1&&!swap_pops&&swap_calls==unsigned(!stopped_before_swap));
        assert(!borrow_depth&&!release_calls);
        // Failure never manufactures an effect rollback: both reference-count
        // and five-helper final-dispatch states retain the actual Push result.
        assert(admission_effect_system.ownerCnt[0x10]==effect_refs-1);
        for(auto count:effect_release_dispatch)assert(count==unsigned(effect_refs==1));
        auto expected_reads=before_effect_reads;
        if(mode==16||mode==22)++expected_reads[0].Count;
        assert(!std::memcmp(EvtMgr.ReadTbl.pWork,expected_reads.data(),sizeof(expected_reads)));
        cDataUnit expected_unit;std::memcpy(&expected_unit,&before_effect_unit,sizeof(expected_unit));
        if(mode==9)expected_unit.m_name[0]='x';
        if(mode==18)expected_unit.m_id=77;
        if(mode==24)expected_unit.m_id=88;
        assert(!std::memcmp(&loaded,&expected_unit,sizeof(loaded)));
        auto expected_em=before_effect_em;expected_em.swapped=success;
        if(mode==17||mode==23)expected_em.pad_2[0]^=1;
        assert(!std::memcmp(&EvtMgr.readEm[0],&expected_em,sizeof(expected_em)));
        if(mode==19)assert(EvtMgr.ReadTbl.pWork==alternate_reads.data());
        if(mode==20)assert(EvtMgr.ReadTbl.NumDatTbl==7);
        if(mode==13||mode==25)assert(forward_module_binding==&alternate_module);
        if(mode==14||mode==26)assert(exchange_module.size==27488);
        if(mode==15||mode==27)assert(module_heap==5);
        int heap=-1;const unsigned receipt=re4dc_cabin_carrier_reverse_token(&loaded,&exchange_module,arena,27456,&heap);
        if(stopped_before_swap){
            assert(!receipt&&!diagnostics&&!backing_active&&!backing_allocations&&bytes_are(arena,0x11));
            assert(carriers[0].state==CarrierReference&&!carriers[0].role&&!carriers[0].phase&&!carriers[0].readers);
            assert(carriers[0].generation==(mode==11?42U:41U));
        }else if(mode==0||mode==14||mode==15||mode==16||mode==17||mode==18||mode==19||mode==20||
                 mode==22||mode==23||mode==24||mode==26||mode>=28){
            assert(receipt==41&&!diagnostics&&carriers[0].state==CarrierReady&&carriers[0].role==1);
            assert(bytes_are(arena,0x5a)&&bytes_are(backing(),0x11));
        }else if(mode==11){assert(receipt==42&&!diagnostics);}
        else if(mode==13){assert(!receipt&&!diagnostics&&carriers[0].state==CarrierReady);}
        else{assert(!receipt&&diagnostics);}
        if(mode>=1&&mode<=6)assert(bytes_are(arena,0x11));
        if((mode>=7&&mode<=10)||mode>=22)assert(bytes_are(arena,0x5a));
        if(mode==12)assert(bytes_are(arena,0x11)&&carriers[0].state==CarrierReference);
        if(mode==7){
            assert(carriers[0].state==CarrierFailed&&carriers[0].role==1&&carriers[0].phase==2&&carriers[0].readers==1);
            assert(bytes_are(backing(),0x11)&&!carrier_retirement_ready(carriers[0]));
            const auto carrier_before=carriers[0];const auto request_before=carrier_dma[0];
            const auto row_before=EvtMgr.ReadTbl.pWork[0];
            assert(!EvtMgr.EvtFree(file_name));
            assert(!std::memcmp(&carriers[0],&carrier_before,sizeof(carrier_before)));
            assert(!std::memcmp(&carrier_dma[0],&request_before,sizeof(request_before)));
            assert(!std::memcmp(&EvtMgr.ReadTbl.pWork[0],&row_before,sizeof(row_before)));
            assert(bytes_are(arena,0x5a)&&bytes_are(backing(),0x11));
        }
        if(mode==5)assert(carriers[0].readers==1&&carriers[0].phase==1);
        if(mode==8)assert(carriers[0].generation==42&&carriers[0].state==CarrierSwap&&carriers[0].phase==1);
        std::cout<<"FORWARD mode="<<mode<<" fresh="<<fresh<<" effect_refs="<<effect_refs<<" state="<<carriers[0].state
                 <<" role="<<carriers[0].role<<" phase="<<carriers[0].phase<<" readers="<<carriers[0].readers
                 <<" generation="<<carriers[0].generation<<" caller_success="<<result<<" post_receipt="<<receipt<<" PASS\n";
    }
    std::cout<<"CABIN_FORWARD_RECEIPT_CASES="<<cases<<" enabled="<<RE4DC_EVD_FORWARD_RECEIPT<<" PASS\n";
    munmap(arena,0x40000);
}
