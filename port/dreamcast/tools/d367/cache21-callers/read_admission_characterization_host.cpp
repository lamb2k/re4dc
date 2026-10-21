#define RE4DC_EXEC_REAL_SCENARIO 1
#define RE4DC_EXEC_REAL_TRANSPORT 1
#define RE4DC_READ_ADMISSION_CHARACTERIZE 1
#include "event_start_rollback_host.cpp"

char* EventMgr::NameChange(char* name){return name;}
static void exec_create_boundary(){std::abort();}
static cDataUnit descriptor_pool[32];
static void reset_case(){
    std::strcpy(file_name,"event/evd/r11cs00.evd");setup();DC.m_nblock_read_stop=0;DC.m_DataUnit=descriptor_pool;DC.dbgHeap=0;
    std::memset(descriptor_pool,0,sizeof(descriptor_pool));admission_source_errors=0;
    module_missing=swap_refuse=false;swap_pushes=swap_pops=swap_calls=transport_calls=0;
    transport_refuse=transport_other_flags=false;cabin_clear_refuse=false;clear_refusals=0;
    exchange_module={arena,27456};loaded.m_size=27456;
    EvtMgr.readEm[0]={0,0,{0x55,0xaa}};
}
int main(){
    std::cout<<std::unitbuf;
    arena=static_cast<unsigned char*>(mmap(reinterpret_cast<void*>(0x90000000),0x20000,
        PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS|MAP_FIXED_NOREPLACE,-1,0));
    assert(arena==reinterpret_cast<void*>(0x90000000));unsigned cases=0;
    reset_case();++cases;assert(EvtMgr.DelRead(file_name));EvtMgr.ReadTbl.NumDatTbl=0;
    for(unsigned i=0;i<32;++i){
        int out=1;assert(!EvtMgr.EvtReadMram(file_name,0,&out,0,0)&&!out);
        for(unsigned j=0;j<32;++j)assert(descriptor_pool[j].chk(1)==int(j<=i));
        const auto& u=descriptor_pool[i];assert(u.m_condition==0&&u.m_command==0&&u.m_err==0);
        assert(!u.m_addr&&!u.m_malloc_addr&&u.m_size==27456&&!std::strcmp(u.m_name,"evd/r11cs00.evd"));
        assert(!transport_calls&&!release_calls);
    }
    int out=1;assert(!EvtMgr.EvtReadMram(file_name,0,&out,0,0)&&!out&&admission_source_errors==1);
    std::cout<<"actual fresh SetRead refusal consumes all32 active descriptors without transport PASS\n";
    reset_case();++cases;
    auto* acquired=DC.setData(const_cast<char*>("evd/r11cs00.evd"));assert(acquired==descriptor_pool&&acquired->chk(1));
    assert(acquired->setClear()&&acquired->chk(1)&&acquired->m_size==27456);
    assert(DC.getNewUnit()==descriptor_pool+1);
    assert(acquired->setDelete()&&!acquired->chk(1)&&!acquired->m_size);
    assert(DC.getNewUnit()==acquired);
    std::cout<<"actual clear retains descriptor; delete permits exact slot reuse PASS\n";
    reset_case();++cases;
    loaded.m_condition=4;loaded.m_addr=arena+0x10000;EvtMgr.readEm[0]={1,1,{0x55,0xaa}};
    const auto before_reads=reads;const auto prior=EvtMgr.readEm[0];
    assert(EvtMgr.EvtReadMram(file_name,0,&out,0,0)&&u32(out)==u32(std::uintptr_t(arena)));
    assert(EvtMgr.readEm[0].em==0&&!EvtMgr.readEm[0].swapped&&prior.swapped==1);
    assert(transport_calls==1&&!swap_calls&&!swap_pops&&!swap_pushes&&!release_calls);
    assert(!std::memcmp(reads.data(),before_reads.data(),sizeof(reads)));
    std::cout<<"existing swapped role overwritten before em0 synthetic promotion PASS\n";
    for(unsigned fail:{0U,1U,2U}){
        reset_case();++cases;loaded.m_condition=4;loaded.m_addr=arena+0x10000;
        module_missing=fail==0;exchange_module.size=fail==1?27455:27456;swap_refuse=fail==2;
        const auto before_unit=loaded;const auto before=reads;
        std::array<u8,0x20000> data;std::memcpy(data.data(),arena,data.size());out=1;
        const int result=EvtMgr.EvtReadMram(file_name,1,&out,0,0);
        assert(swap_pushes==1&&!swap_pops&&!release_calls&&!transport_calls);
        assert(!std::memcmp(&loaded,&before_unit,sizeof(loaded))&&!std::memcmp(arena,data.data(),data.size()));
        if(fail<2){assert(!result&&!out&&!EvtMgr.ReadTbl.ChkDat(file_name)&&!swap_calls);}
        else{assert(result&&u32(out)==u32(std::uintptr_t(arena))&&swap_calls==1&&EvtMgr.readEm[0].swapped==1);
             assert(!std::memcmp(reads.data(),before.data(),sizeof(reads)));}
    }
    std::cout<<"actual prior read caller mutates after missing/undersized module and accepts void swap refusal PASS\n";
    std::cout<<"READ_ADMISSION_CHARACTERIZATION_CASES="<<cases<<" cabin="<<RE4DC_CABIN_SOURCE<<" PASS\n";
    assert(mprotect(arena,0x20000,PROT_READ|PROT_WRITE)==0);munmap(arena,0x20000);
}
