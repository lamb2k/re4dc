#include "forward_diagnostic_base.cpp"
#include <iomanip>
static unsigned diagnostic_mode,case_mode,case_refs;
static bool case_fresh;
static int*case_output;
static unsigned bytes_value(const void*p){u8 n=*static_cast<const u8*>(p);return bytes_are(p,n)?n:256;}
static void snapshot(const char*outcome,int result){
    int heap=-1;const unsigned token=re4dc_cabin_carrier_reverse_token(&loaded,&exchange_module,arena,27456,&heap);
    unsigned pending=0;for(const auto&request:carrier_dma)pending+=request.state!=0;
    std::cout<<"{\"mode\":"<<case_mode<<",\"fresh\":"<<case_fresh<<",\"effect_refs\":"<<case_refs
      <<",\"guard\":"<<RE4DC_EVD_FORWARD_RECEIPT<<",\"diagnostic_stop\":"<<diagnostic_mode
      <<",\"outcome\":\""<<outcome<<"\",\"result\":"<<result<<",\"output\":"<<u32(*case_output)
      <<",\"diagnostics\":"<<diagnostics<<",\"swapped\":"<<unsigned(EvtMgr.readEm[0].swapped)
      <<",\"pushes\":"<<swap_pushes<<",\"pops\":"<<swap_pops<<",\"swap_calls\":"<<swap_calls
      <<",\"effect_count\":"<<admission_effect_system.ownerCnt[0x10]<<",\"effect_final_dispatches\":"<<effect_release_dispatch[0]
      <<",\"state\":"<<carriers[0].state<<",\"role\":"<<carriers[0].role<<",\"phase\":"<<carriers[0].phase
      <<",\"readers\":"<<carriers[0].readers<<",\"generation\":"<<carriers[0].generation
      <<",\"post_token\":"<<token<<",\"post_heap\":"<<heap<<",\"pending_requests\":"<<pending
      <<",\"borrow_depth\":"<<borrow_depth<<",\"module_bytes\":"<<bytes_value(arena)
      <<",\"backing_active\":"<<backing_active<<",\"backing_bytes\":"<<bytes_value(backing())
      <<",\"backing_allocations\":"<<backing_allocations<<",\"dma_calls\":"<<dma_calls
      <<",\"fresh_module_lookups\":"<<forward_emread_calls<<"}\n";
    std::cout.flush();
}
static void forward_missing_observer(){
    if(!diagnostic_mode)return;
    snapshot("halt",-1);
    // No automatic-object unwind: the target missing loop never reaches the
    // MemorySwap borrow-scope destructor. Each control has its own process.
    std::_Exit(73);
}
int main(int argc,char**argv){
    assert(argc==5);case_mode=std::strtoul(argv[1],nullptr,10);case_fresh=std::atoi(argv[2]);case_refs=std::strtoul(argv[3],nullptr,10);diagnostic_mode=std::atoi(argv[4]);
    assert(case_mode<=32&&(case_refs==1||case_refs==2)&&diagnostic_mode<=1);
    arena=static_cast<unsigned char*>(mmap(reinterpret_cast<void*>(0x90000000),0x40000,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS|MAP_FIXED_NOREPLACE,-1,0));assert(arena==reinterpret_cast<void*>(0x90000000));
    prepare(case_fresh,case_refs);
    if(case_mode==32){MemorySwap(arena,0x1000,27456);dma_calls=0;MemorySwap(arena,0x1000,27456);assert(carriers[0].role==2);swap_calls=dma_calls=0;}
    failure_mode=case_mode;
    if(case_mode==1)carrier_event_readers=1;
    if(case_mode==28)reads[0].Etc=1;
    if(case_mode==29)reads[0].FlagBe8=1;
    if(case_mode==30)reads[0].Count=0x8000;
    if(case_mode==31)reads[0].dat2=arena+0x3f000;
    int output=0x11223344;case_output=&output;
    const int result=EvtMgr.EvtReadMram(file_name,0x13,&output,0,0);
    snapshot("return",result);munmap(arena,0x40000);
}
