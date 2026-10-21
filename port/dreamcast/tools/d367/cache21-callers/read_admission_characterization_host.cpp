#define RE4DC_EXEC_REAL_SCENARIO 1
#define RE4DC_EXEC_REAL_TRANSPORT 1
#define RE4DC_READ_ADMISSION_CHARACTERIZE 1
#include "event_start_rollback_host.cpp"

char* EventMgr::NameChange(char* name){return name;}
static void exec_create_boundary(){std::abort();}
static cDataUnit descriptor_pool[32];
static bool change_table_at_file_check;
static void admission_file_boundary(){if(change_table_at_file_check)EvtMgr.ReadTbl.NumDatTbl=0;}
static void reset_case(){
    std::strcpy(file_name,"event/evd/r11cs00.evd");setup();DC.m_nblock_read_stop=0;DC.m_DataUnit=descriptor_pool;DC.dbgHeap=0;
    std::memset(descriptor_pool,0,sizeof(descriptor_pool));admission_source_errors=admission_file_checks=0;change_table_at_file_check=false;
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
#if RE4DC_EVD_READ_ADMISSION_PREFLIGHT
        for(const auto& u:descriptor_pool)assert(!u.chk(1));
        assert(!admission_file_checks&&!admission_source_errors&&!transport_calls&&!release_calls);
#else
        for(unsigned j=0;j<32;++j)assert(descriptor_pool[j].chk(1)==int(j<=i));
        const auto& u=descriptor_pool[i];assert(u.m_condition==0&&u.m_command==0&&u.m_err==0);
        assert(!u.m_addr&&!u.m_malloc_addr&&u.m_size==27456&&!std::strcmp(u.m_name,"evd/r11cs00.evd"));
        assert(!transport_calls&&!release_calls);
#endif
    }
    int out=1;assert(!EvtMgr.EvtReadMram(file_name,0,&out,0,0)&&!out);
    assert(admission_source_errors==unsigned(!RE4DC_EVD_READ_ADMISSION_PREFLIGHT));
    std::cout<<"actual initial full-table admission refusal source OFF/ON control PASS\n";
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
    const auto before_unit=loaded;const auto before_descriptors=descriptor_pool[0];
#if RE4DC_EVD_READ_ADMISSION_PREFLIGHT
    assert(!EvtMgr.EvtReadMram(file_name,0,&out,0,0)&&!out);
    assert(!std::memcmp(&EvtMgr.readEm[0],&prior,sizeof(prior))&&!std::memcmp(&loaded,&before_unit,sizeof(loaded)));
    assert(!transport_calls&&!swap_calls&&!swap_pops&&!swap_pushes&&!release_calls&&!admission_file_checks);
    assert(!std::memcmp(&descriptor_pool[0],&before_descriptors,sizeof(before_descriptors)));
#else
    assert(EvtMgr.EvtReadMram(file_name,0,&out,0,0)&&u32(out)==u32(std::uintptr_t(arena)));
    assert(EvtMgr.readEm[0].em==0&&!EvtMgr.readEm[0].swapped&&prior.swapped==1);
    assert(transport_calls==1&&!swap_calls&&!swap_pops&&!swap_pushes&&!release_calls);
#endif
    assert(!std::memcmp(reads.data(),before_reads.data(),sizeof(reads)));
    std::cout<<"existing swapped role admission source OFF/ON control PASS\n";
#if RE4DC_EVD_READ_ADMISSION_PREFLIGHT
    for(unsigned mode:{0U,1U,2U})for(unsigned swapped:{1U,2U,255U}){
        reset_case();++cases;EvtMgr.readEm[0]={1,u8(swapped),{0x12,0x34}};
        loaded.m_condition=4;loaded.m_addr=arena+0x10000;
        const auto read_snapshot=reads;const auto unit_snapshot=loaded;const auto em_snapshot=EvtMgr.readEm[0];
        assert(!EvtMgr.EvtReadSub(file_name,mode==2,mode==1, &out,0,0)&&!out);
        assert(!std::memcmp(reads.data(),read_snapshot.data(),sizeof(reads))&&!std::memcmp(&loaded,&unit_snapshot,sizeof(loaded)));
        assert(!std::memcmp(&EvtMgr.readEm[0],&em_snapshot,sizeof(em_snapshot))&&!swap_pushes&&!swap_calls&&!transport_calls);
    }
#endif
    // A full table may still reuse its existing unswapped preload owner.
    for(unsigned module:{0U,1U}){
        reset_case();++cases;for(unsigned i=1;i<8;++i){reads[i].FlagBe8=3;reads[i].Count=1;std::snprintf(reads[i].Name,sizeof(reads[i].Name),"occupied-read%u",i);reads[i].Dat=&loaded;}
        loaded.m_condition=4;loaded.m_addr=arena+0x10000;EvtMgr.readEm[0]={1,0,{0x12,0x34}};
        const auto preload_reads=reads;assert(EvtMgr.EvtReadMram(file_name,module,&out,0,0));
        assert(transport_calls==unsigned(!module)&&swap_calls==module&&!admission_file_checks&&!std::memcmp(reads.data(),preload_reads.data(),sizeof(reads)));
    }
    // File work can invalidate capacity after preflight; this guard intentionally
    // does not claim an admission reservation or delete a stale descriptor.
    reset_case();++cases;assert(EvtMgr.DelRead(file_name));change_table_at_file_check=true;
    assert(!EvtMgr.EvtReadMram(file_name,0,&out,0,0)&&!out&&admission_file_checks==1&&descriptor_pool[0].chk(1));
    assert(!transport_calls&&!release_calls);
#if RE4DC_EVD_READ_ADMISSION_PREFLIGHT
    for(unsigned refusal:{0U,1U,2U,3U}){
        reset_case();++cases;assert(EvtMgr.DelRead(file_name));
        char long_name[80];std::memset(long_name,'x',sizeof(long_name));std::memcpy(long_name,"event/evd/",10);long_name[79]=0;
        if(refusal==0)EvtMgr.ReadTbl.pWork=nullptr;
        if(refusal==1)for(unsigned i=0;i<8;++i){reads[i].FlagBe8=3;std::snprintf(reads[i].Name,sizeof(reads[i].Name),"full%u",i);}
        if(refusal==3)EvtMgr.ReadTbl.NumDatTbl=-1;
        assert(!EvtMgr.EvtReadMram(refusal==2?long_name:file_name,0,&out,0,0)&&!out&&!admission_file_checks);
        for(const auto& u:descriptor_pool)assert(!u.chk(1));
    }
    // Last allowed slot is enough; ordinary fresh admission still succeeds.
    reset_case();++cases;assert(EvtMgr.DelRead(file_name));
    for(unsigned i=0;i<7;++i){reads[i].FlagBe8=3;std::snprintf(reads[i].Name,sizeof(reads[i].Name),"full%u",i);}
    assert(EvtMgr.EvtReadMram(file_name,0,&out,0,0)&&reads[7].Dat==descriptor_pool);
    assert(admission_file_checks==1&&transport_calls==1&&descriptor_pool[0].chk(1));
    reset_case();++cases;assert(EvtMgr.DelRead(file_name));
    char max_name[48];const auto prefix=47-std::strlen(file_name);std::memset(max_name,'x',prefix);std::strcpy(max_name+prefix,file_name);
    assert(std::strlen(max_name)==47&&EvtMgr.EvtReadMram(max_name,0,&out,0,0)&&admission_file_checks==1);
#endif
    reset_case();++cases;std::array<DatTblEntry,9> oversized={};
    for(unsigned i=0;i<8;++i){oversized[i].FlagBe8=3;std::snprintf(oversized[i].Name,sizeof(oversized[i].Name),"full%u",i);}
    EvtMgr.ReadTbl={9,oversized.data()};const auto oversized_before=oversized;
    assert(!EvtMgr.EvtReadMram(file_name,0,&out,0,0)&&!out);
    assert(admission_file_checks==unsigned(!RE4DC_EVD_READ_ADMISSION_PREFLIGHT));
    assert(descriptor_pool[0].chk(1)==int(!RE4DC_EVD_READ_ADMISSION_PREFLIGHT));
    assert(!std::memcmp(oversized.data(),oversized_before.data(),sizeof(oversized)));
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
    std::cout<<"READ_ADMISSION_CHARACTERIZATION_CASES="<<cases<<" cabin="<<RE4DC_CABIN_SOURCE<<" preflight="<<RE4DC_EVD_READ_ADMISSION_PREFLIGHT<<" PASS\n";
    assert(mprotect(arena,0x20000,PROT_READ|PROT_WRITE)==0);munmap(arena,0x20000);
}
