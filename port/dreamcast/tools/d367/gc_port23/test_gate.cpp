#include "../../../game/platform/include/gc_asset_gate.h"
#include <cassert>
#include <cstdarg>
#include <cstdio>
#include <string>
std::string output;
extern "C" void re4dc_log(const char* fmt, ...) {
    char line[256];va_list args;va_start(args,fmt);const int written=vsnprintf(line,sizeof line,fmt,args);va_end(args);
    assert(written>=0 && unsigned(written)<sizeof line);output+=line;
}
using namespace re4dc_gcasset;
unsigned rows() {
    unsigned n=0;std::string::size_type p=0;
    while((p=output.find("GC-ASSET v=",p))!=std::string::npos) { ++n;++p; }
    return n;
}
int main() {
    const Digest golden=fingerprint("abc",3);
    const unsigned char abc[]={0xba,0x78,0x16,0xbf,0x8f,0x01,0xcf,0xea,0x41,0x41,0x40,0xde,0x5d,0xae,0x22,0x23,
        0xb0,0x03,0x61,0xa3,0x96,0x17,0x7a,0x9c,0xb4,0x10,0xff,0x61,0xf2,0x00,0x15,0xad};
    for(unsigned i=0;i<32;++i)assert(golden.bytes[i]==abc[i]);
    Digest gc{}, ps2{}, unknown{};gc.bytes[0]=1;ps2.bytes[0]=2;unknown.bytes[0]=3;
    CatalogRow catalog[]={{"model","trap",gc,GameCube},{"texture","gc-key",ps2,PS2}};
    assert(install(catalog,2));
    begin(0x111,1,Required);
    for(unsigned i=0;i<ConsumerCount;++i)checked(Consumer(i));
    emitted(SourceGeometry,"model","trap",gc);
    emitted(Weapon,"model","trap",gc); // same asset through another consumer still logs once
    emitted(SourceGeometry,"model","trap",gc); // one line per id/digest/room
    emitted(Texture,"texture","gc-key",ps2);   // PS2 bytes under GC key are clean
    emitted(Texture,"texture","gc-key",unknown); // same key, unreviewed bytes stay unknown
    queued(audio_ticket(),SoundBank,"sample","core:1",gc);
    pump();end(42);
    assert(rows()==3);
    assert(output.find("provenance=unknown")!=std::string::npos);
    assert(output.find("source_geometry=2 texture=2")!=std::string::npos);
    assert(output.find("sound_bank=1")!=std::string::npos);
    assert(output.find("unique=3 overflow=0 errors=0")!=std::string::npos);
    begin(0x113,2,Required);emitted(SourceGeometry,"model","trap",gc);end(1);
    assert(rows()==4); // new room is not suppressed
    output.clear();
    begin(0x111,3,Required);
    for(unsigned i=0;i<40;++i)queued(audio_ticket(),SoundBank,"sample","core:1",gc);
    end(1);
    assert(output.find("errors=9")!=std::string::npos); // bounded handoff cannot silently drop events
    output.clear();
    assert(install(catalog,2)); // resets the bounded unknown quarantine
    begin(0x111,4,Required);
    for(unsigned i=0;i<9;++i) {
        char id[40];snprintf(id,sizeof id,"model-%u",i);emitted(SourceGeometry,"model",id,gc);
    }
    end(1);assert(output.find("unique=8 overflow=1")!=std::string::npos);
    assert(!install(catalog,0xffffffffU)); // invalid table count must be rejected before walking
    assert(install(catalog,2));
    output.clear();begin(0x111,5,Required);
    auto late=audio_ticket();end(1);
    assert(output.find("errors=1")!=std::string::npos); // ticket paused before delivery
    output.clear();begin(0x113,6,Required);
    queued(late,SoundBank,"sample","core:1",gc);pump();end(1);
    assert(output.find("GC-ASSET v=")==std::string::npos); // cannot relabel old audio as room 0113
    assert(output.find("errors=2")!=std::string::npos);
    output.clear();begin(0x111,7,Required);
    test_queue_lock(true);end(1);test_queue_lock(false);
    assert(output.find("errors=2")!=std::string::npos); // lock contention cannot print errors=0
    output.clear();queued(audio_ticket(),SoundBank,"sample","core:1",gc);pump();
    assert(output.find("GC-ASSET-ERROR")!=std::string::npos); // after END stays an explicit error
    output.clear();begin(0xffffffffU,0xffffffffU,0xffffffffU);
    test_max_counters();
    emitted(SourceGeometry,"abcdefghijklmno","abcdefghijklmnopqrstuvwxyz012345678901234567890",gc);
    end(0xffffffffU); // all production formatter rows must fit the real 256-byte logger
}
