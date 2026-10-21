// Actual pinned KOS read/cache/seek source is included unchanged below. Drive calls are mocks.
#include <algorithm>
#include <cassert>
#include <cerrno>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <cstddef>
using mutex_t=int;void mutex_lock(mutex_t*){}void mutex_unlock(mutex_t*){}
#define mutex_lock_scoped(p) ((void)0)
#define __is_aligned(p,n) ((reinterpret_cast<uintptr_t>(p)&((n)-1))==0)
constexpr int ERR_OK=0,ERR_DISC_CHG=-2,ERR_NO_DISC=-3;
using thd_cb_t=int(*)(size_t*);void thd_poll(thd_cb_t,size_t*,int){}
struct Req{unsigned kind,bytes,context;};Req requests[4096];unsigned nrequests,readbytes,remaining,request_context;
void counted(unsigned kind,unsigned n){requests[nrequests++]={kind,n,request_context};readbytes+=n;assert(nrequests<4096);}
int cdrom_read_sectors_ex(void* dst,uint32_t,size_t n,bool){counted(0,n*2048);std::memset(dst,0,n*2048);return 0;}
int cdrom_stream_start(int,int n,bool){remaining=n*2048;return 0;}
int cdrom_stream_stop(bool){remaining=0;return 0;}
int cdrom_stream_request(void* dst,size_t n,int){counted(1,n);std::memset(dst,0,n);remaining-=n;return 0;}
int cdrom_stream_progress(size_t* out){*out=remaining;return 0;}
int init_percd(){return 0;}
typedef struct {uint8_t* data;uint32_t sector;}cache_block_t;
constexpr unsigned NUM_CACHE_BLOCKS=16;
cache_block_t* icache[16];cache_block_t* dcache[16];mutex_t cache_mutex,fh_mutex,iso_mutex;
struct iso_fd_t{uint32_t first_extent;bool broken;uint32_t ptr,size;size_t stream_part;alignas(32)uint8_t stream_data[32];};
iso_fd_t* stream_fd;
static void iso_abort_stream(void);
#include "actual_iso.inc"
alignas(32)uint8_t bounce[16384+32],cache_bytes[16][2048],aligned[2048];cache_block_t blocks[16];
void reset(){stream_fd=nullptr;remaining=0;nrequests=readbytes=0;for(unsigned i=0;i<16;++i){blocks[i]={cache_bytes[i],~0U};dcache[i]=&blocks[i];icache[i]=&blocks[i];}}
void close_file(iso_fd_t& f){if(stream_fd==&f)iso_abort_stream();}
void read_chunks(iso_fd_t& f,unsigned n){while(n){unsigned chunk=std::min(n,16384U);assert(iso_read(&f,bounce+16,chunk)==int(chunk));n-=chunk;}}
void member(unsigned offset,unsigned payload_at,unsigned payload){request_context=0;iso_fd_t f{1,false,0,200000000,0,{}};assert(iso_seek(&f,offset,SEEK_SET)==offset);read_chunks(f,48);read_chunks(f,96);assert(iso_seek(&f,offset+payload_at,SEEK_SET)==offset+payload_at);read_chunks(f,payload);close_file(f);}
void index_sector(unsigned s){request_context=1;iso_fd_t f{1,false,0,200000000,0,{}};assert(iso_seek(&f,2048*(s+1),SEEK_SET)==2048*(s+1));assert(iso_read(&f,aligned,2048)==2048);close_file(f);}
struct Case{unsigned arm,restore,index_sector,offset,size,payload_at,payload;const char* key;};
#include "cases.inc"
int main(){unsigned totals[2][2]{};
 for(unsigned arm=0;arm<2;++arm){reset();unsigned cached=~0U;
  for(const auto& c:cases){if(c.arm!=arm)continue;if(c.restore&&totals[arm][0]==0){nrequests=readbytes=0;totals[arm][0]=1;}
   const unsigned r0=nrequests,b0=readbytes;
   if(c.index_sector!=cached){index_sector(c.index_sector);cached=c.index_sector;}
   member(c.offset,c.payload_at,c.payload);
   if(c.restore)printf("MEMBER arm=%u key=%s index=%u reads=%u bytes=%u size=%u payload=%u\n",arm,c.key,c.index_sector,nrequests-r0,readbytes-b0,c.size,c.payload);
  }
  unsigned headers=0,bulk=0,tails=0,index=0;
  for(unsigned i=0;i<nrequests;++i){const auto& q=requests[i];if(q.context)++index;else if(q.kind==0)++headers;else if(q.bytes==32)++tails;else ++bulk;}
  printf("REQUEST_CLASSES arm=%u member_header_sectors=%u member_bulk_streams=%u member_tail_streams=%u index_streams=%u\n",arm,headers,bulk,tails,index);
  totals[arm][0]=nrequests;totals[arm][1]=readbytes;printf("TOTAL arm=%u reads=%u bytes=%u\n",arm,nrequests,readbytes);
 }
 assert(totals[1][0]-totals[0][0]==102&&totals[1][1]-totals[0][1]==168032);
 printf("ACTUAL_ISO_REPLAY PASS delta_reads=%u delta_bytes=%u\n",totals[1][0]-totals[0][0],totals[1][1]-totals[0][1]);
}
