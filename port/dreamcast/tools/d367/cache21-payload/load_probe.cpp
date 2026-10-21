#include <algorithm>
#include <cstring>
#include <cstdio>
#include <cassert>
#include <cstdint>
#define RE4DC_TEX_PACK 1
#define RE4DC_TEX_RESIDENT 1
#define RE4DC_UI_VRAM 1
#define RE4DC_PROFILE_SCOPE(x)
#define RE4DC_PROFILE_COUNT(x,n)
#define RE4DC_TEXCHK_FAIL(k,w)
#define RE4DC_TEXCHK_BIND(e)
#define RE4DC_FX_EVICTED()
#define RE4DC_HOLD_EVICTED(e)
#define RE4DC_ENTRY_PINNED(e) false
#define RE4DC_CORE_PINNED(e) false
#define RE4DC_TEX_PATH(p,k) std::strcpy(p,"member")
#define RE4DC_TOUCH(e) ((e).frame=frame)
#define RE4DC_GAD_HIT(k)
#define re4dc_log(...) ((void)0)
using file_t=int;
constexpr int FILEHND_INVALID=-1,O_RDONLY=0;
int fs_open(const char*,int){return 1;} void fs_close(int){}
struct Key {unsigned crc,fnv;bool operator==(const Key& b)const{return crc==b.crc&&fnv==b.fnv;}};
namespace re4dc {namespace texture {constexpr unsigned kPayloadVq=1;}}
struct Re4dcUiImage {void* pixels;unsigned width,height,format;};
unsigned image_size(const Re4dcUiImage&){return 16;}
bool image_key(const Re4dcUiImage&,Key&){return false;}
unsigned calls,evictions,closes,frame,used,peak,reclaimed,vram_rejects,vram_retries,loads,pack_error_skips;
const char* injected="streamed texture upload read failed";
struct Package {
 const char* err=nullptr;
 struct H{unsigned texture_count=1,data_size=16;} h;
 struct T{unsigned payload=0,data_size=16,width=8,height=8;} tx;
 bool open_streamed_at(const char*,unsigned,unsigned){++calls;err=nullptr;if(injected&&!std::strcmp(injected,"streamed header read failed")){err=injected;return false;}return true;}
 bool open_streamed(const char*){++calls;return true;}
 const char* error()const{return err;}
 const H& header()const{return h;}
 bool upload(){if(injected){err=injected;return false;}return true;}
 bool release_payload(){return true;}
 unsigned vram_bytes()const{return 16;}
 unsigned metadata_bytes()const{return 16;}
 const T* textures()const{return &tx;}
 void close(){++closes;}
};
struct Entry {Package package;Key key{};unsigned frame=0;bool valid=false;} entries[4];
Key missing_keys[16]{};unsigned nmissing=0;
constexpr unsigned vram_budget=4096;
using pvr_ptr_t=void*; void* pvr_mem_malloc(unsigned){return (void*)1;} void pvr_mem_free(void*){}
unsigned pvr_mem_available(){return 8192;}
int re4dc_ui_heap_free(){return 4096;}
void close_entry(Entry& e){if(e.valid){++evictions;e.valid=false;used-=16;}e.package.close();}
namespace texpack {constexpr const char* kPath="pack";enum Result{kFound,kNotInPack,kError};Result selected=kFound;unsigned member=0;
 Result find(const Key&,unsigned& offset,unsigned& size,unsigned
#if RE4DC_TEX_PAYLOAD_RETRY
 ,unsigned* ordinal=nullptr
#endif
 ){offset=member*2048;size=200;
#if RE4DC_TEX_PAYLOAD_RETRY
 if(ordinal)*ordinal=member;
#endif
 return selected;}}
#if RE4DC_TEX_PAYLOAD_RETRY
#include "texpack_payload_retry.inc"
#endif
#include "actual_load.inc"
void refill(){for(unsigned i=0;i<4;++i){entries[i].valid=true;entries[i].key=Key{100+i,100};entries[i].frame=0;}used=64;}
int main(){Re4dcUiImage image{(void*)1,8,8,1};const Key bad{1,2};
 for(frame=0;frame<20;++frame){refill();assert(!load(image,false,&bad));}
#if RE4DC_TEX_PAYLOAD_RETRY
 assert(calls==1&&evictions==1);
#else
 assert(calls==20&&evictions==20);
#endif

#if RE4DC_TEX_PAYLOAD_RETRY
 unsigned first_calls=calls;frame=60;injected=nullptr;refill();assert(load(image,false,&bad));assert(calls==first_calls+1);assert(!texpack_payload_retry::blocked(0,60));
 // Resident hits return before any failed-member gate or package work.
 texpack_payload_retry::failed(0,60);assert(load(image,false,&bad));assert(calls==first_calls+1);
 // Healthy first use still opens after a storm of more than 32 exact failures.
 texpack_payload_retry::reset();for(unsigned i=0;i<4000;++i)texpack_payload_retry::failed(i,60);
 texpack::member=4000;const Key healthy{9,9};refill();assert(load(image,false,&healthy));assert(calls==first_calls+2);
 // Heap/refusal paths are not latched and existing capacity retry remains available.
 texpack_payload_retry::reset();texpack::member=0;injected="streamed metadata allocation failed";
 unsigned start=calls;for(frame=100;frame<110;++frame){refill();assert(!load(image,false,&bad));}assert(calls==start+10);
 // Packed header failures are spaced but no loose-key missing entry is created.
 texpack_payload_retry::reset();injected="streamed header read failed";start=calls;
 for(frame=120;frame<130;++frame){refill();assert(!load(image,false,&bad));}assert(calls==start+1&&nmissing==0);
 // Loose packages never consult or arm the packed-member retry maps.
 texpack::selected=texpack::kNotInPack;injected="streamed texture upload read failed";start=calls;
 for(frame=130;frame<140;++frame){refill();assert(!load(image,false,&bad));}assert(calls==start+10);
#endif
 printf("ACTUAL_LOAD_PROBE PASS calls=%u evictions=%u missing=%u\n",calls,evictions,nmissing);assert(nmissing==0);
}
