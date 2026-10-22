#define RE4DC_EXEC_REAL_SCENARIO 1
#define RE4DC_EXEC_REAL_TRANSPORT 1
#define RE4DC_ARAM_ACTUAL 1
#include "event_start_rollback_host.cpp"

char* EventMgr::NameChange(char* name){return name;}
static void exec_create_boundary(){std::abort();}
static unsigned alloc_calls,provider_calls,native_frees,mutation;
static bool allow_allocation,allocation_active;
static cDataUnit after_mutation_unit;
static std::array<DatTblEntry,8> after_mutation_reads;
static EvtReadEm after_mutation_em;
static std::array<CabinCarrier,3> after_mutation_carriers;
static std::array<CabinCarrierDma,16> after_mutation_dma;
static void* aram_actual_alloc(unsigned bytes,int flag,int heap){
    assert(bytes==27456&&flag==1&&heap==13);++alloc_calls;
    if(alloc_calls==2&&mutation){
        switch(mutation){
        case 1:carriers[0].generation=++carrier_epoch;break;
        case 2:++reads[0].Count;break;
        case 3:EvtMgr.readEm[0].pad_2[0]^=1;break;
        case 4:loaded.m_id=73;break;
        case 5:carriers[0].readers=1;break;
        case 6:carrier_event_readers=1;break;
        case 7:carriers[0].phase=2;break;
        case 8:carrier_dma[0].state=1;carrier_dma[0].owner=0;break;
        case 9:loaded.m_name[0]='x';break;
        default:std::abort();
        }
        after_mutation_unit=loaded;after_mutation_reads=reads;after_mutation_em=EvtMgr.readEm[0];
        std::memcpy(after_mutation_carriers.data(),carriers,sizeof(carriers));
        std::memcpy(after_mutation_dma.data(),carrier_dma,sizeof(carrier_dma));
    }
    if(!allow_allocation)return nullptr;
    allocation_active=true;return arena;
}
static void aram_actual_free_boundary(void* address,int heap){
    assert(address==arena&&heap==4&&allocation_active);allocation_active=false;
}
extern "C" int re4dc_cabin_source_allocation(const void* address,unsigned bytes,int* heap){
    if(address!=arena||!allocation_active||bytes>27456||!heap)return 0;
    *heap=4;return 1;
}
extern "C" const void* re4dc_cabin_source_module(const void*,unsigned){return nullptr;}
extern "C" int re4dc_cabin_source_free(void* address,unsigned bytes,int heap){
    assert(address==arena&&bytes==27456&&heap==4&&allocation_active);
    allocation_active=false;++native_frees;return 1;
}
static bool run(const char* name,unsigned bytes,void* dst,unsigned certificate){
    assert(!std::strcmp(name,"evd/r11cs00.evd")&&bytes==27456&&dst==arena&&certificate==0x71ab9c4d);
    ++provider_calls;std::memset(dst,0x5a,bytes);return true;
}
static void prepare(){
    std::strcpy(file_name,"event/evd/r11cs00.evd");setup();
    DC.m_DataUnit=actual_units;alloc_calls=provider_calls=native_frees=mutation=0;
    allow_allocation=allocation_active=false;
    for(auto& c:carriers)c={};for(auto& d:carrier_dma)d={};
    carrier_epoch=41;carrier_event_readers=carrier_dma_scope=carrier_dma_epoch=0;carrier_fault=false;
    std::memset(&loaded,0,sizeof(loaded));loaded.m_condition=4;loaded.m_be_flag=5;loaded.m_addr=reinterpret_cast<void*>(0x1000);
    loaded.dest=0x1000;loaded.m_size=27456;loaded.m_id=-1;std::strcpy(loaded.m_name,"evd/r11cs00.evd");
    EvtMgr.readEm[0]={0,0,{0x55,0xaa}};
    auto& c=carriers[0];c.unit=&loaded;c.generation=41;c.logical=0x1000;c.bytes=27456;
    c.heap=c.backing_heap=-1;c.state=CarrierReference;
}
static unsigned epoch(){return re4dc_cabin_carrier_preload_epoch(&loaded,0x1000,27456);}
static auto carrier_snapshot(){return std::array<CabinCarrier,3>{carriers[0],carriers[1],carriers[2]};}
int main(){
    std::cout<<std::unitbuf;
    arena=static_cast<unsigned char*>(mmap(reinterpret_cast<void*>(0x90000000),0x20000,
        PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS|MAP_FIXED_NOREPLACE,-1,0));
    assert(arena==reinterpret_cast<void*>(0x90000000));unsigned cases=0;
    for(unsigned prior_wait:{0U,1U})for(unsigned prior_count:{1U,2U}){
        prepare();++cases;loaded.wait=prior_wait;reads[0].Count=prior_count;
        const auto before=loaded;const auto before_reads=reads;const auto before_em=EvtMgr.readEm[0];
        const auto before_carriers=carrier_snapshot();const auto before_parents=parents;const auto before_bins=bins;
        std::array<u8,0x20000> before_data;std::memcpy(before_data.data(),arena,before_data.size());
        assert(epoch()==41);int out=1;
        assert(!EvtMgr.EvtReadMram(file_name,0,&out,0,0)&&!out&&alloc_calls==2&&!provider_calls&&!native_frees&&!release_calls);
#if RE4DC_EVD_ARAM_ALLOC_RETRY
        assert(!std::memcmp(&loaded,&before,sizeof(before))&&!std::memcmp(reads.data(),before_reads.data(),sizeof(reads)));
        assert(!std::memcmp(&EvtMgr.readEm[0],&before_em,sizeof(before_em)));
        assert(!std::memcmp(carriers,before_carriers.data(),sizeof(carriers))&&epoch()==41);
        assert(!std::memcmp(parents.data(),before_parents.data(),sizeof(parents))&&!std::memcmp(bins.data(),before_bins.data(),sizeof(bins)));
        assert(!std::memcmp(arena,before_data.data(),before_data.size()));
        allow_allocation=true;
        assert(EvtMgr.EvtReadMram(file_name,0,&out,0,0)&&u32(out)==u32(std::uintptr_t(arena)));
        assert(alloc_calls==3&&provider_calls==1&&loaded.m_condition==2&&loaded.m_err==0&&loaded.m_addr==arena);
        assert(carriers[0].state==CarrierMram&&carriers[0].mram==arena&&!epoch());
        assert(!std::memcmp(reads.data(),before_reads.data(),sizeof(reads)));
        assert(EvtMgr.EvtFree(file_name));
#if RE4DC_EVD_READ_RELEASE_REFS
        if(prior_count>1){
            assert(!native_frees&&allocation_active&&reads[0].Count==1&&loaded.m_addr==arena);
            assert(EvtMgr.EvtFree(file_name));
        }
        assert(native_frees==1&&!allocation_active&&!EvtMgr.ReadTbl.ChkDat(file_name));
#else
        assert(native_frees==1&&!allocation_active);
        if(prior_count==1)assert(!EvtMgr.ReadTbl.ChkDat(file_name));
        else assert(reads[0].Count==1); // Existing successful shared-release contract remains separate.
#endif
#else
        assert(loaded.m_condition==0&&!loaded.m_addr&&!carriers[0].state);
        assert(prior_count==1?!EvtMgr.ReadTbl.ChkDat(file_name):reads[0].Count==1);
#endif
    }
    // Registration releases are not native reader leases. Non-final logical
    // releases preserve even a currently borrowed carrier; final release still
    // executes the actual reader refusal and must be retried after unbinding.
#if RE4DC_EVD_READ_RELEASE_REFS
    for(unsigned count:{2U,3U,32767U}){
        prepare();++cases;reads[0].Count=count;allow_allocation=true;int out=0;
        assert(EvtMgr.EvtReadMram(file_name,0,&out,0,0)&&loaded.m_addr==arena);
        assert(re4dc_cabin_carrier_event(&pool[1],arena,file_name));
        const auto before=loaded;const auto before_carriers=carrier_snapshot();const auto before_em=EvtMgr.readEm[0];
        auto expected_reads=reads;--expected_reads[0].Count;
        assert(EvtMgr.EvtFree(file_name)&&!native_frees&&allocation_active);
        assert(!std::memcmp(&loaded,&before,sizeof(before))&&!std::memcmp(carriers,before_carriers.data(),sizeof(carriers)));
        assert(!std::memcmp(reads.data(),expected_reads.data(),sizeof(reads))&&!std::memcmp(&EvtMgr.readEm[0],&before_em,sizeof(before_em)));
        while(reads[0].Count>1)assert(EvtMgr.EvtFree(file_name));
        const auto final_reads=reads;
        assert(!EvtMgr.EvtFree(file_name)&&!native_frees&&allocation_active);
        assert(!std::memcmp(reads.data(),final_reads.data(),sizeof(reads))&&!std::memcmp(&loaded,&before,sizeof(before)));
        assert(!std::memcmp(carriers,before_carriers.data(),sizeof(carriers)));
        re4dc_cabin_carrier_event_deleted(&pool[1]);
        assert(!carriers[0].event&&!carriers[0].readers);
        assert(EvtMgr.EvtFree(file_name)&&native_frees==1&&!allocation_active&&!EvtMgr.ReadTbl.ChkDat(file_name));
    }
#endif
    // Each query is observational, including malformed/refused contexts.
    for(unsigned refusal=0;refusal<26;++refusal){
        prepare();++cases;
        switch(refusal){
        case 0:carrier_fault=true;break;case 1:carrier_event_readers=1;break;case 2:carrier_dma_scope=1;break;
        case 3:carriers[0].generation=0;break;case 4:carriers[0].generation=0x80000000u;break;
        case 5:carriers[0].state=CarrierPreparing;break;case 6:carriers[0].state=CarrierReady;break;
        case 7:carriers[0].role=1;break;case 8:carriers[0].phase=1;break;
        case 9:carriers[0].backing=arena;break;case 10:carriers[0].mram=arena;break;
        case 11:carriers[0].module=arena;break;case 12:carriers[0].event=&pool[1];break;
        case 13:carriers[0].readers=1;break;case 14:carriers[0].releasing=true;break;
        case 15:carriers[0].heap=4;break;case 16:carriers[0].backing_heap=4;break;
        case 17:loaded.m_size-=32;break;case 18:loaded.m_name[0]='x';break;
        case 19:loaded.m_condition=2;break;case 20:loaded.m_be_flag|=2;break;
        case 21:carrier_dma[0].state=1;carrier_dma[0].owner=0;break;
        case 22:carriers[0].logical+=32;break;case 23:carriers[0].bytes-=32;break;
        case 24:carriers[0].generation=42;break;case 25:carrier_epoch=0;break;
        }
        const auto before=loaded;const auto before_carriers=carrier_snapshot();
        std::array<CabinCarrierDma,16> before_dma;std::memcpy(before_dma.data(),carrier_dma,sizeof(carrier_dma));
        const unsigned before_global[]={carrier_epoch,carrier_event_readers,carrier_dma_scope,carrier_dma_epoch};const bool before_fault=carrier_fault;
        assert(!epoch());
        assert(!std::memcmp(&loaded,&before,sizeof(before))&&!std::memcmp(carriers,before_carriers.data(),sizeof(carriers)));
        assert(!std::memcmp(carrier_dma,before_dma.data(),sizeof(carrier_dma))&&carrier_fault==before_fault);
        assert(carrier_epoch==before_global[0]&&carrier_event_readers==before_global[1]&&carrier_dma_scope==before_global[2]&&carrier_dma_epoch==before_global[3]);
        assert(!provider_calls&&!alloc_calls&&!native_frees);
    }
    prepare();++cases;assert(!re4dc_cabin_carrier_preload_epoch(nullptr,0x1000,27456));
    assert(!re4dc_cabin_carrier_preload_epoch(&loaded,0,27456)&&!re4dc_cabin_carrier_preload_epoch(&loaded,0x1000,0));
#if RE4DC_EVD_ARAM_ALLOC_RETRY
    // Adversarial changes at the allocation boundary lose the receipt. Preserve
    // the current owner instead of restoring or clearing its newer state.
    for(unsigned change=1;change<=9;++change){
        prepare();++cases;mutation=change;int out=1;
        assert(!EvtMgr.EvtReadMram(file_name,0,&out,0,0)&&!out&&alloc_calls==2);
        assert(!std::memcmp(&loaded,&after_mutation_unit,sizeof(loaded)));
        assert(!std::memcmp(reads.data(),after_mutation_reads.data(),sizeof(reads)));
        assert(!std::memcmp(&EvtMgr.readEm[0],&after_mutation_em,sizeof(after_mutation_em)));
        assert(!std::memcmp(carriers,after_mutation_carriers.data(),sizeof(carriers))&&!std::memcmp(carrier_dma,after_mutation_dma.data(),sizeof(carrier_dma)));
        assert(!native_frees&&!provider_calls&&!release_calls);
    }
#endif
    // No accepted epoch retains the old path, including its known caller gap.
    prepare();++cases;carriers[0]={};int out=1;
    assert(!EvtMgr.EvtReadMram(file_name,0,&out,0,0)&&!EvtMgr.ReadTbl.ChkDat(file_name)&&loaded.m_condition==0);
    // The real carrier clear predicate still refuses an accepted reader.
    prepare();++cases;carriers[0].readers=1;
    const auto refused=loaded;const auto refused_carrier=carrier_snapshot();
    assert(!loaded.setClear());
    assert(!std::memcmp(&loaded,&refused,sizeof(refused))&&!std::memcmp(carriers,refused_carrier.data(),sizeof(carriers)));
    assert(!EvtMgr.EvtReadMram(file_name,0,&out,0,0)&&!EvtMgr.ReadTbl.ChkDat(file_name));
    assert(loaded.m_addr==reinterpret_cast<void*>(0x1000)&&loaded.m_condition==4&&carriers[0].readers==1);
    std::cout<<"CABIN_ARAM_ALLOC_RETRY_CASES="<<cases<<" enabled="<<RE4DC_EVD_ARAM_ALLOC_RETRY<<" PASS\n";
    assert(mprotect(arena,0x20000,PROT_READ|PROT_WRITE)==0);munmap(arena,0x20000);
}
