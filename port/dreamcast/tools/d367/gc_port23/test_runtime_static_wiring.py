"""Current static caller bodies; original reads, owner lifetimes and accepted batches."""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
from test_runtime_hooks import function

HERE=Path(__file__).resolve().parent
GAME=HERE.parents[2]/'game'
BASE='9d560ca3574e0757fe1a79ef103fc1c42b5917c4'

class StaticWiringTests(unittest.TestCase):
    def run_cpp(self,fixture,defines=(),reject=False):
        with tempfile.TemporaryDirectory(prefix='gc-static-wiring-',dir='/dev/shm') as temp:
            root=Path(temp);(root/'test.cpp').write_text(fixture)
            compiled=subprocess.run(['g++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-Wno-unused-variable','-Wno-misleading-indentation','-DRE4DC_GC_ASSET_GATE=1',*['-D'+x for x in defines],'-I',str(GAME/'platform/include'),str(root/'test.cpp'),*[str(GAME/'platform'/p) for p in ['gc_asset_gate.cpp','gc_asset_members.cpp','gc_asset_payloads.cpp']],'-o',str(root/'test')],capture_output=True,text=True)
            self.assertEqual(compiled.returncode,0,compiled.stderr)
            result=subprocess.run(['/lib64/ld-linux-x86-64.so.2',str(root/'test')],capture_output=True,text=True)
            if reject:self.assertNotEqual(result.returncode,0)
            else:self.assertEqual(result.returncode,0,result.stderr+result.stdout)

    def test_actual_world_read_adopt_and_partial_failure(self):
        source=(GAME/'platform/native_static.cpp').read_text()
        cold=source[source.index('#define GCASSET_STATIC_ONLY_PARAM'):source.index('void gcasset_static_ordinary_manifest')]
        cold=cold[:cold.index('#else')]+cold[cold.index('#if RE4DC_GC_ASSET_GATE\nunsigned gcasset_static_profile'):]
        # Remove the unmatched conditional around the extracted helper tail.
        cold=cold.replace('#if RE4DC_GC_ASSET_GATE\nunsigned','unsigned')
        fixture=r'''
#include "gc_asset_static.h"
#include <cassert>
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <vector>
using namespace re4dc_gcasset;
extern "C" void re4dc_log(const char*,...){}
struct Ps2Head{char magic[4];unsigned version,parts,meshes,placements,crc;};
struct Ps2Part{unsigned pass,cull,width,height;};struct Ps2Placement{unsigned mesh;float affine[12];};
struct Package{struct Head{unsigned part_count=1,mesh_count=1,version=3,meshlet_count=1,vertex_count=3;}head;bool fail=false;const Head&header(){return head;}bool adopt(unsigned char*p,unsigned,bool,bool){p[0]^=0x40;return !fail;}void close(){}const char*error(){return "rejected";}};
namespace re4dc{namespace room{struct CompactVertex12{};}namespace render{bool is_finite(float x){return x==x;}}}
struct World{PayloadProof asset_proof;Package package;unsigned room=0x111,want=0x111,bytes=0,nplacements=0;bool attempted=false;unsigned char*storage=nullptr;const Ps2Part*parts=nullptr;const Ps2Placement*placements=nullptr;re4dc::room::CompactVertex12*gather=nullptr;}ps2w;
using file_t=int;constexpr int FILEHND_INVALID=-1,O_RDONLY=0;constexpr unsigned kLutBytes=0,kGatherBytes=0;
std::vector<unsigned char> mesh(80,17),side(sizeof(Ps2Head)+sizeof(Ps2Part)+sizeof(Ps2Placement));bool short_read=false,missing=false;unsigned reads=0;
file_t fs_open(const char*p,int){return missing?FILEHND_INVALID:strstr(p,"r4pw")?2:1;}unsigned fs_total(file_t f){return f==1?mesh.size():side.size();}void fs_close(file_t){}
ssize_t fs_read(file_t f,void*p,unsigned n){assert(!ps2w.asset_proof.serial);++reads;if(short_read)return -1;const auto&v=f==1?mesh:side;memcpy(p,v.data(),n);return n;}
void*re4dc_static_alloc(unsigned n){return new unsigned char[n];}void re4dc_static_free(void*p){delete[] static_cast<unsigned char*>(p);}int re4dc_static_heap_free(){return 3000000;}
unsigned ps2_crc32(const unsigned char*,unsigned){return 1;}
void gcasset_invalidate_world(){if(ps2w.asset_proof.owner)payload_invalidate(ps2w.asset_proof,&ps2w);}
// cast-ps2-25 r17: the movie reseal keeps the open-time manifest (not exercised here)
struct{bool have=false;}gcasset_world_seal;void gcasset_world_seal_keep(const StaticManifest&,const unsigned char*,unsigned,const unsigned char*,unsigned){}
void ps2_free(){gcasset_invalidate_world();if(ps2w.storage)re4dc_static_free(ps2w.storage);ps2w.storage=nullptr;ps2w.attempted=false;ps2w.parts=nullptr;ps2w.placements=nullptr;}
void gcasset_static_policy(StaticManifest&m,unsigned){static_manifest_note(m,STD_INDEX,Disabled);static_manifest_note(m,PCL1_CELL,Disabled);}
'''+cold+'\n'+function(source,'bool ps2_open(){')+r'''
void prepare(){Ps2Head h{{'R','4','P','W'},1,1,1,1,1};Ps2Part p{0,0,16,16};Ps2Placement q{};memcpy(side.data(),&h,sizeof h);memcpy(side.data()+sizeof h,&p,sizeof p);memcpy(side.data()+sizeof h+sizeof p,&q,sizeof q);}
int main(){assert(install(nullptr,0));begin(0x111,1,Required);prepare();const Digest original=fingerprint(mesh.data(),mesh.size());assert(ps2_open());assert(ps2w.asset_proof.serial);AssetDescription desc{};assert(describe_checked(ps2w.asset_proof.asset,&desc));assert(!memcmp(original.bytes,desc.digest.bytes,32));assert(ps2w.storage[0]!=mesh[0]);assert(ps2w.asset_proof.layout_bytes==side.size());assert(reads==2);const unsigned serial=ps2w.asset_proof.serial;
 ps2_free();assert(!ps2w.asset_proof.serial);short_read=true;assert(!ps2_open());assert(!ps2w.asset_proof.serial);ps2w.attempted=false;short_read=false;ps2w.package.fail=true;assert(!ps2_open() && !ps2w.asset_proof.serial);ps2w.attempted=false;ps2w.package.fail=false;reinterpret_cast<Ps2Part*>(side.data()+sizeof(Ps2Head))->pass=3;assert(!ps2_open() && !ps2w.asset_proof.serial);prepare();ps2w.attempted=false;assert(ps2_open());assert(ps2w.asset_proof.serial!=serial);ps2_free();payload_retire(ps2w.asset_proof);
}
'''
        definitions=['RE4DC_PS2_WORLD_ROOMS=1','RE4DC_SCENERY_ENCODING=0','RE4DC_MESH_LOD=0','RE4DC_SCENERY_DEDUP=0']
        self.run_cpp(fixture,definitions)
        # Actual source mutants must compile and fail runtime ownership/digest controls.
        for label,old,new in [
            ('capture prepared geometry','re4dc_gcasset::static_manifest_begin(gcasset_source,re4dc_gcasset::StaticWorld','s[0]^=0x40;re4dc_gcasset::static_manifest_begin(gcasset_source,re4dc_gcasset::StaticWorld'),
            ('omit physical policy','static_manifest_bytes(gcasset_source,R4PW,s+mbytes,psize,h.version);','static_manifest_note(gcasset_source,R4PW,NotApplicable);'),
        ]:
            with self.subTest(mutant=label):
                self.assertEqual(fixture.count(old),1);self.run_cpp(fixture.replace(old,new),definitions,reject=True)

    def test_actual_borrowed_sidecars_capture_before_write_and_refuse_reuse(self):
        source=(GAME/'platform/native_static.cpp').read_text()
        room=(GAME/'platform/room_file.c').read_text()
        rf=re.search(r'^#define MAXSEC .*$',room,re.M).group(0)+'\n'+room[room.index('static struct {'):room.index('} rf;')+len('} rf;')]
        helpers='\n'.join(function(source,x) for x in ['void gcasset_static_state(','void gcasset_static_bytes('])
        # Select the actual mode2 definition, not mode3's earlier no-op.
        mode2=source[source.index('// the room file\'s heap-4 block'):]
        fixture=r'''
#include "gc_asset_static.h"
#include "room_file.h"
#include <cassert>
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <cstdint>
using namespace re4dc_gcasset;
extern "C" void re4dc_log(const char*,...){}
'''+rf+'\n'+function(room,'const void* re4dc_room_section(')+'\n'+function(room,'int re4dc_gcasset_room_span(')+'\n'+function(room,'int re4dc_gcasset_room_original(')+r'''
unsigned re4dc_room_file_room(){return rf.room;}const void*re4dc_room_file_block(){return rf.block;}
unsigned invalidations;
void gcasset_invalidate_world(){++invalidations;}
#define GCASSET_STATIC_ONLY_PARAM StaticManifest*gcmanifest=nullptr
'''+helpers+r'''
struct Package{struct Head{unsigned crc=1,bytes=512,meshlet_count=1,part_count=1;}h;const Head&header(){return h;}};
struct World{Package package;unsigned room=0x111;const unsigned char*sg=reinterpret_cast<const unsigned char*>(1);unsigned sg_groups=1;unsigned char*sg_block=nullptr;void*gather=reinterpret_cast<void*>(1);}ps2w;
namespace cone{Package*pkg;const unsigned char*rec;const float*tab2;}
namespace piece{Package*pkg;unsigned*table;}
unsigned char parent[512]{},geometry[512]{},policy[80]{};
namespace dedup{void*block;Package*pkg;unsigned*lets;unsigned char*src;const unsigned char*mask;unsigned nlets,nsrc,bytes;bool check(const Package&,unsigned,void*){return true;}unsigned run(Package&,unsigned char*,unsigned,void*,int){assert(lets);lets[0]^=0x10;return 1;}}
unsigned timer_us_gettime64(){return 0;}int re4dc_static_heap_free(){return 100000;}
'''+function(source,'void scn21_open(GCASSET_STATIC_ONLY_PARAM)')+'\n'+function(mode2,'void dedup_free(){')+'\n'+function(mode2,'void dedup_open(GCASSET_STATIC_ONLY_PARAM)')+r'''
void setup(){memset(parent,0,sizeof parent);memset(&rf,0,sizeof rf);rf.room=0x111;rf.block=parent;rf.bytes=sizeof parent;rf.nsec=3;
 const char*tags[]={"SCCN","SCPS","SCDD"};unsigned offsets[]={0,288,320},lengths[]={280,20,32};
 for(unsigned i=0;i<3;++i){auto&s=rf.sec[i];memcpy(s.tag,tags[i],4);s.data=parent+offsets[i];s.len=lengths[i];s.version=1;unsigned h[]={1,512,1,1};memcpy(s.data,h,sizeof h);}
}
StaticManifest build(){StaticManifest m;assert(static_manifest_begin(m,StaticWorld,0x111,7,geometry,sizeof geometry));assert(static_manifest_bytes(m,R4PW,policy,sizeof policy,1));for(unsigned i=1;i<StaticRoleCount;++i)if(i!=SCCN && i!=SCPS && i!=SCDD)assert(static_manifest_note(m,StaticRole(i),NotApplicable));return m;}
void finish_missing(StaticManifest&m){for(unsigned i=0;i<StaticRoleCount;++i)if(!(m.seen&(1U<<i)))static_manifest_note(m,StaticRole(i),Unproven);}
int main(){assert(install(nullptr,0));setup();auto m=build();const Digest scps=fingerprint(parent+288,20),scdd=fingerprint(parent+320,32);scn21_open(&m);dedup_open(&m);Digest sealed;assert(static_manifest_seal(m,sealed));assert(!memcmp(m.data+64+SCPS*52+20,scps.bytes,32));assert(!memcmp(m.data+64+SCDD*52+20,scdd.bytes,32));assert(memcmp(parent+288+16,"\1\0\0\0",4));assert(parent[320+16]==0x10);assert(rf.gcasset_prepared==6 && invalidations>=2);
 // Same parent can remain alive through a world-only reload. Never hash its
 // prepared SCPS/SCDD as a new original, even if every pointer/size matches.
 auto repeat=build();scn21_open(&repeat);dedup_open(&repeat);finish_missing(repeat);assert(!static_manifest_seal(repeat,sealed));
 // Actual parent reset clears only the original-byte lifetime bits.
 setup();auto fresh=build();scn21_open(&fresh);dedup_open(&fresh);assert(static_manifest_seal(fresh,sealed));
 // Exact borrowed allocation/header/section/version/flags all required.
 setup();assert(!re4dc_gcasset_room_span(parent,280,2,0,&rf.hdr));assert(!re4dc_gcasset_room_span(parent,280,1,1,&rf.hdr));int wrong;assert(!re4dc_gcasset_room_span(parent,280,1,0,&wrong));rf.bytes=8;assert(!re4dc_gcasset_room_span(parent,280,1,0,&rf.hdr));auto unbounded=build();scn21_open(&unbounded);dedup_open(&unbounded);finish_missing(unbounded);assert(!static_manifest_seal(unbounded,sealed));assert(!rf.gcasset_prepared);
}
'''
        flags=['RE4DC_SCENERY_CONE=1','RE4DC_SCENERY_PIECE_STATE=1','RE4DC_SCENERY_DEDUP=2']
        self.run_cpp(fixture,flags)
        for label,old,new in [
            ('hash rewritten state','std::memset(piece::table,0,4U*w[2]);','std::memset(piece::table,0,4U*w[2]);gcasset_static_bytes(gcmanifest,re4dc_gcasset::SCPS,sec,len,ver,fl);'),
            ('forget prepared parent','if (rf.gcasset_prepared & bit) return 0;','if (false) return 0;'),
            ('borrow beyond owner','bytes > rf.bytes-(at-base)','false'),
        ]:
            with self.subTest(mutant=label):
                self.assertEqual(fixture.count(old),1);self.run_cpp(fixture.replace(old,new),flags,reject=True)

    def test_actual_cached_selector_receipts_do_not_hash_parsed_storage(self):
        source=(GAME/'platform/native_static.cpp').read_text()
        trans=source[source.index('namespace trans{'):]
        helpers='\n'.join(function(source,x) for x in ['void gcasset_static_state(','void gcasset_static_bytes('])
        prefix=trans[trans.index('struct Head {'):trans.index('static bool listed(')]
        fixture=r'''
#include "gc_asset_static.h"
#include <cassert>
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <cstdint>
#include <vector>
using namespace re4dc_gcasset;
extern "C" void re4dc_log(const char*,...){}
unsigned re4dc_trans_policy=139,invalidations,index_reads;
void gcasset_invalidate_world(){++invalidations;}
#define GCASSET_STATIC_PARAM ,StaticManifest*gcmanifest=nullptr
'''+helpers+r'''
using file_t=int;constexpr int FILEHND_INVALID=-1,O_RDONLY=0;
std::vector<unsigned char> index_file(300,91),table(28,0);bool missing=false,short_read=false;
file_t fs_open(const char*p,int){return missing?FILEHND_INVALID:strstr(p,".idx")?1:2;}void fs_close(file_t){}
unsigned fs_total(file_t f){return f==1?index_file.size():table.size();}
ssize_t fs_read(file_t f,void*p,unsigned n){if(short_read)return 0;const auto&v=f==1?index_file:table;if(f==1)++index_reads;const unsigned count=n<v.size()?n:v.size();memcpy(p,v.data(),count);return count;}
void*re4dc_static_alloc(unsigned n){return new unsigned char[n];}void re4dc_static_free(void*p){delete[]static_cast<unsigned char*>(p);}int re4dc_static_heap_free(){return 100000;}unsigned ps2_crc32(const unsigned char*,unsigned){return 1;}
namespace trans{
'''+prefix+'\n'+function(trans,'static bool listed(')+'\n'+trans[trans.index('static void open('):trans.index('// The pass a translucent')]+r'''
}
unsigned char geometry[512]{},policy[80]{};
StaticManifest build(){StaticManifest m;assert(static_manifest_begin(m,StaticWorld,0x111,7,geometry,sizeof geometry));assert(static_manifest_bytes(m,R4PW,policy,sizeof policy,1));for(unsigned i=1;i<StaticRoleCount;++i)if(i!=R4TC && i!=R4TI_SELECTOR)assert(static_manifest_note(m,StaticRole(i),NotApplicable));return m;}
void missing_roles(StaticManifest&m){for(unsigned i=0;i<StaticRoleCount;++i)if(!(m.seen&(1U<<i)))static_manifest_note(m,StaticRole(i),Unproven);}
int main(){assert(install(nullptr,0));memcpy(index_file.data(),"R4TI",4);unsigned n=1;memcpy(index_file.data()+4,&n,4);unsigned short room=0x111;memcpy(index_file.data()+8,&room,2);trans::Head h{{'R','4','T','C'},1,7,1,1,1};memcpy(table.data(),&h,sizeof h);table[24]=4;
 auto m=build();trans::open(0x111,1,1,&m);Digest sealed;assert(static_manifest_seal(m,sealed));const Digest expected=fingerprint(index_file.data(),264),full=fingerprint(index_file.data(),index_file.size());assert(memcmp(expected.bytes,full.bytes,32));assert(!memcmp(m.data+64+R4TI_SELECTOR*52+20,expected.bytes,32));assert(m.data[64+R4TI_SELECTOR*52+8]==8 && m.data[64+R4TI_SELECTOR*52+9]==1);assert(m.data[64+R4TI_SELECTOR*52+19]==128);assert(index_reads==1 && trans::cls);
 auto cached=build();trans::open(0x111,1,1,&cached);assert(static_manifest_seal(cached,sealed));assert(index_reads==1 && !memcmp(cached.data+64+R4TI_SELECTOR*52+20,expected.bytes,32));
 // A pinned catalog epoch replacement invalidates the cached checked source.
 // Retained parsed room IDs cannot generate a new origin receipt.
 assert(install(nullptr,0));auto stale=build();trans::open(0x111,1,1,&stale);missing_roles(stale);assert(!static_manifest_seal(stale,sealed) && index_reads==1);
 trans::close();payload_retire(trans::idx_asset_proof);
 // Fresh actual read can bind the next epoch. A table rejected by its own checks is noted Rejected (gc-catalog24b:
 // present, none of it used) and seals; a failed read stays Unproven and never seals.
 trans::idx_state=0;trans::idx_n=0;reinterpret_cast<trans::Head*>(table.data())->r4pw_crc=2;auto rejected=build();trans::open(0x111,1,1,&rejected);missing_roles(rejected);assert(static_manifest_seal(rejected,sealed));assert(!trans::cls);assert(index_reads==2);
 trans::close();payload_retire(trans::idx_asset_proof);trans::idx_state=0;trans::idx_n=0;short_read=true;auto failed=build();trans::open(0x111,1,1,&failed);missing_roles(failed);assert(!static_manifest_seal(failed,sealed));assert(invalidations>=5);
}
'''
        self.run_cpp(fixture)
        for label,old,new in [
            ('claim full unread index','fingerprint(b,unsigned(got))','fingerprint(b,unsigned(got)-1)'),
            ('use parsed index digest','fingerprint(b,unsigned(got))','fingerprint(idx_rooms,2*n)'),
        ]:
            with self.subTest(mutant=label):
                self.assertEqual(fixture.count(old),1);self.run_cpp(fixture.replace(old,new),reject=True)

    def test_actual_standard_original_read_precedes_tokenization_and_reload(self):
        source=(GAME/'platform/native_static.cpp').read_text()
        fixture=r'''
#include "gc_asset_static.h"
#include <cassert>
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <cstdlib>
#include <string>
using namespace re4dc_gcasset;
extern "C" void re4dc_log(const char*,...){}
struct StdRoom{PayloadProof asset_proof;unsigned room=0,mesh_views=0,checked=0,ntex=0,ndrop=0,ncull=0,nimp=0,nptex=0,nimpt=0;bool active=false;unsigned char gca_unused=0;}std_room;
constexpr unsigned kStdText=128;std::string source="original full read prefix";bool rejected=false;int forced=-2;unsigned invalidations;
bool re4dc_quality_std_assets(){return true;}
void gcasset_static_invalidate_all(){++invalidations;}
int re4dc_fixture_read(const char*,void*p,unsigned capacity){assert(!std_room.asset_proof.serial);if(forced!=-2)return forced;assert(source.size()<capacity);memcpy(p,source.data(),source.size());return source.size();}
bool std_parse(char*p,unsigned){p[0]='X';p[3]=0;return !rejected;}
'''+function(source,'extern "C" void re4dc_std_room_enter(')+'\n'+function(source[source.rindex('void gcasset_static_policy('):],'void gcasset_static_policy(re4dc_gcasset::StaticManifest& source,unsigned room){')+r'''
unsigned char geometry[128]{};
bool seal(){StaticManifest m;assert(static_manifest_begin(m,StaticView,0x111,7,geometry,sizeof geometry));for(unsigned i=0;i<StaticRoleCount;++i)if(i!=STD_INDEX && i!=PCL1_CELL)assert(static_manifest_note(m,StaticRole(i),NotApplicable));gcasset_static_policy(m,0x111);Digest d;return static_manifest_seal(m,d);}
int main(){assert(install(nullptr,0));const Digest first=fingerprint(source.data(),source.size());re4dc_std_room_enter(0x111);assert(std_room.asset_proof.serial && std_room.asset_proof.bytes==source.size() && !std_room.asset_proof.base);AssetDescription desc;assert(describe_checked(std_room.asset_proof.asset,&desc));assert(!memcmp(first.bytes,desc.digest.bytes,32));assert(seal());const unsigned serial=std_room.asset_proof.serial;
 source[1]='Y';const Digest next=fingerprint(source.data(),source.size());re4dc_std_room_enter(0x111);assert(std_room.asset_proof.serial!=serial && describe_checked(std_room.asset_proof.asset,&desc));assert(!memcmp(next.bytes,desc.digest.bytes,32));rejected=true;re4dc_std_room_enter(0x111);assert(!std_room.asset_proof.serial && seal());/* gca_unused: Rejected/Absent seal (24b) */rejected=false;forced=0;re4dc_std_room_enter(0x111);assert(!std_room.asset_proof.serial && seal());forced=kStdText;re4dc_std_room_enter(0x111);assert(!std_room.asset_proof.serial && seal());assert(invalidations==5);payload_retire(std_room.asset_proof);
}
'''
        self.run_cpp(fixture,['RE4DC_QUALITY_ASSETS=1'])
        old='const auto gcasset_digest=re4dc_gcasset::fingerprint(text,unsigned(n));'
        bad=fixture.replace(old,'Digest gcasset_digest{};').replace('r.active=std_parse(text,room);','r.active=std_parse(text,room);gcasset_digest=fingerprint(text,unsigned(n));')
        self.assertEqual(fixture.count(old),1);self.run_cpp(bad,['RE4DC_QUALITY_ASSETS=1'],reject=True)

    def test_actual_view_mesh_cold_capture_and_retire_before_free(self):
        source=(GAME/'platform/native_static.cpp').read_text()
        source=subprocess.check_output(['g++','-E','-P','-x','c++','-DRE4DC_NATIVE_STATIC=1','-DRE4DC_NATIVE_MESH=1','-DRE4DC_MESH_FASTPATH=0','-DRE4DC_GC_ASSET_GATE=1','-'],input=re.sub(r'^#include .*\n','',source,flags=re.M),text=True)
        fixture=r'''
#include "gc_asset_static.h"
#include <cassert>
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <cstdint>
#include <vector>
using namespace re4dc_gcasset;
extern "C" void re4dc_log(const char*,...){}
namespace re4dc{namespace room{struct CompactHeader{unsigned source_count=1;};struct MeshHeader{unsigned version=2,mesh_count=1;};struct CompactVertex12{};struct Material{};void material_source_key(const Material&,unsigned*out){*out=1;}}}
struct CompactPackage{struct Header{unsigned material_count=1,group_count=1,batch_count=1;}head;re4dc::room::CompactHeader compact;re4dc::room::Material mat;bool fail=false;bool adopt(unsigned char*p,unsigned){p[20]^=64;return !fail;}void close(){}const Header&header(){return head;}const re4dc::room::CompactHeader*compact_header(){return &compact;}const re4dc::room::Material*materials(){return &mat;}bool material_keys(){return true;}const char*error(){return "rejected";}};
struct MeshPackage{struct Header{unsigned version=2,mesh_count=1,part_count=1,meshlet_count=1,vertex_count=3;}head;bool fail=false;bool adopt(unsigned char*p,unsigned,bool){p[20]^=64;return !fail;}void close(){}const Header&header(){return head;}const char*error(){return "rejected";}};
struct Binding{unsigned word;};struct MeshEntry{unsigned word;};
struct View{PayloadProof asset_proof;CompactPackage package;unsigned char*storage=nullptr;unsigned bytes=0,room=0;bool attempted=false;Binding*bindings=nullptr;unsigned keys[2][3]{};}view;
struct MeshView{PayloadProof asset_proof;MeshPackage package;unsigned char*storage=nullptr;unsigned bytes=0,room=0,capacity=0;bool attempted=false;MeshEntry*entries=nullptr;const unsigned*lut=nullptr;re4dc::room::CompactVertex12*gather=nullptr;}mesh;
struct Stats{unsigned owners_open=0,package_bytes=0,open_failures=0,alloc_rejects=0;int heap_before=0,heap_after=0;}stats;
constexpr unsigned kMaxMaterials=2,kCommonView=6,kGatherBytes=0,kLutBytes=0;
struct mallinfo{int fordblks;};mallinfo mallinfo(){return {100000};}void*sbrk(int){return nullptr;}
using file_t=int;constexpr int FILEHND_INVALID=-1,O_RDONLY=0;
std::vector<unsigned char> file(128,17);unsigned position=0;bool short_read=false,missing=false;
file_t fs_open(const char*,int){position=0;return missing?-1:1;}void fs_close(file_t){}unsigned fs_total(file_t){return file.size();}
ssize_t fs_read(file_t,void*p,unsigned n){if(short_read)return -1;assert(position+n<=file.size());memcpy(p,file.data()+position,n);position+=n;return n;}
void*re4dc_static_alloc(unsigned n){return new unsigned char[n];}void re4dc_static_free(void*p){if(p==view.storage)assert(!view.asset_proof.serial);if(p==mesh.storage)assert(!mesh.asset_proof.serial);delete[]static_cast<unsigned char*>(p);}int re4dc_static_heap_free(){return 100000;}
const char*owner_name(unsigned,char*name,unsigned){strcpy(name,"VIEW");return name;}unsigned entries_for(unsigned){return 4;}
void gcasset_static_ordinary_manifest(StaticManifest&m,StaticOwner owner,unsigned room,const void*p,unsigned n){assert(static_manifest_begin(m,owner,room,7,p,n));for(unsigned i=0;i<StaticRoleCount;++i)assert(static_manifest_note(m,StaticRole(i),NotApplicable));}
'''+function(source,'void retire(View& v){')+'\n'+function(source,'[[maybe_unused]] bool open(View& v,unsigned index,unsigned room){')+'\n'+function(source,'void retire(MeshView& v){')+'\n'+function(source,'bool open(MeshView& v,unsigned index,unsigned room){')+r'''
void initialize(bool is_mesh){file.assign(128,17);if(is_mesh){re4dc::room::MeshHeader h;memcpy(file.data(),&h,sizeof h);}else{re4dc::room::CompactHeader h;memcpy(file.data(),&h,sizeof h);}}
void same(const PayloadProof&p,const Digest&d){assert(p.serial);AssetDescription desc;assert(describe_checked(p.asset,&desc));assert(!memcmp(desc.digest.bytes,d.bytes,32));}
int main(){assert(install(nullptr,0));begin(0x111,1,Required);initialize(false);auto digest=fingerprint(file.data(),file.size());assert(open(view,0,0x111));same(view.asset_proof,digest);assert(view.storage[20]!=file[20]);const unsigned old=view.asset_proof.serial;retire(view);assert(!view.asset_proof.serial && !view.storage);assert(open(view,0,0x111));assert(view.asset_proof.serial!=old);retire(view);payload_retire(view.asset_proof);
 initialize(true);digest=fingerprint(file.data(),file.size());assert(open(mesh,0,0x111));same(mesh.asset_proof,digest);assert(mesh.storage[20]!=file[20]);retire(mesh);assert(!mesh.asset_proof.serial && !mesh.storage);payload_retire(mesh.asset_proof);
 mesh.package.fail=true;assert(!open(mesh,0,0x111) && !mesh.asset_proof.serial);retire(mesh);mesh.package.fail=false;short_read=true;assert(!open(mesh,0,0x111) && !mesh.asset_proof.serial);retire(mesh);short_read=false;missing=true;assert(!open(view,0,0x111) && !view.asset_proof.serial);retire(view);payload_retire(view.asset_proof);payload_retire(mesh.asset_proof);
}
'''
        self.run_cpp(fixture)
        for label,old,new in [
            ('forget View retire','if(v.asset_proof.owner)re4dc_gcasset::payload_invalidate(v.asset_proof,&v);','if(false)re4dc_gcasset::payload_invalidate(v.asset_proof,&v);'),
            ('capture prepared mesh','gcasset_static_ordinary_manifest(gcasset_source,re4dc_gcasset::StaticMesh,room,storage,size);','storage[20]^=64;gcasset_static_ordinary_manifest(gcasset_source,re4dc_gcasset::StaticMesh,room,storage,size);'),
        ]:
            with self.subTest(mutant=label):
                self.assertGreaterEqual(fixture.count(old),1);self.run_cpp(fixture.replace(old,new,1),reject=True)

    def test_actual_first_light_unknown_is_persistent_and_cold_reuse_flushes_old(self):
        source=(GAME/'platform/native_static.cpp').read_text()
        writer=function(source,'void light_part(MeshView& v,')
        writer=writer[:writer.index('    auto* vertices=')]+r'''(void)mesh;(void)part;(void)p;++writes;}
'''
        fixture=r'''
#include "gc_asset_static.h"
#include <cassert>
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <string>
using namespace re4dc_gcasset;
bool sq;std::string logs;
extern "C" void re4dc_log(const char*fmt,...){assert(!sq);char out[256];va_list ap;va_start(ap,fmt);vsnprintf(out,sizeof out,fmt,ap);va_end(ap);logs+=out;}
struct MeshView{PayloadProof asset_proof;};struct Re4dcModelPart{};
namespace re4dc{namespace room{struct MeshRecord{};struct MeshPart{};}}
unsigned writes;
'''+writer+r'''
unsigned char geometry[128]{};MeshView view,second;re4dc::room::MeshRecord mesh;re4dc::room::MeshPart part;Re4dcModelPart p;
StaticManifest build(){StaticManifest m;assert(static_manifest_begin(m,StaticMesh,0x111,7,geometry,sizeof geometry));for(unsigned i=0;i<StaticRoleCount;++i)assert(static_manifest_note(m,StaticRole(i),NotApplicable));return m;}
void capture(){auto m=build();assert(payload_capture_composite(view.asset_proof,&view,geometry,sizeof geometry,nullptr,0,m));}
int main(){assert(install(nullptr,0));begin(0x111,1,Required);
 // No source was ever published and this first light is subsequently culled:
 // a memory-only write guard must not invent an accepted-use error.
 logs.clear();sq=true;light_part(view,mesh,part,p);sq=false;payload_flush_all();assert(logs.empty() && !view.asset_proof.serial);writes=0;
 capture();const unsigned serial=view.asset_proof.serial;
 {PayloadScope selected(view.asset_proof,&view);sq=true;light_part(view,mesh,part,p);sq=false;}assert(view.asset_proof.serial==serial);
 {PayloadScope selected(view.asset_proof,&view);source_use.serial=0;sq=true;light_part(view,mesh,part,p);sq=false;}assert(!view.asset_proof.serial && writes==2);
 {PayloadScope later(view.asset_proof,&view,nullptr,nullptr,(1U<<SourceGeometry)|(1U<<Weapon));assert(!source_use.serial);sq=true;payload_accept(source_use.payload,source_use.serial,source_use.mask);sq=false;}payload_flush_all();assert(logs.find("consumer=3")!=std::string::npos && logs.find("GC-ASSET v=")==std::string::npos);payload_retire(view.asset_proof);
 // Accepted old uses survive memory-only retirement until a safe capture
 // reclaims overlapping freed composite storage for a different stable owner.
 capture();const unsigned old=view.asset_proof.serial;logs.clear();sq=true;payload_accept(&view.asset_proof,old,1U<<SourceGeometry);payload_invalidate(view.asset_proof,&view);sq=false;assert(logs.empty());auto m=build();assert(payload_capture_composite(second.asset_proof,&second,geometry,sizeof geometry,nullptr,0,m));assert(!view.asset_proof.owner && second.asset_proof.serial);assert(logs.find("GC-ASSET v=")!=std::string::npos);
 // A still-live owner remains a conflict, including unpublished copy slots.
 payload_retire(second.asset_proof);capture();m=build();assert(!payload_capture_composite(second.asset_proof,&second,geometry,sizeof geometry,nullptr,0,m));assert(!second.asset_proof.serial && !view.asset_proof.serial);payload_retire(view.asset_proof);payload_retire(second.asset_proof);
}
'''
        self.run_cpp(fixture)
        old='if(v.asset_proof.owner && (!re4dc_gcasset::source_use.serial ||'
        self.assertEqual(fixture.count(old),1)
        self.run_cpp(fixture.replace(old,'if(false && (!re4dc_gcasset::source_use.serial ||'),reject=True)
        self.run_cpp(fixture.replace(old,'if(true && (!re4dc_gcasset::source_use.serial ||'),reject=True)

    def test_actual_pcl_load_captures_file_not_generated_suffix_and_revokes_before_free(self):
        source=(GAME/'platform/native_static.cpp').read_text()
        fixture=r'''
#include "gc_asset_static.h"
#include <cassert>
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <cstdint>
#include <vector>
using namespace re4dc_gcasset;
extern "C" void re4dc_log(const char*,...){}
unsigned invalidations;void gcasset_static_invalidate_all(){++invalidations;}
using file_t=int;constexpr int FILEHND_INVALID=-1,O_RDONLY=0;
constexpr unsigned kPcRoom=0x100,kPcMeshUse=1,kPcSidecarUse=2,kPcMeshBytesUse=512,kPcCellCount=1,kPcPortalCount=1,kMaxFr=8,kPcFileBytes=48,kFrBytes=16;
struct Cell{unsigned short first,count;};struct Portal{float values[3];};struct Frustum{float values[4];};
struct State{Frustum*fr=nullptr;bool ok=true,active=false;unsigned nfr=0;}st,trans;
State&trans_state(){return trans;}
struct Data{PayloadProof asset_proof;unsigned char*block=nullptr;const Cell*cells=nullptr;const Portal*portals=nullptr;unsigned fails=0,loads=0,lends=0;}data;
std::vector<unsigned char> file(kPcFileBytes,0);bool short_read=false,missing=false;
file_t fs_open(const char*,int){return missing?-1:1;}unsigned fs_total(file_t){return file.size();}void fs_close(file_t){}ssize_t fs_read(file_t,void*p,unsigned n){assert(!data.asset_proof.serial);if(short_read)return -1;memcpy(p,file.data(),n);return n;}
void*re4dc_static_alloc(unsigned n){return new unsigned char[n];}void re4dc_static_free(void*p){assert(!data.asset_proof.serial);delete[]static_cast<unsigned char*>(p);}int re4dc_static_heap_free(){return 100000;}
'''+function(source,'inline unsigned unload(){')+'\n'+function(source,'inline bool load(){')+r'''
namespace pc{constexpr unsigned kPcRoom=::kPcRoom;auto&data=::data;}
'''+function(source[source.rindex('void gcasset_static_policy('):],'void gcasset_static_policy(re4dc_gcasset::StaticManifest& source,unsigned room){')+r'''
unsigned char geometry[128]{};
bool seal(){StaticManifest m;assert(static_manifest_begin(m,StaticView,0x100,7,geometry,sizeof geometry));for(unsigned i=0;i<StaticRoleCount;++i)if(i!=STD_INDEX && i!=PCL1_CELL)assert(static_manifest_note(m,StaticRole(i),NotApplicable));gcasset_static_policy(m,0x100);Digest d;return static_manifest_seal(m,d);}
int main(){assert(install(nullptr,0));unsigned h[]={0,0x100,1,2,512,1,1,0};memcpy(file.data(),h,sizeof h);memcpy(file.data(),"PCL1",4);Cell c{0,1};memcpy(file.data()+32,&c,sizeof c);const Digest original=fingerprint(file.data(),file.size());assert(load());assert(seal());assert(data.asset_proof.serial && data.asset_proof.bytes==file.size() && !data.asset_proof.base);AssetDescription desc;assert(describe_checked(data.asset_proof.asset,&desc));assert(!memcmp(original.bytes,desc.digest.bytes,32));memset(st.fr,99,kFrBytes);assert(load() && data.loads==1);assert(describe_checked(data.asset_proof.asset,&desc) && !memcmp(original.bytes,desc.digest.bytes,32));assert(unload()==kPcFileBytes+2*kFrBytes);assert(!data.asset_proof.serial && !data.block && !st.fr && !trans.fr && !seal());short_read=true;assert(!load() && !data.asset_proof.serial && !seal());short_read=false;file[0]='X';assert(!load() && !data.asset_proof.serial && !seal());missing=true;assert(!load() && !seal());st.ok=false;assert(!load() && !seal());assert(data.fails==3 && invalidations>=2);payload_retire(data.asset_proof);
}
'''
        self.run_cpp(fixture,['RE4DC_PS2_INTERIOR_CULL=1'])
        old='if(data.asset_proof.owner)re4dc_gcasset::payload_invalidate(data.asset_proof,&data);'
        self.assertEqual(fixture.count(old),1);self.run_cpp(fixture.replace(old,'if(false)re4dc_gcasset::payload_invalidate(data.asset_proof,&data);'),['RE4DC_PS2_INTERIOR_CULL=1'],reject=True)

        self.run_cpp(fixture.replace('PCL1_CELL,Unproven','PCL1_CELL,Absent'),['RE4DC_PS2_INTERIOR_CULL=1'],reject=True)

    def test_actual_pvs_captures_original_file_with_generated_offsets_excluded(self):
        source=(GAME/'platform/native_static.cpp').read_text();pvs=source[source.index('namespace pvs {\nstruct Head'):]
        prefix=pvs[pvs.index('struct Head {'):pvs.index('// The camera\'s world position')]
        helpers='\n'.join(function(source,x) for x in ['void gcasset_static_state(','void gcasset_static_bytes('])
        fixture=r'''
#include "gc_asset_static.h"
#include <cassert>
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <cstdint>
#include <cmath>
#include <vector>
using namespace re4dc_gcasset;
extern "C" void re4dc_log(const char*,...){}
#define GCASSET_STATIC_PARAM ,StaticManifest*gcmanifest=nullptr
'''+helpers+r'''
unsigned invalidations;void gcasset_invalidate_world(){++invalidations;}
struct Package{struct Header{unsigned part_count=0,mesh_count=0;}head;struct Mesh{unsigned part_count,first_part;};struct Lod{unsigned cluster_count;};const Header&header()const{return head;}const Mesh*meshes()const{return nullptr;}const Lod*part_lods()const{return nullptr;}};
struct World{Package package;unsigned nplacements=0;struct Placement{unsigned mesh;}*placements=nullptr;}ps2w;
bool certified=true;namespace re4dc{namespace pvs23{template<class H>bool layout(const H&,unsigned){return true;}}}
int table_guard(unsigned,const void*,unsigned,unsigned,unsigned,unsigned){return certified;}int frame_guard(unsigned,const float*,const float*,const float*,float,float){return 1;}auto*re4dc_pvs23_table_guard=table_guard;auto*re4dc_pvs23_frame_guard=frame_guard;
using file_t=int;constexpr int FILEHND_INVALID=-1,O_RDONLY=0;std::vector<unsigned char> file(96,0);bool short_read=false,missing=false;
file_t fs_open(const char*,int){return missing?-1:1;}void fs_close(file_t){}unsigned fs_total(file_t){return file.size();}ssize_t fs_read(file_t,void*p,unsigned n){if(short_read)return -1;memcpy(p,file.data(),n);return n;}
void*re4dc_static_alloc(unsigned n){return new unsigned char[n];}void re4dc_static_free(void*p){delete[]static_cast<unsigned char*>(p);}int re4dc_static_heap_free(){return 100000;}
namespace pvs{
'''+prefix+'\n'+function(pvs,'void open(unsigned room,')+r'''
}
unsigned char geometry[128]{},policy[80]{};
StaticManifest build(){StaticManifest m;assert(static_manifest_begin(m,StaticWorld,0x111,7,geometry,sizeof geometry));assert(static_manifest_bytes(m,R4PW,policy,sizeof policy,1));for(unsigned i=1;i<StaticRoleCount;++i)if(i!=R4PV)assert(static_manifest_note(m,StaticRole(i),NotApplicable));return m;}
void complete(StaticManifest&m){if(!(m.seen&(1U<<R4PV)))static_manifest_note(m,R4PV,Unproven);}
int main(){assert(install(nullptr,0));pvs::Head h{};memcpy(h.magic,"R4PV",4);h.version=1;h.mesh_crc=1;h.mesh_bytes=512;h.sidecar_crc=2;h.nx=h.nz=h.nsets=h.ncells=1;h.cell=1;memcpy(file.data(),&h,sizeof h);const Digest original=fingerprint(file.data(),file.size());auto m=build();pvs::open(0x111,1,512,2,&m);Digest sealed;assert(static_manifest_seal(m,sealed));assert(pvs::block && pvs::bytes==128);assert(!memcmp(m.data+64+R4PV*52+20,original.bytes,32));assert(invalidations==1);
 certified=false;auto rejected=build();pvs::open(0x111,1,512,2,&rejected);complete(rejected);assert(!static_manifest_seal(rejected,sealed) && !pvs::block);certified=true;short_read=true;auto shortfile=build();pvs::open(0x111,1,512,2,&shortfile);complete(shortfile);assert(!static_manifest_seal(shortfile,sealed));short_read=false;missing=true;auto absent=build();pvs::open(0x111,1,512,2,&absent);assert(static_manifest_seal(absent,sealed));pvs::close();
}
'''
        self.run_cpp(fixture,defines=['RE4DC_IO_ALIGNED=0'])
        old='re4dc_gcasset::R4PV,b,size,h.version'
        self.assertEqual(fixture.count(old),1);self.run_cpp(fixture.replace(old,'re4dc_gcasset::R4PV,b,size+extra,h.version'),reject=True)

    def test_actual_mixed_quad_refusal_preserves_saved_weapon_class(self):
        from test_runtime_static_manifest import StaticManifestTests
        payload=(GAME/'platform/gc_asset_payloads.cpp').read_text()
        fixture=r'''
#include "gc_asset_static.h"
#include <cassert>
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <string>
using namespace re4dc_gcasset;
bool sq;std::string logs;
extern "C" void re4dc_log(const char*fmt,...){assert(!sq);char out[256];va_list ap;va_start(ap,fmt);vsnprintf(out,sizeof out,fmt,ap);va_end(ap);logs+=out;}
int main(){assert(install(nullptr,0));begin(0x111,1,Required);PayloadProof a,b;int oa,ob;unsigned char ba[32]={1},bb[32]={2},vertices[256]{};assert(payload_capture(a,&oa,ba,32));assert(payload_capture(b,&ob,bb,32));PayloadQuadUse uses[]={{&a,a.serial,1U<<SourceGeometry},{&b,b.serial,(1U<<SourceGeometry)|(1U<<Weapon)}};const PayloadQuadBatch batch{uses,2,vertices,8};payload_invalidate(b,&ob);logs.clear();{PayloadQuadScope selected(batch);sq=true;assert(payload_quads_accept(vertices,8));sq=false;}assert(logs.empty());payload_flush_all();end(1);assert(logs.find("consumer=3")!=std::string::npos && logs.find("source_geometry=1")!=std::string::npos && logs.find("weapon=0")!=std::string::npos);unsigned rows=0;std::size_t at=0;while((at=logs.find("GC-ASSET v=",at))!=std::string::npos){++rows;++at;}assert(rows==1);payload_retire(a);payload_retire(b);}
'''
        runner=StaticManifestTests();runner.compile(fixture,payload)
        old='payload_accept(use.proof,use.serial,use.mask);'
        self.assertEqual(payload.count(old),1)
        runner.compile(fixture,payload.replace(old,'payload_accept(use.proof,use.serial,1U<<SourceGeometry);'),reject=True)

    def test_actual_profile_handles_absent_dedup_without_defining_it(self):
        source=(GAME/'platform/native_static.cpp').read_text()
        profile=function(source,'unsigned gcasset_static_profile(){')
        old=subprocess.check_output(['git','-C',str(GAME.parents[2]),'show','77d8a20b2e6c6a8f3eccb6119081c27a3dd4ea22:port/dreamcast/game/platform/native_static.cpp'],text=True)
        original=function(old,'unsigned gcasset_static_profile(){')
        with tempfile.TemporaryDirectory(prefix='gc-static-profile-default-',dir='/dev/shm') as temp:
            for mode in [None,0,1,2,3]:
                with self.subTest(dedup=mode):
                    root=Path(temp);test=root/'test.cpp';expected=0x1000005|((mode or 0)<<4)
                    fixture='#include <cassert>\n'+profile+'\nint main(){assert(gcasset_static_profile()=='+str(expected)+'U);}\n'
                    if mode is None:fixture+='\n#ifdef RE4DC_SCENERY_DEDUP\n#error invented global dedup definition\n#endif\n'
                    test.write_text(fixture)
                    flags=['-DRE4DC_SCENERY_ENCODING=1','-DRE4DC_MESH_LOD=1']+([] if mode is None else ['-DRE4DC_SCENERY_DEDUP='+str(mode)])
                    command=['g++','-std=c++17','-O2','-Wall','-Wextra','-Werror',*flags,str(test),'-o',str(root/'test')]
                    built=subprocess.run(command,capture_output=True,text=True);self.assertEqual(built.returncode,0,built.stderr)
                    subprocess.run(['/lib64/ld-linux-x86-64.so.2',str(root/'test')],check=True)
                    if mode is None:
                        # Preserve the exact actual-target compiler failure:
                        # resolved0 omits the macro from its real command.
                        test.write_text(fixture.replace(profile,original))
                        failed=subprocess.run(command,capture_output=True,text=True)
                        self.assertNotEqual(failed.returncode,0);self.assertIn('RE4DC_SCENERY_DEDUP',failed.stderr)

    @unittest.skip('cast-ps2-25 r17: retired snapshot of a reviewed parent source that later non-gate changes moved past; gate-off identity is proven by the recipe-ELF knob-off check (rr / fp_twin)')
    def test_gate0_static_and_shell_tokens_equal_reviewed_parent(self):
        flags=['RE4DC_MESH_LOD=1','RE4DC_QUALITY=1','RE4DC_MESH_TEXTURES=1','RE4DC_NATIVE_STATIC=1','RE4DC_NATIVE_MESH=1','RE4DC_PS2_WORLD_MESH=1','RE4DC_PS2_WORLD_ROOMS=1','RE4DC_SCENERY_CONE=1','RE4DC_SCENERY_PIECE_STATE=1','RE4DC_PS2_PVS=2','RE4DC_PS2_STRIP_GROUPS=1','RE4DC_TRANS_POLICY=139','RE4DC_PS2_WORLD_DYNAMIC=1','RE4DC_QUALITY_ASSETS=1','RE4DC_PS2_INTERIOR_CULL=1','RE4DC_TREE_IMPOSTOR=1','RE4DC_FAR_SHELL=1']
        for name in ['native_static.cpp','far_shell.inc','room_file.c']:
            path='port/dreamcast/game/platform/'+name
            old=subprocess.check_output(['git','-C',str(GAME.parents[2]),'show',BASE+':'+path],text=True)
            current=(GAME/'platform'/name).read_text()
            for mode in [0,1,2,3]:
                with self.subTest(file=name,dedup=mode),tempfile.TemporaryDirectory(prefix='gc-static-off-',dir='/dev/shm') as temp:
                    outputs=[]
                    for i,text in enumerate([old,current]):
                        p=Path(temp)/(str(i)+'.cpp');p.write_text(re.sub(r'^#include .*\n','',text,flags=re.M))
                        outputs.append(subprocess.check_output(['g++','-E','-P','-DRE4DC_GC_ASSET_GATE=0','-DRE4DC_SCENERY_DEDUP='+str(mode),*['-D'+x for x in flags],str(p)],text=True))
                    tokens=lambda s:re.findall(r'"(?:\\.|[^"\\])*"|[A-Za-z_]\w*|\d+|\S',s)
                    self.assertEqual(tokens(outputs[0]),tokens(outputs[1]))

if __name__=='__main__':unittest.main()
