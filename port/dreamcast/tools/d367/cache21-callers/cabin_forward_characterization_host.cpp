#define RE4DC_EXEC_REAL_SCENARIO 1
#define RE4DC_EXEC_REAL_TRANSPORT 1
#define RE4DC_ARAM_ACTUAL 1
#define RE4DC_FORWARD_ACTUAL 1
#include "event_start_rollback_host.cpp"

char* EventMgr::NameChange(char* name){return name;}
static void exec_create_boundary(){std::abort();}
static unsigned failure_mode,diagnostics,backing_allocations,provider_calls,dma_calls,borrow_depth;
static bool mram_current,backing_active;
static u8* backing(){return arena+0x10000;}
static u8* saved(){return arena+0x20000;}
static u8* read_buffer(){return arena+0x30000;}
static void* aram_actual_alloc(unsigned,int,int){std::abort();}
static void aram_actual_free_boundary(void*,int){std::abort();}
static void re4dc_missing(const char*){++diagnostics;}
extern "C" int re4dc_cabin_source_allocation(const void* address,unsigned bytes,int* heap){
    if(!heap||bytes!=27456||!((address==arena&&mram_current)||(address==backing()&&backing_active)))return 0;
    *heap=4;return 1;
}
extern "C" const void* re4dc_cabin_source_module(const void* address,unsigned bytes){
    return address==arena&&mram_current&&bytes==27456?&exchange_module:nullptr;
}
extern "C" void* re4dc_cabin_source_alloc(unsigned bytes,int heap){
    assert(bytes==27456&&heap==4);++backing_allocations;
    if(failure_mode==2)return nullptr;
    backing_active=true;return backing();
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
    if(failure_mode==11)carriers[0].generation=++carrier_epoch;
    if(failure_mode==12)exchange_module.pArc=arena+0x8000;
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
    return token;
}
static void prepare(){
    std::strcpy(file_name,"event/evd/r11cs00.evd");setup();DC.m_DataUnit=actual_units;
    std::memset(actual_units,0,sizeof(actual_units));loaded.m_be_flag=1;
    loaded.m_size=27456;loaded.m_id=-1;
    std::strcpy(loaded.m_name,"evd/r11cs00.evd");
    for(auto& c:carriers)c={};for(auto& d:carrier_dma)d={};
    carrier_epoch=40;carrier_event_readers=carrier_dma_scope=carrier_dma_epoch=0;carrier_fault=false;
    backing_active=false;mram_current=true;
    failure_mode=diagnostics=backing_allocations=provider_calls=dma_calls=borrow_depth=0;
    swap_pushes=swap_pops=swap_calls=0;exchange_module={arena,27456};EvtMgr.readEm[0]={0,0,{0x55,0xaa}};
    std::memset(arena,0x11,27456);std::memset(backing(),0xcc,27456);
    loaded.setCommand(CMND_ARAM_LOAD,0x1000,1);
    assert(loaded.m_condition==4&&loaded.m_addr==reinterpret_cast<void*>(0x1000)&&!loaded.m_command&&loaded.m_be_flag==5);
    assert(carriers[0].generation==41&&re4dc_cabin_carrier_preload_epoch(&loaded,0x1000,27456)==41);
}
static bool bytes_are(const void* p,unsigned char value){
    const auto* bytes=static_cast<const u8*>(p);for(unsigned i=0;i<27456;++i)if(bytes[i]!=value)return false;return true;
}
int main(){
    std::cout<<std::unitbuf;
    arena=static_cast<unsigned char*>(mmap(reinterpret_cast<void*>(0x90000000),0x40000,
        PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS|MAP_FIXED_NOREPLACE,-1,0));
    assert(arena==reinterpret_cast<void*>(0x90000000));unsigned cases=0;
    for(unsigned mode=0;mode<=12;++mode){
        prepare();++cases;
        const unsigned captured_epoch=re4dc_cabin_carrier_preload_epoch(&loaded,0x1000,27456);
        assert(captured_epoch==41);failure_mode=mode;if(mode==1)carrier_event_readers=1;
        const auto before_reads=reads;const auto before_unit=loaded;int output=0;
        assert(EvtMgr.EvtReadMram(file_name,1,&output,0,0)==1&&u32(output)==u32(std::uintptr_t(exchange_module.pArc)));
        assert(EvtMgr.readEm[0].em==1&&EvtMgr.readEm[0].swapped==1&&swap_pushes==1&&!swap_pops&&swap_calls==1);
        assert(!borrow_depth&&!release_calls&&!std::memcmp(reads.data(),before_reads.data(),sizeof(reads)));
        if(mode!=9)assert(!std::memcmp(&loaded,&before_unit,sizeof(loaded)));
        int heap=-1;const unsigned receipt=re4dc_cabin_carrier_reverse_token(&loaded,&exchange_module,arena,27456,&heap);
        if(mode==0){assert(receipt==41&&heap==4&&!diagnostics&&carriers[0].role==1&&carriers[0].state==CarrierReady);
                    assert(bytes_are(arena,0x5a)&&bytes_are(backing(),0x11));}
        else if(mode==11){assert(receipt==42&&receipt!=captured_epoch&&!diagnostics);}
        else{assert(!receipt&&diagnostics);}
        if(mode>=1&&mode<=6)assert(bytes_are(arena,0x11));
        if(mode>=7&&mode<=11)assert(bytes_are(arena,0x5a));
        if(mode==12)assert(bytes_are(arena,0x11)&&carriers[0].state==CarrierReference);
        if(mode==7){assert(carriers[0].state==CarrierFailed&&carriers[0].role==1&&carriers[0].phase==2&&carriers[0].readers==1);
                    assert(bytes_are(backing(),0x11)&&!carrier_retirement_ready(carriers[0]));}
        if(mode==5)assert(carriers[0].readers==1&&carriers[0].phase==1);
        if(mode==8)assert(carriers[0].generation==42&&carriers[0].state==CarrierSwap&&carriers[0].phase==1);
        std::cout<<"FORWARD mode="<<mode<<" state="<<carriers[0].state<<" role="<<carriers[0].role<<" phase="<<carriers[0].phase
                 <<" readers="<<carriers[0].readers<<" generation="<<carriers[0].generation<<" diagnostic="<<diagnostics<<" caller_success=1 post_receipt="<<receipt<<" PASS\n";
    }
    std::cout<<"CABIN_FORWARD_CHARACTERIZATION_CASES="<<cases<<" PASS\n";
    munmap(arena,0x40000);
}
