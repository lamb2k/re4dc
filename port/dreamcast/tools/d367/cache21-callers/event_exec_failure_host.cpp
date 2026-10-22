#define RE4DC_EXEC_REAL_SCENARIO 1
#define RE4DC_EXEC_REAL_TRANSPORT 1
#include "event_start_rollback_host.cpp"

char* EventMgr::NameChange(char* name){return name;} // Synthetic costume0 input.
static bool add_read_ref_on_create;
static void exec_create_boundary(){
    if(add_read_ref_on_create){
        add_read_ref_on_create=false;
        assert(EvtMgr.ReadTbl.SetDat(file_name,&loaded,0,nullptr,2,nullptr));
    }
}
static void reset_case(bool prior,bool aram,unsigned nested,bool seeded){
    setup();SceSys={};host_task={};host_player={};start_calls=end_calls=camera_calls=0;
    transport_calls=0;transport_refuse=false;cabin_clear_refuse=false;clear_refusals=0;
    transport_other_flags=false;swap_pushes=swap_pops=swap_calls=0;
    add_read_ref_on_create=false;
    loaded.m_condition=aram?4:2;
    loaded.m_addr=loaded.m_malloc_addr=aram?arena+0x10000:arena;
    EvtMgr.readEm[0]={0,0,{0x55,0xaa}};
    if(!prior)assert(EvtMgr.DelRead(file_name));
    if(nested)SceEventStart(0);
    global.Status_flg[2]=seeded?0x49090000:0x49000000;
    global.System_flg|=seeded?0x100400:0x100000;
    start_calls=end_calls=camera_calls=0;
}
static void verify_owned_flags(u32 status,u32 system){
    assert(global.Status_flg[2]==status);
    assert((global.System_flg&0x400)==(system&0x400));
    assert(global.System_flg&0x100000);
}
int main(){
    std::cout<<std::unitbuf;
    arena=static_cast<unsigned char*>(mmap(reinterpret_cast<void*>(0x90000000),0x20000,
        PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS|MAP_FIXED_NOREPLACE,-1,0));
    assert(arena==reinterpret_cast<void*>(0x90000000));
    unsigned cases=0;
    for(u32 flags:{0U,4U,0x10U,0x20U,0x80U,0x100U,0x200U,2U,0x40U})
    for(bool prior:{false,true})for(bool aram:{false,true})for(unsigned nested:{0U,1U})for(bool seeded:{false,true}){
        reset_case(prior,aram,nested,seeded);++cases;
        const auto before_reads=reads;const auto before_em=EvtMgr.readEm[0];
        const u32 before_status=global.Status_flg[2],before_system=global.System_flg;
        const int result=EvtMgr.EvtReadExec(file_name,0,flags);
        assert(start_calls==1&&transport_calls==1&&!init_calls&&pool_logs==1);
#if RE4DC_EVD_EXEC_FAILURE_CLEANUP
        assert(result==0&&end_calls==1&&SceSys.event_start_cnt==nested&&sleep_calls==0);
        verify_owned_flags(before_status,before_system);
        assert(release_calls==unsigned(!prior));
        if(prior){
            assert(!std::memcmp(reads.data(),before_reads.data(),sizeof(reads)));
            assert(!std::memcmp(&EvtMgr.readEm[0],&before_em,sizeof(before_em)));
            assert(loaded.m_addr==arena&&loaded.m_condition==2);
        }else assert(!EvtMgr.ReadTbl.ChkDat(file_name)&&!loaded.m_addr);
        assert(camera_calls==unsigned(!nested&&!(flags&0x80)));
#else
        assert(result==1);
        if(flags&(2|0x40))assert(!end_calls&&!release_calls&&SceSys.event_start_cnt==nested+1);
        else assert(end_calls==1&&release_calls==1&&SceSys.event_start_cnt==nested);
#endif
    }
#if RE4DC_EVD_EXEC_FAILURE_CLEANUP
    reset_case(true,false,1,false);++cases;transport_other_flags=true;
    const u32 concurrent_status=global.Status_flg[2],concurrent_system=global.System_flg;
    assert(!EvtMgr.EvtReadExec(file_name,0,0));
    verify_owned_flags(concurrent_status|0x20,concurrent_system);
    assert(global.System_flg&0x4000000);
    // A prior running name must never delay the failed new start.
    reset_case(true,false,1,true);++cases;
    std::strcpy(EvtMgr.NowExeEvtName,"occupied1");
    assert(!EvtMgr.EvtReadExec(file_name,0,4)&&!sleep_calls&&pool[1].isAlive());
    // Prior reference counts and metadata are opaque owner state, not a lease
    // the failed work may release or normalize.
    reset_case(true,true,1,true);++cases;
    assert(EvtMgr.ReadTbl.SetDat(file_name,&loaded,0,nullptr,2,nullptr));
    EvtMgr.readEm[0]={7,0,{0x32,0x76}};
    const auto prior_reads=reads;const auto prior_em=EvtMgr.readEm[0];
    assert(!EvtMgr.EvtReadExec(file_name,0,0x42));
    assert(!std::memcmp(reads.data(),prior_reads.data(),sizeof(reads)));
    assert(!std::memcmp(&EvtMgr.readEm[0],&prior_em,sizeof(prior_em))&&!release_calls);
    // Real source retry uses the retained read and an available work slot.
    pool[0].be_flag=0;
    int address=0;assert(EvtMgr.EvtReadMram(file_name,0,&address,0,0));
    assert(EvtMgr.SetEvt(reinterpret_cast<void*>(u32(address)),static_cast<u32*>(nullptr)));
    assert(init_calls==1&&reads[0].Count==2&&pool[0].pData==reinterpret_cast<EvtHeader*>(arena));
    // Fresh registration can still be borrowed: a live event or published
    // parent/bin range must retain its backing after failed new creation.
    for(unsigned borrower:{0U,1U,2U,3U}){
        reset_case(false,false,0,false);++cases;
        if(borrower==0)pool[1].pData=reinterpret_cast<EvtHeader*>(arena+128);
        if(borrower==1)assert(EvtMgr.EvdTbl.SetDat("borrowed",arena+128,8,nullptr,2,nullptr));
        if(borrower==2)assert(EvtMgr.SetBin(const_cast<char*>("borrowed.bin"),arena+128,nullptr,2));
        if(borrower==3)add_read_ref_on_create=true; // Injected transfer at create boundary.
        assert(!EvtMgr.EvtReadExec(file_name,0,2)&&!release_calls&&loaded.m_addr==arena);
        assert(reads[0].Count==(borrower==3?2:1)&&EvtMgr.ReadTbl.ChkDat(file_name));
    }
#if RE4DC_CABIN_SOURCE
    reset_case(false,false,1,true);++cases;cabin_clear_refuse=true;
    const u32 refusal_status=global.Status_flg[2],refusal_system=global.System_flg;
    assert(!EvtMgr.EvtReadExec(file_name,0,0x42)&&!release_calls&&clear_refusals==1);
    assert(EvtMgr.ReadTbl.ChkDat(file_name)&&reads[0].Count==1&&loaded.m_addr==arena);
    assert(end_calls==1&&SceSys.event_start_cnt==1);verify_owned_flags(refusal_status,refusal_system);
    cabin_clear_refuse=false;assert(EvtMgr.EvtFree(file_name)&&release_calls==1&&!EvtMgr.ReadTbl.ChkDat(file_name));
#endif
#endif
    // Negative scope: em!=0 still follows the existing successful keep return
    // after a failed start, retaining its exchanged read. No reversal is claimed.
    reset_case(true,true,0,false);++cases;
    exchange_module={arena+0x18000,4096};event_at(static_cast<u8*>(exchange_module.pArc));
    assert(EvtMgr.EvtReadExec(file_name,1,2)==1);
    assert(EvtMgr.readEm[0].em==1&&EvtMgr.readEm[0].swapped==1&&swap_pushes==1&&swap_calls==1&&!swap_pops);
    assert(!release_calls&&EvtMgr.ReadTbl.ChkDat(file_name)&&start_calls==1&&!end_calls);
    // Negative scope: EvtReadMram's internal destructive load-failure cleanup
    // precedes the repaired SetEvt branch and remains a separate known gap.
    reset_case(true,true,0,false);++cases;transport_refuse=true;
    assert(!EvtMgr.EvtReadExec(file_name,0,2)&&!EvtMgr.ReadTbl.ChkDat(file_name));
    assert(start_calls==1&&end_calls==1&&release_calls==1);
    std::cout<<"EVENT_EXEC_FAILURE_CASES="<<cases<<" cleanup="<<RE4DC_EVD_EXEC_FAILURE_CLEANUP<<" cabin="<<RE4DC_CABIN_SOURCE<<" PASS\n";
    assert(mprotect(arena,0x20000,PROT_READ|PROT_WRITE)==0);munmap(arena,0x20000);
}
