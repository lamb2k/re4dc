// Actual frozen texpack_index.inc with a bounded reader over the original sorted index.
#include <algorithm>
#include <cassert>
#include <cstdarg>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <iterator>
#include <vector>
using mutex_t=int;
#define MUTEX_INITIALIZER 0
static unsigned locks,logs;
void mutex_lock(mutex_t*){++locks;}
void mutex_unlock(mutex_t*){assert(locks);--locks;}
void re4dc_log(const char*,...){++logs;}
struct Key{unsigned crc,fnv;bool operator==(const Key& x)const{return crc==x.crc&&fnv==x.fnv;}};
static std::vector<unsigned char> prefix;
static unsigned long long virtual_size;
static unsigned sector_reads[64],header_reads;
static bool armed;
static unsigned affected_bits[2]={3,0};
static bool affected(unsigned s){return s<64&&(affected_bits[s>>5]&(1U<<(s&31)));}
static unsigned fault; // 1 I/O error, 2 changed first key, 3 changed non-first row/CRC, 4 mixed I/O/CRC.
namespace re4dc::texture{
enum class RangeRead{ok,absent,io_error,short_file};
RangeRead read_file_range(const char*,std::uint32_t off,void* dst,std::uint32_t n,unsigned long long* total){
 if(total)*total=virtual_size;
 if(off==0)++header_reads;else{assert(off%2048==0&&off/2048<=64);++sector_reads[off/2048-1];}
 if((unsigned long long)off+n>prefix.size())return RangeRead::short_file;
 unsigned s=off/2048-1;
 if(armed&&off&&affected(s)&&((fault==1)||(fault==4&&s==0)))return RangeRead::io_error;
 std::memcpy(dst,prefix.data()+off,n);
 if(armed&&off&&affected(s)){
  if(fault==2)((unsigned char*)dst)[0]^=0x40; // first-key receipt rejects in both arms.
  if(fault==3||(fault==4&&s==1))((unsigned char*)dst)[16*7+12]^=1; // preserve first key and requested row.
 }
 return RangeRead::ok;
}
}
namespace{
#if RE4DC_TEX_PAYLOAD_RETRY
#include "texpack_payload_retry.inc"
#endif
#include "texpack_index.inc"
}
static unsigned word_at(unsigned o){return texpack::word(prefix.data()+o);}
static Key key(unsigned s){return {word_at(2048*(s+1)),word_at(2048*(s+1)+4)};}
static unsigned checks;
#define CHECK(x) do{++checks;if(!(x)){std::fprintf(stderr,"FAIL %u: %s\n",__LINE__,#x);return false;}}while(0)
static bool lookup(unsigned s,unsigned now,texpack::Result expected){
 const unsigned before=sector_reads[s]; unsigned off=~0U,size=~0U;
#if RE4DC_TEX_PAYLOAD_RETRY
 unsigned member=~0U,epoch=~0U;
 auto r=texpack::find(key(s),off,size,now,&member,&epoch);
 CHECK(r==expected);
 if(r==texpack::kError)CHECK(member==~0U&&epoch==~0U);
 else if(r==texpack::kFound)CHECK(member==128*s&&epoch!=0);
#else
 auto r=texpack::find(key(s),off,size,now);CHECK(r==expected);
#endif
 CHECK(locks==0);
 if(r==texpack::kError){CHECK(texpack::cached!=s);if(sector_reads[s]>before)CHECK(texpack::cached==~0U);CHECK(off==~0U&&size==~0U);}
 if(r==texpack::kFound)CHECK(off==word_at(2048*(s+1)+8)&&size==word_at(2048*(s+1)+12));
 return true;
}
static bool prepare(unsigned f,unsigned now=1000){
 armed=false;fault=f;affected_bits[0]=3;affected_bits[1]=0;texpack::state=texpack::kUntried;texpack::cached=~0U;
 texpack::count=texpack::data_offset=texpack::sectors=texpack::hits=texpack::misses=texpack::errors=0;
 texpack::attempts=texpack::streak=texpack::room_gen=texpack::attempt_gen=texpack::retry_at=0;
 texpack::bad_sector=~0U;texpack::bad_until=0;texpack::pack_bytes=0;
#if RE4DC_TEX_PAYLOAD_RETRY
 texpack::payload_epoch=1;texpack::payload_epoch_exhausted=false;texpack_payload_retry::reset();
#endif
 CHECK(lookup(2,now,texpack::kFound));
 CHECK(texpack::count==word_at(12)&&texpack::state==texpack::kReady&&texpack::cached==2);
 std::memset(sector_reads,0,sizeof(sector_reads));header_reads=logs=0;armed=true;return true;
}
static void emit(const char* name,unsigned f){
 unsigned all=header_reads;for(unsigned n:sector_reads)all+=n;
 std::printf("{\"case\":\"%s\",\"fault\":%u,\"reads_A\":%u,\"reads_B\":%u,\"reads_healthy\":%u,\"all_reads\":%u,\"error_logs\":%u,\"bad_sector\":%u}\n",name,f,sector_reads[0],sector_reads[1],sector_reads[2],all,logs,texpack::bad_sector);
}
static bool scenarios(unsigned f){
 const auto err=texpack::kError,found=texpack::kFound;
 CHECK(prepare(f));CHECK(lookup(0,1000,err));CHECK(lookup(1,1000,err));CHECK(lookup(0,1000,err));
 CHECK(sector_reads[0]==(RE4DC_TEX_PAYLOAD_RETRY?1U:2U)&&sector_reads[1]==1&&logs==(RE4DC_TEX_PAYLOAD_RETRY?2U:3U));emit("minimal_ABA_same_frame",f);
 CHECK(prepare(f));
 for(unsigned s:{0U,2U,1U,2U,0U,2U})CHECK(lookup(s,1000,s==2?found:err));
 CHECK(sector_reads[0]==(RE4DC_TEX_PAYLOAD_RETRY?1U:2U)&&sector_reads[1]==1&&sector_reads[2]==(RE4DC_TEX_PAYLOAD_RETRY?2U:3U)&&logs==(RE4DC_TEX_PAYLOAD_RETRY?2U:3U));emit("minimal_AHBHAH_same_frame",f);
 CHECK(prepare(f));
 // Only A fails/gets used: the most recent failure's existing control works.
 for(unsigned i=0;i<30;++i){CHECK(lookup(0,1000+i,err));CHECK(lookup(2,1000+i,found));}
 CHECK(sector_reads[0]==1&&sector_reads[1]==0&&sector_reads[2]==1&&logs==1);emit("one_failed_sector_30_frames",f);
 for(unsigned burst:{0U,1U}){
  CHECK(prepare(f));
  for(unsigned i=0;i<30;++i){unsigned now=1000+(burst?0:i);CHECK(lookup(0,now,err));CHECK(lookup(1,now,err));CHECK(lookup(2,now,found));}
  CHECK(sector_reads[0]==(RE4DC_TEX_PAYLOAD_RETRY?1U:30U)&&sector_reads[1]==(RE4DC_TEX_PAYLOAD_RETRY?1U:30U)&&sector_reads[2]==(RE4DC_TEX_PAYLOAD_RETRY?1U:30U)&&logs==(RE4DC_TEX_PAYLOAD_RETRY?2U:60U));
  emit(burst?"two_failed_sectors_30_same_frame_cycles":"two_failed_sectors_30_frames",f);
 }
 CHECK(prepare(f));CHECK(lookup(0,1000,err));CHECK(lookup(1,1000,err));CHECK(lookup(1,1001,err));
 CHECK(sector_reads[0]==1&&sector_reads[1]==1);
 CHECK(lookup(0,1001,err));CHECK(lookup(1,1001,err));CHECK(sector_reads[0]==(RE4DC_TEX_PAYLOAD_RETRY?1U:2U)&&sector_reads[1]==(RE4DC_TEX_PAYLOAD_RETRY?1U:2U));emit("last_slot_replacement",f);
 CHECK(prepare(f));CHECK(lookup(0,1000,err));CHECK(lookup(0,1029,err));CHECK(sector_reads[0]==1);
 armed=false;CHECK(lookup(0,1030,found));CHECK(sector_reads[0]==2&&logs==1);emit("single_sector_retry_boundary_recovery",f);
 CHECK(prepare(f));CHECK(lookup(0,1000,err));CHECK(lookup(0,1001,err));texpack::room_loaded();armed=false;
 CHECK(lookup(0,1001,found));CHECK(sector_reads[0]==2&&logs==1);emit("room_reset_recovery",f);
 CHECK(prepare(f,0xfffffff0U));CHECK(lookup(0,0xfffffff0U,err));CHECK(lookup(0,13,err));CHECK(sector_reads[0]==1);
 armed=false;CHECK(lookup(0,14,found));CHECK(sector_reads[0]==2&&logs==1);emit("single_sector_wrap_recovery",f);
 return true;
}

static void put(unsigned at,unsigned x){for(unsigned i=0;i<4;++i)prefix.at(at+i)=x>>(8*i);}
static void make_max_index(){
 prefix.assign(65*2048,0);virtual_size=prefix.size()+8192ULL*2048;
 std::memcpy(prefix.data(),"RE4PAK1",8);put(8,1);put(12,8192);put(16,2048);put(20,prefix.size());
 for(unsigned i=0;i<8192;++i){unsigned p=2048+16*i;put(p,i+1);put(p+4,0x100+i);put(p+8,prefix.size()+2048*i);put(p+12,100);}
 put(24,~texpack::crc_update(0xffffffffU,prefix.data()+2048,64*2048));
}
static bool cap_boundary(){
 make_max_index();CHECK(prepare(1));armed=false;unsigned off=0,size=0;
#if RE4DC_TEX_PAYLOAD_RETRY
 unsigned member=~0U,epoch=~0U;
 CHECK(texpack::find({8192,0x100+8191},off,size,1000,&member,&epoch)==texpack::kFound&&member==8191&&epoch);
 CHECK(texpack::payload_blocked(8192,1000,epoch));
#else
 CHECK(texpack::find({8192,0x100+8191},off,size,1000)==texpack::kFound);
#endif
 CHECK(off==prefix.size()+8191U*2048&&size==100&&texpack::sectors==64);
 put(12,8193);texpack::state=texpack::kUntried;texpack::cached=~0U;
 unsigned before=header_reads;CHECK(texpack::find({1,0x100},off,size,1001)==texpack::kNotInPack&&texpack::state==texpack::kInvalid&&header_reads==before+1);
 std::printf("{\"case\":\"8192_max_ordinal_8193_header_refusal\",\"guard\":%u}\n",unsigned(RE4DC_TEX_PAYLOAD_RETRY));return true;
}
#if RE4DC_TEX_PAYLOAD_RETRY
static unsigned reads_all(){unsigned n=header_reads;for(unsigned x:sector_reads)n+=x;return n;}
static bool new_policy(){
 make_max_index();CHECK(prepare(1));affected_bits[0]=affected_bits[1]=~0U;
 for(unsigned s=0;s<64;++s)CHECK(lookup(s,1000,texpack::kError));
 CHECK(texpack::index_bad_bits[0]==~0U&&texpack::index_bad_bits[1]==~0U&&reads_all()==64);
 for(unsigned s=0;s<64;++s){CHECK(texpack::index_bad_until[s]==1030);CHECK(lookup(s,1029,texpack::kError));CHECK(sector_reads[s]==1);}
 armed=false;
 for(unsigned s=0;s<64;++s){CHECK(lookup(s,1030,texpack::kFound));CHECK(sector_reads[s]==2);CHECK(!(texpack::index_bad_bits[s>>5]&(1U<<(s&31))));}
 CHECK(texpack::index_bad_bits[0]==0&&texpack::index_bad_bits[1]==0&&reads_all()==128&&logs==64);
 std::printf("{\"case\":\"all64_failure_hold_deadline_recovery\",\"failed_reads\":64,\"held_extra_reads\":0,\"recovery_reads\":64}\n");
 CHECK(prepare(1));affected_bits[0]=0x80000000U;affected_bits[1]=1;
 CHECK(lookup(31,1000,texpack::kError));CHECK(lookup(32,1010,texpack::kError));
 CHECK(texpack::index_bad_bits[0]==0x80000000U&&texpack::index_bad_bits[1]==1);
 CHECK(lookup(31,1029,texpack::kError));CHECK(lookup(32,1030,texpack::kError));armed=false;
 CHECK(lookup(31,1030,texpack::kFound));CHECK(texpack::index_bad_bits[0]==0&&texpack::index_bad_bits[1]==1);
 CHECK(lookup(32,1039,texpack::kError));CHECK(lookup(32,1040,texpack::kFound));CHECK(texpack::index_bad_bits[1]==0);
 CHECK(sector_reads[31]==2&&sector_reads[32]==2&&logs==2);
 std::printf("{\"case\":\"31_32_independent_staggered_deadlines\",\"reads31\":2,\"reads32\":2}\n");
 CHECK(prepare(1,0xfffffff0U));affected_bits[0]=0x80000000U;affected_bits[1]=1;
 CHECK(lookup(31,0xfffffff0U,texpack::kError));CHECK(lookup(32,0xfffffff8U,texpack::kError));
 CHECK(texpack::index_bad_until[31]==14&&texpack::index_bad_until[32]==22);
 CHECK(lookup(31,13,texpack::kError));CHECK(lookup(32,14,texpack::kError));armed=false;
 CHECK(lookup(31,14,texpack::kFound));CHECK(texpack::index_bad_bits[0]==0&&texpack::index_bad_bits[1]==1);
 CHECK(lookup(32,21,texpack::kError));CHECK(lookup(32,22,texpack::kFound));CHECK(texpack::index_bad_bits[1]==0);
 std::printf("{\"case\":\"31_32_staggered_UINT_wrap\",\"reads31\":%u,\"reads32\":%u}\n",sector_reads[31],sector_reads[32]);
 CHECK(prepare(1));affected_bits[0]=affected_bits[1]=~0U;
 for(unsigned s=0;s<64;++s)CHECK(lookup(s,1000,texpack::kError));unsigned epoch=texpack::payload_epoch;
 texpack::room_loaded();CHECK(texpack::payload_epoch!=epoch&&texpack::index_bad_bits[0]==0&&texpack::index_bad_bits[1]==0);
 // Deadlines deliberately remain stored; validity bits must make them irrelevant.
 for(unsigned s=0;s<64;++s)CHECK(texpack::index_bad_until[s]==1030);
 armed=false;for(unsigned s=0;s<64;++s){CHECK(lookup(s,1001,texpack::kFound));CHECK(sector_reads[s]==2);}
 std::printf("{\"case\":\"room_reset_all64_stale_deadlines_ignored\",\"immediate_recoveries\":64}\n");
 CHECK(prepare(1));affected_bits[0]=affected_bits[1]=~0U;
 for(unsigned s=0;s<64;++s)CHECK(lookup(s,1000,texpack::kError));epoch=texpack::payload_epoch;
 armed=false;texpack::state=texpack::kUntried;texpack::cached=~0U;
 CHECK(lookup(0,1001,texpack::kFound));CHECK(texpack::payload_epoch!=epoch&&texpack::index_bad_bits[0]==0&&texpack::index_bad_bits[1]==0);
 std::printf("{\"case\":\"validated_new_ready_all64_clear\",\"old_failed_sectors\":64}\n");
 CHECK(prepare(1));affected_bits[0]=~(1U<<2);affected_bits[1]=~0U;
 for(unsigned s=0;s<64;++s)if(s!=2){CHECK(lookup(s,1000,texpack::kError));CHECK(lookup(2,1000,texpack::kFound));}
 CHECK(sector_reads[2]==63&&reads_all()==126&&!(texpack::index_bad_bits[0]&(1U<<2)));
 for(unsigned s=0;s<64;++s)if(s!=2){CHECK(lookup(s,1001,texpack::kError));CHECK(lookup(2,1001,texpack::kFound));}
 CHECK(sector_reads[2]==63&&reads_all()==126&&logs==63);
 std::printf("{\"case\":\"healthy_sector_among63_failed\",\"first_failed_reads\":63,\"first_healthy_reads\":63,\"held_extra_reads\":0}\n");
 return true;
}
#endif

int main(int argc,char**argv){
 assert(argc==3);std::ifstream in(argv[1],std::ios::binary);assert(in);prefix.assign(std::istreambuf_iterator<char>(in),{});virtual_size=std::stoull(argv[2]);
 assert(prefix.size()>=8192&&word_at(12)>=384);
 if(!scenarios(1)||!scenarios(2))return 1;
#if RE4DC_TEX_PAYLOAD_RETRY
 if(!scenarios(3)||!scenarios(4))return 1;
#else
 if(!prepare(3))return 1;
 for(unsigned i=0;i<30;++i)for(unsigned s:{0U,1U,2U})if(!lookup(s,1000+i,texpack::kFound))return 1;
 if(sector_reads[0]!=30||sector_reads[1]!=30||sector_reads[2]!=30||logs)return 1;
 emit("CRC_only_mutation_not_checked_OFF",3);
#endif
#if RE4DC_TEX_PAYLOAD_RETRY
 if(!new_policy())return 1;
#endif
 if(!cap_boundary())return 1;
 std::printf("{\"checks\":%u,\"guard\":%u}\n",checks,unsigned(RE4DC_TEX_PAYLOAD_RETRY));
}
