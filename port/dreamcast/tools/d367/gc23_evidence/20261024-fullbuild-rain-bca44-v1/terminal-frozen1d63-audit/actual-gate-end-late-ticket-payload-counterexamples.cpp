
#include "gc_asset_static.h"
#include <cassert>
#include <cstdio>
#include <cstdarg>
#include <cstring>
#include <string>
using namespace re4dc_gcasset;bool protected_scope;std::string logs;
extern "C" void re4dc_log(const char*fmt,...){assert(!protected_scope);char s[256];va_list a;va_start(a,fmt);vsnprintf(s,sizeof s,fmt,a);va_end(a);logs+=s;}
int main(){assert(install(nullptr,0));
// A clean END does not prevent a later producer attempt. Closing diagnostic
// admission makes that future attempt a fault, but only a later pump logs it.
begin(0x111,1,Required);close_audio_admission();pump();end(1);assert(logs.find("errors=0")!=std::string::npos);logs.clear();protected_scope=true;auto invalid=audio_ticket();protected_scope=false;assert(invalid.slot==32&&logs.empty());pump();assert(logs.find("unowned-audio")!=std::string::npos);
// An empty observation queue can still have a captured uncompleted ticket.
logs.clear();begin(0x112,2,Required);auto outstanding=audio_ticket();assert(outstanding.slot<32);pump();close_audio_admission();end(2);assert(logs.find("errors=1")!=std::string::npos);logs.clear();protected_scope=true;queued_checked(outstanding,SoundBank,{});protected_scope=false;assert(logs.empty());pump();assert(logs.find("audio-room-lifetime")!=std::string::npos);
// Deferred geometry/payload latches intentionally have no visit stamp.
// If a draw is allowed after finish, it can remain silent then be flushed in
// another visit. A final fixture must stop that producer, not infer quiescence.
logs.clear();begin(0x113,3,Required);static PayloadProof proof;static int owner;unsigned char bytes[32]={17};assert(payload_capture(proof,&owner,bytes,sizeof bytes));const unsigned serial=proof.serial;payload_flush_all();end(3);assert(logs.find("errors=0")!=std::string::npos);logs.clear();protected_scope=true;payload_accept(&proof,serial,(1U<<SourceGeometry)|(1U<<Weapon));protected_scope=false;assert(logs.empty());begin(0x114,4,Required);payload_flush_all();end(4);assert(logs.find("room=0114 visit=4 kind=geometry")!=std::string::npos&&logs.find("source_geometry=1")!=std::string::npos&&logs.find("weapon=1")!=std::string::npos);payload_retire(proof);
}
