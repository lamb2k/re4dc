// Independent semantic oracles for actual preload functions. Included after generated namespaces.
struct Pair { Snapshot off,on; };
static FakeFS off_fs,on_fs;
static unsigned checks;
#define CHECK(x) do{++checks;if(!(x)){std::fprintf(stderr,"FAIL %u: %s\n",__LINE__,#x);std::abort();}}while(0)
static std::vector<Rec> cores,real_rows;
static std::vector<unsigned char> file(std::vector<Rec>rows){std::vector<unsigned char>b(((rows.size()+31)/32)*512);if(!rows.empty())std::memcpy(b.data(),rows.data(),rows.size()*sizeof(Rec));return b;}
static Rec row(unsigned room,unsigned key,unsigned width=8,unsigned height=8){return{std::uint16_t(room),std::uint16_t(width),std::uint16_t(height),1,key,key*17+3};}
static void reset(std::vector<unsigned char>data){direct::reset();cached::reset();off_fs={};on_fs={};off_fs.data=on_fs.data=data;active_room=0x101;}
static Pair step(const char*name,unsigned n=0,unsigned resident=0,unsigned limit=416,unsigned budget=10000000,unsigned owner=0,bool seed=false){
 active_fs=&off_fs;auto a=direct::pass(n,resident,limit,budget,owner,seed);
 active_fs=&on_fs;auto b=cached::pass(n,resident,limit,budget,owner,seed);
 CHECK(a.n==b.n&&a.resident==b.resident&&a.bytes==b.bytes&&a.listed==b.listed&&a.picked==b.picked);
 std::printf("{\"case\":\"%s\",\"off_core\":%u,\"on_core\":%u,\"off_room_on\":%u,\"on_room_on\":%u,\"off_pinned\":%u,\"on_pinned\":%u,\"n\":%u,\"resident\":%u,\"off_reads\":%u,\"on_reads\":%u,\"cache_valid\":%u}\n",name,a.core,b.core,a.room_on,b.room_on,a.pinned,b.pinned,a.n,a.resident,a.reads,b.reads,b.cache_valid);
 return{a,b};
}
static void metadata(Pair p,unsigned off_core,bool off_on,unsigned fixed_core,bool fixed_on){
 CHECK(p.off.core==off_core&&p.off.room_on==off_on);
 CHECK(p.on.core==(EXPECT_FIXED?fixed_core:off_core)&&p.on.room_on==(EXPECT_FIXED?fixed_on:off_on));
}
int main(int argc,char**argv){
 CHECK(argc==2);std::ifstream input(argv[1],std::ios::binary);CHECK(bool(input));std::vector<unsigned char>data(std::istreambuf_iterator<char>(input),{});
 CHECK(data.size()%16==0);for(unsigned i=0;i<data.size();i+=16){Rec r;std::memcpy(&r,data.data()+i,16);if(r.width){real_rows.push_back(r);if(!r.room)cores.push_back(r);}}
 CHECK(cores.size()==6);core_rows=cores;
 reset(data);auto p=step("roomy_control");metadata(p,6,true,6,true);CHECK(p.off.pinned&&p.on.pinned);
 for(unsigned which=0;which<4;++which){reset(data);p=step(which==0?"full_n_equal_limit":which==1?"resident_equal_limit":which==2?"over_limit":"zero_limit",which==0?416:which==2?417:0,which==1?416:0,which==3?0:416);metadata(p,0,false,6,true);CHECK(!p.off.pinned&&p.on.pinned==bool(EXPECT_FIXED));CHECK(p.off.listed==0&&p.off.picked==0);}
 reset(data);p=step("six_cores_fill_before_own",410);metadata(p,6,false,6,true);CHECK(p.off.n==416&&p.off.picked==6);
 reset(data);p=step("six_resident_cores_fill_before_own",410,0,416,10000000,0,true);metadata(p,6,false,6,true);CHECK(p.off.n==410&&p.off.resident==6);
 reset(data);p=step("normal_owner_select_fills_all",0,0,416,10000000,416);metadata(p,0,false,6,true);CHECK(p.off.n==416);
 reset(data);p=step("normal_owner_select_leaves_six",0,0,416,10000000,410);metadata(p,6,false,6,true);CHECK(p.off.n==416);
 reset(data);metadata(step("prime_warm_cache"),6,true,6,true);p=step("warm_full_reclassifies_existing_cores",416);metadata(p,6,false,6,true);CHECK(p.on.reads==0&&p.off.reads>0);
 reset(data);p=step("byte_budget_zero_metadata_still_seen",0,0,416,0);metadata(p,6,true,6,true);CHECK(!p.off.n&&!p.on.n);
 reset(file(cores));metadata(step("no_own_room_control"),6,false,6,false);
 auto malformed=cores;malformed.push_back(row(0x101,123456,0,0));reset(file(malformed));metadata(step("malformed_own_row_retains_existing_semantics"),6,true,6,true);
 reset(file(malformed));metadata(step("full_malformed_own_classification",416),0,false,6,true);
 std::vector<Rec>cross;for(unsigned i=0;i<32;++i)cross.push_back(row(0x102,200000+i));cross.push_back(cores[0]);cross.push_back(cores[1]);cross.push_back(row(0x101,300000));reset(file(cross));metadata(step("crossblock_late_core_and_own",416),0,false,2,true);
 std::vector<Rec>cap;for(unsigned i=0;i<20;++i)cap.push_back(row(0,400000+i));cap.push_back(cap[0]);cap.push_back(row(0x101,500000));reset(file(cap));metadata(step("core_capacity16_and_duplicate",416),0,false,16,true);
 std::vector<Rec>late=cores;for(unsigned i=0;i<26;++i)late.push_back(row(0x102,600000+i));late.push_back(row(0x101,700000));reset(file(late));off_fs.fail_offset=on_fs.fail_offset=512;
 p=step("late_read_failure_before_first_own",416);metadata(p,0,false,6,false);CHECK(!p.on.cache_valid&&p.on.reads==2);
 off_fs.fail_offset=on_fs.fail_offset=~0U;p=step("late_failure_recovery",416);metadata(p,0,false,6,true);CHECK(p.on.cache_valid&&p.on.reads==3);
 reset(data);off_fs.fail_offset=on_fs.fail_offset=512;p=step("late_error_after_own_prefix_known",416);metadata(p,0,false,6,true);CHECK(!p.on.cache_valid);
 reset(data);off_fs.fail_offset=on_fs.fail_offset=0;p=step("first_read_failure_nothing_classified",416);metadata(p,0,false,0,false);CHECK(!p.on.cache_valid);
 auto partial=file(std::vector<Rec>(late.begin(),late.begin()+32));const Rec last=row(0x101,800000);auto old=partial.size();partial.resize(old+sizeof(last));std::memcpy(partial.data()+old,&last,sizeof(last));reset(partial);p=step("partial_tail_own_not_processed",416);metadata(p,0,false,6,false);CHECK(!p.on.cache_valid);
 auto overflow=cores;for(unsigned i=0;i<257;++i)overflow.push_back(row(0x101,900000+i));reset(file(overflow));p=step("cache_overflow_semantics_full_scan",416);metadata(p,0,false,6,true);CHECK(!p.on.cache_valid);p=step("overflow_retries_full_scan",416);metadata(p,0,false,6,true);CHECK(p.on.reads>0&&!p.on.cache_valid);
 std::printf("{\"checks\":%u,\"expect_fixed\":%u}\n",checks,unsigned(EXPECT_FIXED));
}
