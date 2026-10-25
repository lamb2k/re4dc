#include "gc_asset_audio.h"
#include <cassert>
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <string>
using namespace re4dc_gcasset;
std::string logs;bool sq_held;int owner;
extern "C" void re4dc_log(const char* fmt,...){
    assert(!sq_held);char text[256];va_list ap;va_start(ap,fmt);const int n=vsnprintf(text,sizeof text,fmt,ap);va_end(ap);
    assert(n>=0 && unsigned(n)<sizeof text);logs+=text;
}
unsigned char mram[64]={1},aram[256]={};
unsigned rows(){unsigned count=0;std::size_t at=0;while((at=logs.find("GC-ASSET v=",at))!=std::string::npos){++count;++at;}return count;}
void load(unsigned bank=0){
    bank_begin(&owner,bank,1,64);bank_piece(&owner,1,0,mram,32);bank_piece(&owner,1,32,mram+32,32);bank_end(&owner,1);
    bank_begin(&owner,bank,2,256);bank_piece(&owner,2,0,aram,128);
    unsigned char stale[128];memset(stale,0xcd,sizeof stale);bank_piece(&owner,2,128,stale,128);bank_end(&owner,2);
}
void play(unsigned bank,unsigned generation){sq_held=true;const auto use=bank_ticket(bank,generation);played(use);sq_held=false;pump();}
void id(const Digest& d,char* out){for(unsigned i=0;i<20;++i)snprintf(out+2*i,3,"%02x",d.bytes[i]);}
void reload_between_bind_publish(){bank_begin(&owner,0,1,64);}
int main(){
    unsigned magic=0x31434941,total=32;memcpy(aram,&magic,4);memcpy(aram+8,&total,4);aram[96]=2;
    const Digest md=fingerprint(mram,sizeof mram),ad=fingerprint(aram,128);char mi[41],ai[41];id(md,mi);id(ad,ai);
    CatalogRow catalog[]={{"sound-mram",mi,md,Unknown},{"sound-aram",ai,ad,GameCube}};assert(install(catalog,2));
    load();const unsigned gen=bank_generation(0);assert(gen);
    // The independent audio thread may key on before main-thread catalog
    // publication. Its completed immutable digests are copied, never resolved
    // under G2, and remain exact even if the bank reloads before queue drain.
    begin(0x111,0,Required);play(0,gen);end(1);assert(rows()==2 && logs.find("errors=0")!=std::string::npos);
    logs.clear();bank_pump();
    assert(rows()==0);begin(0x111,1,Required);play(0,gen);end(1);
    assert(rows()==2 && logs.find("sound_bank=2")!=std::string::npos && logs.find("errors=0")!=std::string::npos);
    // SND_PAD_SKIP's stale tail never enters the exact AIC1 identity above.
    logs.clear();begin(0x113,2,Required);play(0,gen);end(1);assert(rows()==2);
    // Snapshot before key-on cannot relabel an event into a new room.
    logs.clear();begin(0x111,3,Required);sq_held=true;const auto paused=bank_ticket(0,gen);sq_held=false;end(1);
    assert(logs.find("errors=1")!=std::string::npos); // outstanding ticket set is terminal, counted once
    logs.clear();begin(0x113,4,Required);sq_held=true;played(paused);sq_held=false;pump();end(1);
    assert(rows()==0 && logs.find("errors=3")!=std::string::npos); // old outstanding set plus two late events
    // A canceled/incomplete new load revokes the previous bank before any copy.
    bank_begin(&owner,0,1,64);assert(bank_generation(0)!=gen);
    logs.clear();begin(0x111,5,Required);play(0,gen);end(1);assert(rows()==0 && logs.find("catalog-token")!=std::string::npos);
    // Duplicate/gapped source callbacks and wrong request owner fail closed.
    bank_piece(&owner,1,32,mram,32);bank_end(&owner,1);assert(!bank_generation(0));bank_pump();
    assert(logs.find("bank-source-lifetime")!=std::string::npos);
    load();bank_pump();const unsigned current=bank_generation(0);assert(current);
    // A source step that cannot acquire metadata must invalidate old tokens.
    audio_test_records_lock(true);bank_begin(&owner,0,1,64);audio_test_records_lock(false);assert(!bank_generation(0));
    logs.clear();begin(0x111,6,Required);play(0,current);bank_pump();end(1);assert(rows()==0);
    // A new load between catalog lookup and publish cannot resurrect the old
    // generation, even when the same bank and source pointers are reused.
    load();const unsigned pending=bank_generation(0);audio_test_before_publish(reload_between_bind_publish);bank_pump();
    logs.clear();begin(0x111,7,Required);play(0,pending);end(1);assert(rows()==0);
    // Retry from the beginning gets a new generation; no old partial bytes.
    load();bank_pump();logs.clear();begin(0x111,8,Required);play(0,bank_generation(0));end(1);assert(rows()==2);
    // Disc/catalog replacement leaves old live bank tokens invalid. Rebinding
    // uses saved immutable digests, never reads mutable/relocated MRAM tables.
    assert(install(catalog,2));logs.clear();begin(0x111,9,Required);play(0,bank_generation(0));end(1);assert(rows()==0);
    assert(logs.find("catalog-token")!=std::string::npos);
    // Per-entry stream proof (record + payload groups) is exact bytes, never the filename.
    const Digest container=fingerprint("AIS1 metadata + intro + loop",28);
    stream_source(container);const unsigned stream_gen=stream_generation();
    logs.clear();begin(0x111,10,Required);sq_held=true;const auto stream_use=stream_ticket(stream_gen);played(stream_use);sq_held=false;pump();end(1);
    {char id[41];for(unsigned i=0;i<20;++i)std::snprintf(id+2*i,3,"%02x",unsigned(container.bytes[i]));
     assert(rows()==1 && logs.find(std::string("kind=sound-stream id=")+id)!=std::string::npos);}  // per-entry id = digest prefix
    assert(logs.find("sound_stream=1")!=std::string::npos);
    bank_pump();
    stream_source(fingerprint("changed source",14));bank_pump();
    logs.clear();begin(0x111,11,Required);sq_held=true;played(stream_ticket(stream_gen));sq_held=false;pump();end(1);
    assert(rows()==0 && logs.find("catalog-token")!=std::string::npos);
    const unsigned fresh_stream=stream_generation();stream_source_failed();bank_pump();
    logs.clear();begin(0x111,12,Required);sq_held=true;played(stream_ticket(fresh_stream));sq_held=false;pump();end(1);assert(rows()==0);
}
