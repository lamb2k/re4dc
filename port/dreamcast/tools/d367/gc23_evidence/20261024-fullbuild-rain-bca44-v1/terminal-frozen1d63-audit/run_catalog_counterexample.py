#!/usr/bin/env python3
from pathlib import Path
import sys,subprocess,json,hashlib,resource
resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,256*1024*1024))
ROOT=Path('/dev/shm/gc-static-review1d63/source');GAME=ROOT/'port/dreamcast/game';OUT=Path(__file__).resolve().parent;RAM=Path('/dev/shm/gc-terminal-next1d63/catalog');RAM.mkdir(exist_ok=True)
sys.path.insert(0,str(ROOT/'port/dreamcast/tools/d367/gc_port23'));from test_runtime_hooks import function
s=(GAME/'platform/gc_asset_disc.cpp').read_text();reader=function(s,'unsigned disc_read(')
fixture=r'''
#include "gc_asset_gate.h"
#include "native_io.h"
#include <cassert>
#include <cstdio>
#include <cstdarg>
#include <cstring>
#include <string>
#include <vector>
#include <sys/types.h>
using namespace re4dc_gcasset;
std::string logs;std::vector<unsigned char> file(128+3*112);unsigned cursor,io_depth;constexpr int FILEHND_INVALID=-1;int disc_catalog=1;bool interleave,retire_during_read;CheckedAsset other;
extern "C" void re4dc_log(const char*fmt,...){char s[256];va_list a;va_start(a,fmt);vsnprintf(s,sizeof s,fmt,a);va_end(a);logs+=s;}
extern "C" void* re4dc_io_begin(){++io_depth;return &io_depth;}extern "C" void re4dc_io_end(void*p){assert(p==&io_depth&&io_depth);--io_depth;}
off_t fs_seek(int,off_t off,int){cursor=unsigned(off);if(interleave){interleave=false;AssetDescription d;assert(describe_checked(other,&d));assert(!strcmp(d.id,"b"));}return off;}
ssize_t fs_read(int,void*p,unsigned n){if(cursor+n>file.size())return 0;memcpy(p,file.data()+cursor,n);cursor+=n;if(retire_during_read){retire_during_read=false;retire_catalog();}return n;}
''' + reader + r'''
void word(unsigned at,unsigned value){memcpy(file.data()+at,&value,4);}
int main(){memcpy(file.data(),"GCIDX001",8);word(8,1);word(12,3);word(16,112);word(20,128);Digest d[3];for(unsigned i=0;i<3;++i){unsigned char data=17+i;d[i]=fingerprint(&data,1);auto*p=file.data()+128+i*112;memcpy(p,"geometry",9);p[16]='a'+i;memcpy(p+64,d[i].bytes,32);p[96]=i?PS2:GameCube;}
const auto whole=fingerprint(file.data(),file.size());assert(install_index(disc_read,nullptr,file.size(),whole));const auto a=bind_checked("geometry","a",d[0]);other=bind_checked("geometry","b",d[1]);assert(a.value&&other.value);AssetDescription desc;assert(describe_checked(a,&desc)&&desc.provenance==GameCube&&!strcmp(desc.id,"a"));
begin(0x111,1,Required);logs.clear();emitted_checked(SourceGeometry,a);end(1);assert(logs.find("provenance=gc")!=std::string::npos);
// A seeks row0; B's legitimate description seeks/reads row1; A then reads
// row2 using the shared handle. All rows parse; token A still points row0.
begin(0x112,2,Required);logs.clear();interleave=true;emitted_checked(SourceGeometry,a);end(2);assert(!interleave&&logs.find("GC-ASSET v=")==std::string::npos&&logs.find("errors=0")!=std::string::npos&&logs.find("source_geometry=1")!=std::string::npos);
// Retirement midway through a read is not revalidated by describe_checked.
retire_during_read=true;assert(describe_checked(a,&desc));assert(!checked_current(a));assert(!strcmp(desc.id,"a")&&desc.provenance==GameCube);assert(!io_depth);
}
'''
cpp=RAM/'fixture.cpp';exe=RAM/'fixture';cpp.write_text(fixture);(OUT/'actual-shared-catalog-cursor-counterexample.cpp').write_text(fixture)
q=subprocess.run(['g++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-DRE4DC_GC_ASSET_GATE=1','-I',str(GAME/'platform/include'),str(cpp),str(GAME/'platform/gc_asset_gate.cpp'),'-o',str(exe)],capture_output=True,text=True);assert q.returncode==0,q.stderr;q=subprocess.run(['/lib64/ld-linux-x86-64.so.2',str(exe)],capture_output=True,text=True);assert q.returncode==0,q.stderr
(OUT/'independent-catalog-counterexample.json').write_text(json.dumps({'source':'1d63cffe3a232c402418f2f2d919e7abae476957','scope':'actual disc_read and gate/index functions; mocked shared-handle fs provider; forced nested callback is deterministic two-reader schedule, not a demonstrated reachable target overlap','normal_GC_emission_control':'pass','interleaved_seek_read_suppresses_GC_as_different_PS2_row':'reproduced','inflight_describe_returns_true_after_retire':'reproduced','fixture_sha256':hashlib.sha256(fixture.encode()).hexdigest(),'runtime_source_edited':False},indent=2)+'\n');print('PASS actual shared-handle schedule: wrong PS2 row suppresses GC with errors0; in-flight describe returns after catalog retirement; target reachability remains separate')