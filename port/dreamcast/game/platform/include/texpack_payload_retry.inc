// Exact packed-member failure spacing. Included only by TEX_PAYLOAD_RETRY=1.
// A validated pack index has at most 8192 unique sorted members (texpack_index.inc).
// No heap, replacement, missing-key insertion, healthy-member gate or resource-failure gate.
namespace texpack_payload_retry {
constexpr unsigned kMembers=8192,kWords=kMembers/32,kFrames=30;
static_assert(sizeof(unsigned)==4,"payload retry bitmaps require 32-bit unsigned");
unsigned current[kWords]{},next[kWords]{},base;
bool initialized;
void reset(){std::memset(current,0,sizeof(current));std::memset(next,0,sizeof(next));base=0;initialized=false;}
void advance(unsigned now){
    if(!initialized){base=now;initialized=true;return;}
    const unsigned elapsed=now-base; // unsigned subtraction covers natural UI-frame wrap
    if(elapsed<kFrames)return;
    if(elapsed>=2*kFrames)std::memset(current,0,sizeof(current));
    else std::memcpy(current,next,sizeof(current));
    std::memset(next,0,sizeof(next));base=now-elapsed%kFrames;
}
bool blocked(unsigned member,unsigned now){
    if(member>=kMembers)return false;
    advance(now);return (current[member/32]&(1U<<(member%32)))!=0;
}
void failed(unsigned member,unsigned now){
    if(member>=kMembers)return;
    advance(now);const unsigned bit=1U<<(member%32);current[member/32]|=bit;next[member/32]|=bit;
}
void succeeded(unsigned member){
    if(member>=kMembers)return;
    const unsigned bit=1U<<(member%32);current[member/32]&=~bit;next[member/32]&=~bit;
}
bool source_error(const char* why){
    if(!why)return false;
    // Literal whitelist from room/texture_package.cpp. Allocator/palette/VRAM
    // errors deliberately stay with their existing capacity/fragmentation recovery.
    static const char* const errors[]={
        "open failed","pack entry outside the pack","streamed header read failed",
        "invalid streamed metadata layout","streamed descriptor read failed",
        "magic, version, or header size mismatch","texture package range or stride mismatch",
        "streamed upload requires native texture layout","streamed payload read or CRC mismatch",
        "mipmapped texture must be square 16-bit VQ",
        "invalid texture dimensions, format, layout or payload size","streamed texture upload read failed"
    };
    for(const auto* error:errors)if(!std::strcmp(why,error))return true;
    return false;
}
}
