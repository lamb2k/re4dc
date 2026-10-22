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
static unsigned fault; // 1 I/O error, 2 changed first key, 3 changed non-first row/CRC, 4 mixed I/O/CRC.
namespace re4dc::texture{
enum class RangeRead{ok,absent,io_error,short_file};
RangeRead read_file_range(const char*,std::uint32_t off,void* dst,std::uint32_t n,unsigned long long* total){
 if(total)*total=virtual_size;
 if(off==0)++header_reads;else{assert(off%2048==0&&off/2048<=64);++sector_reads[off/2048-1];}
 if((unsigned long long)off+n>prefix.size())return RangeRead::short_file;
 unsigned s=off/2048-1;
 if(armed&&off&&s<2&&((fault==1)||(fault==4&&s==0)))return RangeRead::io_error;
 std::memcpy(dst,prefix.data()+off,n);
 if(armed&&off&&s<2){
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
 armed=false;fault=f;texpack::state=texpack::kUntried;texpack::cached=~0U;
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
 CHECK(sector_reads[0]==2&&sector_reads[1]==1&&logs==3);emit("minimal_ABA_same_frame",f);
 CHECK(prepare(f));
 for(unsigned s:{0U,2U,1U,2U,0U,2U})CHECK(lookup(s,1000,s==2?found:err));
 CHECK(sector_reads[0]==2&&sector_reads[1]==1&&sector_reads[2]==3&&logs==3);emit("minimal_AHBHAH_same_frame",f);
 CHECK(prepare(f));
 // Only A fails/gets used: the most recent failure's existing control works.
 for(unsigned i=0;i<30;++i){CHECK(lookup(0,1000+i,err));CHECK(lookup(2,1000+i,found));}
 CHECK(sector_reads[0]==1&&sector_reads[1]==0&&sector_reads[2]==1&&logs==1);emit("one_failed_sector_30_frames",f);
 for(unsigned burst:{0U,1U}){
  CHECK(prepare(f));
  for(unsigned i=0;i<30;++i){unsigned now=1000+(burst?0:i);CHECK(lookup(0,now,err));CHECK(lookup(1,now,err));CHECK(lookup(2,now,found));}
  CHECK(sector_reads[0]==30&&sector_reads[1]==30&&sector_reads[2]==30&&logs==60);
  emit(burst?"two_failed_sectors_30_same_frame_cycles":"two_failed_sectors_30_frames",f);
 }
 CHECK(prepare(f));CHECK(lookup(0,1000,err));CHECK(lookup(1,1000,err));CHECK(lookup(1,1001,err));
 CHECK(sector_reads[0]==1&&sector_reads[1]==1);
 CHECK(lookup(0,1001,err));CHECK(lookup(1,1001,err));CHECK(sector_reads[0]==2&&sector_reads[1]==2);emit("last_slot_replacement",f);
 CHECK(prepare(f));CHECK(lookup(0,1000,err));CHECK(lookup(0,1029,err));CHECK(sector_reads[0]==1);
 armed=false;CHECK(lookup(0,1030,found));CHECK(sector_reads[0]==2&&logs==1);emit("single_sector_retry_boundary_recovery",f);
 CHECK(prepare(f));CHECK(lookup(0,1000,err));CHECK(lookup(0,1001,err));texpack::room_loaded();armed=false;
 CHECK(lookup(0,1001,found));CHECK(sector_reads[0]==2&&logs==1);emit("room_reset_recovery",f);
 CHECK(prepare(f,0xfffffff0U));CHECK(lookup(0,0xfffffff0U,err));CHECK(lookup(0,13,err));CHECK(sector_reads[0]==1);
 armed=false;CHECK(lookup(0,14,found));CHECK(sector_reads[0]==2&&logs==1);emit("single_sector_wrap_recovery",f);
 return true;
}
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
 std::printf("{\"checks\":%u,\"guard\":%u}\n",checks,unsigned(RE4DC_TEX_PAYLOAD_RETRY));
}
