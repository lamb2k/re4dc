#include "../../../game/platform/include/gc_asset_members.h"
#include <cassert>
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>
using namespace re4dc_gcasset;
std::string logs;
bool sq_held;
extern "C" void re4dc_log(const char* fmt,...) {
    assert(!sq_held);
    char line[256];va_list ap;va_start(ap,fmt);const int length=vsnprintf(line,sizeof line,fmt,ap);va_end(ap);
    assert(length>=0 && unsigned(length)<sizeof line);logs+=line;
}
void word(std::vector<unsigned char>& data,unsigned offset,unsigned value) { std::memcpy(data.data()+offset,&value,4); }
std::vector<unsigned char> indexed(bool empty_alias=false,bool duplicate=false) {
    std::vector<unsigned char> bytes(256,0);word(bytes,0,3);word(bytes,4,224);
    word(bytes,16,64);word(bytes,20,empty_alias||duplicate?64:128);word(bytes,24,192);
    if(!empty_alias)std::memcpy(bytes.data()+28,"BIN",3);
    std::memcpy(bytes.data()+32,"BIN",3);std::memcpy(bytes.data()+36,"TPL",3);
    return bytes;
}
std::vector<unsigned char> named(bool duplicate=false,bool malformed=false) {
    std::vector<unsigned char> bytes(512,0);word(bytes,0,1);word(bytes,16,32);std::memcpy(bytes.data()+20,"ETM",3);
    word(bytes,32,2);word(bytes,64,192);word(bytes,256,192);
    std::strcpy(reinterpret_cast<char*>(bytes.data()+96),"et0100.bin");
    std::strcpy(reinterpret_cast<char*>(bytes.data()+288),duplicate?"ET0100.BIN":"et0200.bin");
    if(malformed)word(bytes,256,9999);
    return bytes;
}
// gc_asset_disc.cpp (KOS fs) is not host-built: block_adopt's catalog check passes here.
namespace re4dc_gcasset { bool ensure_disc_catalog() { return true; } }
bool same(const Digest& a,const Digest& b) { return !std::memcmp(a.bytes,b.bytes,32); }
Digest digest(const ModelMember& member){AssetDescription row;assert(describe_checked(member.asset,&row));return row.digest;}
int main() {
    install(nullptr,0);begin(0x111,1,Required);
    // Sub screen swap (cast-ps2-25 r16): an archive inside the parked area drops its members and binds nothing while
    // parked; unpark restores it with its adopt-time digests (the relocated bytes are not hashed again).
    {auto parked_archive=indexed();ModelMember before{},after_unpark{};int park_owner=0;
     assert(member_adopt(&park_owner,parked_archive.data(),parked_archive.size(),true));
     assert(member_capture(parked_archive.data()+64));assert(member_lookup(parked_archive.data()+64,&before));
     const Digest kept=digest(before);parked_archive[72]=7;
     member_park(parked_archive.data()+8,16);assert(!member_lookup(parked_archive.data()+64,&after_unpark));
     assert(!member_capture(parked_archive.data()+64));
     member_unpark();assert(member_lookup(parked_archive.data()+64,&after_unpark));assert(after_unpark.serial==before.serial);
     assert(member_capture(parked_archive.data()+64));
     assert(member_lookup(parked_archive.data()+64,&after_unpark));assert(same(kept,digest(after_unpark)));
     {auto screen=indexed();int screen_owner=0;member_park(parked_archive.data(),parked_archive.size());
      assert(member_adopt(&screen_owner,parked_archive.data(),parked_archive.size(),true));member_unpark(); // screen's own: retired
      (void)screen;}
     assert(member_lookup(parked_archive.data()+64,&after_unpark));assert(after_unpark.serial==before.serial);
     member_park(parked_archive.data()+256,64);assert(member_lookup(parked_archive.data()+64,&after_unpark)); // outside
     member_unpark();member_retire(&park_owner);}
    auto archive=indexed();int owner=0;ModelMember original{},later{};
    assert(member_adopt(&owner,archive.data(),archive.size(),true));
    assert(member_capture(archive.data()+64));assert(member_lookup(archive.data()+64,&original));assert(original.arc==4);
    const Digest original_digest=digest(original);
    assert(same(original_digest,fingerprint(archive.data()+64,64)));
    archive[72]=99; // pointer relocation / in-place FE mutation must not change bound digest
    assert(member_adopt(&owner,archive.data(),archive.size(),true));assert(member_capture(archive.data()+64));
    assert(member_lookup(archive.data()+64,&later));assert(same(original_digest,digest(later)));assert(original.serial==later.serial);
    member_retire(&owner);assert(!member_lookup(archive.data()+64,&later));
    assert(member_adopt(&owner,archive.data(),archive.size(),true));assert(member_capture(archive.data()+64));
    assert(member_lookup(archive.data()+64,&later));assert(!same(original_digest,digest(later)));assert(original.serial!=later.serial);
    member_retire_transient();assert(!member_lookup(archive.data()+64,&later));
    // Another owner cannot alias cached/mutated bytes and later hash them as
    // a fresh original payload after the first owner's retirement.
    int alias_owner=1;
    assert(member_adopt(&owner,archive.data(),archive.size(),true));assert(member_capture(archive.data()+64));
    assert(!member_adopt(&alias_owner,archive.data(),archive.size(),true));
    assert(!member_lookup(archive.data()+64,&later));member_retire(&owner);
    assert(!member_capture(archive.data()+64)); // rejected alias never becomes an owner
    // Partial overlaps also revoke both views; reject before inspecting a
    // candidate directory inside an existing archive's payload.
    assert(member_adopt(&owner,archive.data(),archive.size(),true));
    assert(!member_adopt(&alias_owner,archive.data()+64,archive.size()-64,true));
    assert(!member_capture(archive.data()+64));
    assert(logs.find("member-owner-overlap")!=std::string::npos);
    assert(member_adopt(&owner,archive.data(),archive.size(),true,PlayerOwner));
    assert(member_capture(archive.data()+64));assert(member_lookup(archive.data()+64,&later));assert(later.family==PlayerOwner);
    assert(member_adopt(&owner,archive.data(),archive.size(),true,PlayerOwner));
    assert(!member_adopt(&owner,archive.data(),archive.size(),true,WeaponOwner));
    assert(!member_lookup(archive.data()+64,&later)); // family changes cannot re-certify relocated current bytes
    auto empty=indexed(true);assert(member_adopt(&owner,empty.data(),empty.size(),true));
    assert(member_capture(empty.data()+64));assert(member_lookup(empty.data()+64,&later));assert(later.arc==5);member_retire(&owner);
    auto duplicate=indexed(false,true);assert(member_adopt(&owner,duplicate.data(),duplicate.size(),true));
    assert(!member_capture(duplicate.data()+64));member_retire(&owner);
    auto props=named();assert(member_adopt(&owner,props.data(),props.size(),true));
    assert(member_capture(props.data()+128));assert(member_lookup(props.data()+128,&later));
    assert(!std::strcmp(later.name,"et0100.bin"));assert(later.arc==0);assert(same(digest(later),fingerprint(props.data()+128,128)));
    assert(!member_capture(props.data()+510));member_retire(&owner);
    auto mixed=named();std::strcpy(reinterpret_cast<char*>(mixed.data()+288),"et0200.tpl");
    assert(member_adopt(&owner,mixed.data(),mixed.size(),true));assert(member_capture(mixed.data()+128));
    assert(!member_capture(mixed.data()+320));member_retire(&owner); // a normal TPL record is not a model BIN
    auto duplicate_names=named(true);assert(member_adopt(&owner,duplicate_names.data(),duplicate_names.size(),true));
    assert(!member_capture(duplicate_names.data()+128));member_retire(&owner);
    auto overrun=named(false,true);assert(member_adopt(&owner,overrun.data(),overrun.size(),true));
    assert(!member_capture(overrun.data()+128));member_retire(&owner);
    assert(!member_capture(reinterpret_cast<void*>(std::uintptr_t(1)))); // never dereference unbound pointers
    auto malformed=indexed();word(malformed,0,4097);assert(!member_adopt(&owner,malformed.data(),malformed.size(),true));
    std::vector<std::vector<unsigned char>> many_archives;int owners[17]{};
    for(unsigned i=0;i<17;++i)many_archives.push_back(indexed());
    for(unsigned i=0;i<16;++i)assert(member_adopt(&owners[i],many_archives[i].data(),many_archives[i].size(),true));
    assert(!member_adopt(&owners[16],many_archives[16].data(),many_archives[16].size(),true));
    assert(member_capture(many_archives[0].data()+64));
    assert(!member_adopt(&owners[16],many_archives[0].data(),many_archives[0].size(),true));
    assert(!member_lookup(many_archives[0].data()+64,&later)); // overlap revokes even at full capacity
    assert(!member_capture(many_archives[0].data()+64));
    member_retire_transient();
    constexpr unsigned count=258,directory=16+8*count;
    std::vector<unsigned char> many_members(directory+count*64,0);word(many_members,0,count);
    for(unsigned i=0;i<count;++i) { word(many_members,16+4*i,directory+i*64);std::memcpy(many_members.data()+16+4*count+4*i,"BIN",3); }
    assert(member_adopt(&owner,many_members.data(),many_members.size(),true));
    for(unsigned i=0;i<256;++i)assert(member_capture(many_members.data()+directory+64*i));
    assert(!member_capture(many_members.data()+directory+64*256));   // MemberCount 256 (gc-catalog24b)member_retire(&owner);
    assert(logs.find("GC-ASSET v=")==std::string::npos); // binding/preparation is not drawing
    auto accepted=indexed();assert(member_adopt(&owner,accepted.data(),accepted.size(),true));
    assert(member_capture(accepted.data()+64));assert(member_lookup(accepted.data()+64,&original));
    accepted[72]=12;const auto before=logs.size();
    sq_held=true;member_accept(original.serial,(1U<<SourceGeometry)|(1U<<Weapon));sq_held=false;
    assert(logs.size()==before);member_flush();
    assert(logs.find("kind=model")!=std::string::npos); // original captured bytes at accepted emission
    assert(logs.find("consumer=source_geometry")!=std::string::npos);
    const auto after=logs.size();
    sq_held=true;member_accept(original.serial,1U<<Weapon);sq_held=false;
    member_retire(&owner);assert(!member_lookup(accepted.data()+64,&later));
    assert(logs.size()==after); // same identity across consumers logs once
    sq_held=true;member_accept(original.serial,1U<<SourceGeometry);sq_held=false;
    member_flush();assert(logs.find("unbound-accepted-model")!=std::string::npos);
    source_use={99,1U<<SourceGeometry,&owner,&alias_owner};
    {SourceScope scope;assert(!source_use.serial);source_use.serial=42;}
    assert(source_use.serial==99);source_use={};
    // Replay reserves UINT_MAX as "not replaying"; it can never be a live
    // member serial, even at exhaustion immediately before integer wrap.
    auto edge=indexed();member_test_serial(0xfffffffdU);
    assert(member_adopt(&owner,edge.data(),edge.size(),true));assert(member_capture(edge.data()+64));
    assert(member_lookup(edge.data()+64,&later));assert(later.serial==0xfffffffeU);
    assert(!member_capture(edge.data()+128));member_retire(&owner);
    end(1);assert(logs.find("GC-ASSET-ERROR")!=std::string::npos); // all failed coverage persists
}
