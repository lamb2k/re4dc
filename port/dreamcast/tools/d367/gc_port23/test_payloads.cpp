#include "gc_asset_payloads.h"
#include <cassert>
#include <cstdarg>
#include <cstdio>
#include <string>
using namespace re4dc_gcasset;
std::string logs;bool sq_held;
extern "C" void re4dc_log(const char* fmt,...){
    assert(!sq_held);char line[256];va_list ap;va_start(ap,fmt);const int n=vsnprintf(line,sizeof line,fmt,ap);va_end(ap);
    assert(n>=0 && unsigned(n)<sizeof line);logs+=line;
}
struct Re4dcModelPart{const void* model;const void* info;};
// ACTUAL_UI_HELPERS
unsigned rows(){unsigned count=0;std::size_t at=0;while((at=logs.find("GC-ASSET v=",at))!=std::string::npos){++at;++count;}return count;}
int main(){
    assert(install(nullptr,0));begin(0x111,1,Required);
    int owner,other,model,info;unsigned char geometry[64]={1},layout[32]={2},replacement[64]={3};
    PayloadProof proof,alias;
    assert(payload_capture(proof,&owner,geometry,sizeof geometry,layout,sizeof layout));
    const unsigned serial=proof.serial;const CheckedAsset original=proof.asset;
    assert(logs.empty() || rows()==0); // immutable preparation is not use
    geometry[0]=9; // adopt/conversion can mutate after the immutable capture
    assert(payload_capture(proof,&owner,geometry,sizeof geometry,layout,sizeof layout));
    assert(proof.serial==serial && proof.asset.value==original.value);
    {PayloadScope scope(proof,&owner,&model,&info);gcasset_model_prepare(nullptr);
        sq_held=true;gcasset_model_accept();sq_held=false;}
    payload_flush_all();assert(rows()==2); // geometry + interpretation sidecar
    assert(logs.find("kind=geometry")!=std::string::npos && logs.find("kind=layout")!=std::string::npos);
    logs.clear();{PayloadScope scope(proof,&other,&model,&info,(1U<<SourceGeometry)|(1U<<Weapon));gcasset_model_prepare(nullptr);sq_held=true;gcasset_model_accept();sq_held=false;}
    payload_flush_all();assert(rows()==0 && logs.find("unbound-accepted-payload")!=std::string::npos && logs.find("consumer=3")!=std::string::npos); // wrong active owner never inherits; known class survives
    // Deferred proof stays attached to the original stable object + serial.
    payload_retire(proof);assert(payload_capture(proof,&owner,replacement,sizeof replacement));
    logs.clear();{ReplayScope replay(serial,1U<<SourceGeometry,&proof);PayloadScope scope(proof,&owner,&model,&info);
        gcasset_model_prepare(nullptr);sq_held=true;gcasset_model_accept();sq_held=false;}
    payload_flush_all();assert(rows()==0 && logs.find("unbound-accepted-payload")!=std::string::npos);
    // Missing replay proof cannot be replaced with the current package.
    logs.clear();{ReplayScope replay(0,0);PayloadScope scope(proof,&owner);gcasset_model_prepare(nullptr);sq_held=true;gcasset_model_accept();sq_held=false;}
    member_flush();assert(rows()==0 && logs.find("unbound-accepted-model")!=std::string::npos);
    // Owner overlap revokes the previous proof before failing adoption.
    assert(!payload_capture(alias,&other,replacement,sizeof replacement));assert(!proof.serial);
    logs.clear();sq_held=true;payload_accept(&proof,serial,1U<<SourceGeometry);sq_held=false;payload_flush_all();assert(rows()==0);
    assert(payload_capture(proof,&owner,replacement,sizeof replacement));
    assert(!payload_capture(proof,&owner,nullptr,64));assert(!proof.serial);
    // A catalog replacement invalidates surviving owner tokens. Duplicate
    // current capture deliberately cannot rehash already-mutated geometry.
    assert(payload_capture(proof,&owner,replacement,sizeof replacement));unsigned current=proof.serial;
    end(1);assert(install(nullptr,0));begin(0x113,2,Required);logs.clear();
    assert(payload_capture(proof,&owner,replacement,sizeof replacement));assert(proof.serial==current);
    sq_held=true;payload_accept(&proof,current,1U<<SourceGeometry);sq_held=false;payload_flush_all();
    assert(rows()==0 && logs.find("catalog-token")!=std::string::npos);
    payload_retire(proof);
    // Intrusive registration is bounded and allocates no runtime table.
    PayloadProof capacity[129];unsigned char bytes[129][64]{};int owners[129];unsigned admitted=0;
    for(unsigned i=0;i<129;++i){if(payload_capture(capacity[i],&owners[i],bytes[i],64))++admitted;else break;}
    assert(admitted<129 && logs.find("payload-owner-capacity")!=std::string::npos);
    for(auto& item:capacity)payload_retire(item);
    end(1);
}
