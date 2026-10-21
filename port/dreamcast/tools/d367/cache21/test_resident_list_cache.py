#!/usr/bin/env python3
"""Differential tests of the actual source preload functions, without game data."""
from pathlib import Path
import argparse,hashlib,json,subprocess,tempfile
ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path);a=ap.parse_args()
root=Path(__file__).resolve().parents[5];out=a.out or Path(tempfile.mkdtemp(prefix='resident-list-source-'));out.mkdir(parents=True,exist_ok=True)
source='port/dreamcast/game/platform/native_ui.cpp';base=subprocess.check_output(['git','show','c7e0358a44677a15123a7f4233c4115eba627694:'+source],cwd=root,text=True);candidate=(root/source).read_text()
def functions(s):
    first=s.index('void preload_select(');start=s.rfind('#if defined(RE4DC_TEX_PKG_SKIP)',0,first);end=s.index('\n#if RE4DC_ROOM_RESIDENT',first)
    begin=s.index('unsigned resident_listed,resident_picked;');stop=s.index('#endif\n#if RE4DC_IO_PROBE',begin)
    return s[start:end]+'\n'+s[begin:stop]
prefix=r"""
#include <algorithm>
#include <array>
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <sstream>
#include <string>
#include <vector>
#include "resident_list_cache.h"
namespace re4dc { namespace profile {struct Source{unsigned room=0;};} namespace texture {
enum class RangeRead {ok,absent,short_file,io_error};
struct Identity{unsigned crc,fnv,width,height,format;};
struct SourceIdentityTable{std::vector<Identity> rows;unsigned count()const{return rows.size();}bool record(unsigned i,unsigned&c,unsigned&f,unsigned&w,unsigned&h,unsigned&t)const{if(i>=rows.size())return false;auto r=rows[i];c=r.crc;f=r.fnv;w=r.width;h=r.height;t=r.format;return true;}};
} }
using Rec=re4dc::texture::ResidentListRecord;
struct FakeFS{std::vector<unsigned char> data;unsigned calls=0,fail_offset=~0u,oom_offset=~0u;bool absent=false,shrink=false;};
FakeFS* active_fs;unsigned active_room;
void re4dc_profile_source(re4dc::profile::Source*s){s->room=active_room;}
void re4dc_log(const char*,...){}
namespace re4dc { namespace texture {
RangeRead read_file_range(const char*,std::uint32_t off,void*to,std::uint32_t bytes,unsigned long long*total){
 auto&f=*active_fs;++f.calls;if(f.absent)return RangeRead::absent;
 unsigned n=f.data.size();if(f.shrink&&off>=512)n-=512;if(total)*total=n;
 if(static_cast<unsigned long long>(off)+bytes>n)return RangeRead::short_file;
 if(off==f.fail_offset||off==f.oom_offset)return RangeRead::io_error;
 std::memcpy(to,f.data.data()+off,bytes);return RangeRead::ok;
}
} }
#define __sh__ 1
#define RE4DC_QUALITY_ASSETS 0
#define RE4DC_TEX_PKG_SKIP 0
"""
common=r"""
struct Key{unsigned crc=0,fnv=0;bool operator==(const Key&b)const{return crc==b.crc&&fnv==b.fnv;}};
struct Package{unsigned bytes=0;unsigned vram_bytes()const{return bytes;}};
struct Entry{bool valid=false;Key key;unsigned frame=0;Package package;};
std::array<Entry,512> entries{};std::array<Key,16> missing_keys{};
struct PreloadPick{Key key;unsigned short width,height,format;};PreloadPick preload_picks[512]{};
constexpr unsigned kCoreKeys=64;Key core_keys[kCoreKeys]{};unsigned core_nkeys=0;bool core_room_on=false;unsigned frame=0;
unsigned preload_least(unsigned width,unsigned height){unsigned pw=8,ph=8;while(pw<width)pw*=2;while(ph<height)ph*=2;return std::min(pw*ph*2,2048+pw*ph/4);}
"""
wrapper=r"""
void clear_entries(){entries={};}
void reset(){entries={};missing_keys={};std::memset(preload_picks,0,sizeof(preload_picks));std::memset(core_keys,0,sizeof(core_keys));core_nkeys=0;core_room_on=false;frame=0;
#if RE4DC_RESIDENT_LIST_CACHE
resident_list_cache={};
#endif
}
std::string run(unsigned limit,unsigned budget,bool new_owner=false){
 ++frame;unsigned n=0,resident=0,bytes=0;
 re4dc::texture::SourceIdentityTable owner;if(new_owner)owner.rows={{90001,90002,8,8,1},{90003,90004,16,8,1}};
 preload_select(owner,n,resident,bytes,limit,budget);preload_resident(n,resident,bytes,limit,budget);
 std::ostringstream o;o<<n<<','<<resident<<','<<bytes<<','<<resident_listed<<','<<resident_picked<<','<<core_nkeys<<','<<core_room_on;
 for(unsigned i=0;i<core_nkeys;++i)o<<" K"<<core_keys[i].crc<<','<<core_keys[i].fnv;
 for(unsigned i=0;i<n;++i){auto p=preload_picks[i];o<<" P"<<p.key.crc<<','<<p.key.fnv<<','<<p.width<<','<<p.height<<','<<p.format;
   auto it=std::find_if(entries.begin(),entries.end(),[](const Entry&e){return!e.valid;});assert(it!=entries.end());*it={true,p.key,frame,{preload_least(p.width,p.height)}};}
 return o.str();
}
"""
main=r"""
FakeFS ref_fs,on_fs;unsigned checks=0;
std::vector<unsigned char> file(std::vector<Rec>rows,unsigned pieces=0){unsigned bytes=pieces?pieces*512:((rows.size()+31)/32)*512;assert(bytes>=rows.size()*sizeof(Rec));std::vector<unsigned char>b(bytes);std::memcpy(b.data(),rows.data(),rows.size()*sizeof(Rec));return b;}
Rec rec(unsigned room,unsigned key,unsigned width=8,unsigned height=8){return{static_cast<std::uint16_t>(room),static_cast<std::uint16_t>(width),static_cast<std::uint16_t>(height),1,key,key*17+3};}
void reset(std::vector<unsigned char>b){ref::reset();on::reset();ref_fs={};on_fs={};ref_fs.data=on_fs.data=b;}
unsigned step(const char*name,unsigned room=0x100,unsigned limit=448,unsigned budget=10000000,bool owner=false){
 active_room=room;active_fs=&ref_fs;auto expected=ref::run(limit,budget,owner);active_fs=&on_fs;unsigned c=on_fs.calls;auto actual=on::run(limit,budget,owner);
 if(expected!=actual){std::fprintf(stderr,"case %s mismatch\nref %s\non %s\n",name,expected.c_str(),actual.c_str());std::abort();}++checks;return on_fs.calls-c;
}
int main(){
 std::vector<Rec>r;for(unsigned i=0;i<6;++i)r.push_back(rec(0,1+i));for(unsigned i=0;i<117;++i)r.push_back(rec(0x100,100+i));for(unsigned i=0;i<84;++i)r.push_back(rec(0x103,1000+i));
 auto full=file(r,169);reset(full);assert(step("cold169")==170);assert(step("warm-zero-scan")==0);assert(step("new-weapon-owner-still-admits",0x100,448,10000000,true)==0);
 ref::clear_entries();on::clear_entries();assert(step("movie-release-refill")==0);ref::clear_entries();on::clear_entries();assert(step("menu-owner-refill",0x100,448,10000000,true)==0);
 assert(step("room-change",0x103)==170);assert(step("room-warm",0x103)==0);assert(step("return-room",0x100)==170);
 reset(full);step("initial-limit-full",0x100,0);assert(step("later-larger-limit",0x100)==0);
 reset(full);step("initial-byte-limit",0x100,448,0);assert(step("later-more-byte-space")==0);
 reset(full);ref_fs.absent=on_fs.absent=true;assert(step("absent-not-cached")==1);assert(step("absent-retry")==1);ref_fs.absent=on_fs.absent=false;assert(step("file-appears")==170);assert(step("appeared-warm")==0);
 for(unsigned fault:{0u,512u,1024u}){reset(full);ref_fs.fail_offset=on_fs.fail_offset=fault;assert(step("io-error-prefix")==fault/512+1);assert(step("io-error-retry")==fault/512+1);ref_fs.fail_offset=on_fs.fail_offset=~0u;assert(step("io-recovery")==170);assert(step("io-recovered-warm")==0);}
 reset(full);ref_fs.oom_offset=on_fs.oom_offset=512;step("read-layer-oom");assert(step("oom-not-negative-cached")==2);ref_fs.oom_offset=on_fs.oom_offset=~0u;assert(step("oom-recovery")==170);
 reset(full);ref_fs.data.pop_back();on_fs.data.pop_back();assert(step("trailing-partial-piece")==169);assert(step("truncated-retry")==169);
 reset(full);ref_fs.shrink=on_fs.shrink=true;assert(step("size-changes-mid-scan")==169);assert(step("changed-size-not-cached")==169);
 r={rec(0,5,8,0),rec(0,6,2048,8),rec(0,7,0,8),rec(0x100,9,0,8),rec(0x100,10,8,0),rec(0x100,11,2048,8),rec(0x100,12),rec(0x100,12),rec(0x103,13)};reset(file(r));step("invalid-and-duplicate-rows");assert(step("invalid-row-semantics-warm")==0);
 r.clear();for(unsigned i=0;i<256;++i)r.push_back(rec(0x100,i+1));reset(file(r));step("exact256");assert(step("exact256-warm")==0);
 r.push_back(rec(0x100,9999));reset(file(r));step("overflow257");assert(step("overflow-preserves-full-scan")==10);
 reset({});assert(step("empty-file")==1);assert(step("empty-complete-cache")==0);
 reset(file({rec(0x103,9)}));step("no-matching-rows");assert(step("empty-selection-cache")==0);
 reset(file({rec(0,1),rec(0,2)}));step("room-zero-core",0);assert(step("room-zero-warm",0)==0);
 std::printf("PASS checks=%u core_pin=%d cache_bytes=%zu\n",checks,RE4DC_CORE_PIN,sizeof(re4dc::texture::ResidentListCache));
}
"""
cpp=prefix+'\nnamespace ref {\n#define RE4DC_RESIDENT_LIST_CACHE 0\n'+common+functions(base)+wrapper+'\n}\n#undef RE4DC_RESIDENT_LIST_CACHE\nnamespace on {\n#define RE4DC_RESIDENT_LIST_CACHE 1\n'+common+functions(candidate)+wrapper+'\n}\n'+main
(out/'actual-source.cpp').write_text(cpp);runs=[]
for pin in [0,1,2]:
 exe=out/('test-core'+str(pin));cmd=['g++','-std=c++17','-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-DRE4DC_CORE_PIN='+str(pin),'-I',str(root/'port/dreamcast/game/platform/include'),str(out/'actual-source.cpp'),'-o',str(exe)]
 c=subprocess.run(cmd,capture_output=True,text=True);(out/('compile-core'+str(pin)+'.log')).write_text(c.stdout+c.stderr);assert c.returncode==0,c.stderr
 r=subprocess.run([str(exe)],capture_output=True,text=True);(out/('run-core'+str(pin)+'.log')).write_text(r.stdout+r.stderr);assert r.returncode==0,r.stdout+r.stderr;runs.append(r.stdout.strip())
receipt=dict(base='c7e0358a44677a15123a7f4233c4115eba627694',source_sha256=hashlib.sha256(candidate.encode()).hexdigest(),generated_sha256=hashlib.sha256(cpp.encode()).hexdigest(),runs=runs,scope='Actual preload_select + preload_resident extracted from base and candidate, synthetic identities/file backend; ASan+UBSan. Not full renderer, target performance, or console acceptance.')
(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
