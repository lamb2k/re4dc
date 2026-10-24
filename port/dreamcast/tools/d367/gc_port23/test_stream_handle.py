"""Exercise the actual str_index_load function with faulting, owned file IO."""
from pathlib import Path
import subprocess,tempfile,json,hashlib,resource
root=Path(__file__).resolve().parents[3]
src=root/'game/platform/audio_aica.cpp'
s=src.read_text();function=s[s.index('bool str_index_load()'):s.index('\nAXVPBView* vpb_of',s.index('bool str_index_load()'))]
harness=r'''
#include <cassert>
#include <cstdint>
#include <cstring>
#include <cstdio>
#include <vector>
#include <algorithm>
#include <sys/types.h>
using u8=unsigned char;using u32=uint32_t;using file_t=int;
struct StrEnt {u32 flags,sbb_ofs,rate,nch,a_samples,b_samples,pad0,pad1;};
const u32 kStrMagic=0x12345678,kStrEntMax=RE4DC_STR_ENT_MAX;
u8 storage[8192+32];u8* g_strCache=storage+4;StrEnt g_strEnt[255];u32 g_strEntN;file_t g_strFile=-1;
std::vector<u8> disk,hashed;off_t pos,total_override=-2;int opens,closes,total_calls,bookmark_calls,zero_calls,restore_calls,published,failed;
bool open_fail,header_short,long_short,bookmark_fail,zero_fail,restore_fail,hash_short;
void re4dc_log(const char*,...){}
file_t fs_open(const char*,int){++opens;return open_fail?-1:7;}
int fs_close(file_t f){assert(f==7);++closes;return 0;}
off_t fs_total(file_t f){assert(f==7);++total_calls;return total_override==-2?off_t(disk.size()):total_override;}
off_t fs_seek(file_t f,off_t to,int whence){assert(f==7);if(whence==SEEK_CUR){++bookmark_calls;assert(to==0);return bookmark_fail?-1:pos;}assert(whence==SEEK_SET);if(to==0){++zero_calls;if(zero_fail)return -1;}else{++restore_calls;if(restore_fail)return -1;}pos=to;return pos;}
ssize_t fs_read(file_t f,void* target,unsigned bytes){assert(f==7);if((pos==0&&bytes==2048&&header_short)||(pos==2048&&bytes>512&&long_short))return 0;
 if(hash_short&&bytes<=512&&zero_calls)return 0;
 const size_t n=std::min<size_t>(bytes,pos>=off_t(disk.size())?0:disk.size()-pos);std::memcpy(target,disk.data()+pos,n);pos+=n;return n;}
namespace re4dc_gcasset {struct Digest {u8 bytes[32];};bool fingerprint_read(Digest&,unsigned(*read)(void*,void*,unsigned),void* context,unsigned n){hashed.clear();while(n){u8 b[512];unsigned take=std::min(n,512u),got=read(context,b,take);if(got!=take)return false;hashed.insert(hashed.end(),b,b+take);n-=take;}return true;}void stream_source(const Digest&){++published;}void stream_source_failed(){++failed;}}
#define O_RDONLY 0
/*ACTUAL_FUNCTION*/
void reset(unsigned count=2){disk.resize(8192);for(unsigned i=0;i<disk.size();++i)disk[i]=u8(i*13+3);std::memcpy(disk.data(),&kStrMagic,4);std::memcpy(disk.data()+4,&count,4);pos=0;total_override=-2;opens=closes=total_calls=bookmark_calls=zero_calls=restore_calls=published=failed=0;open_fail=header_short=long_short=bookmark_fail=zero_fail=restore_fail=hash_short=false;g_strFile=-1;hashed.clear();}
int main(){unsigned tests=0;
 for(unsigned count: {2u,63u,unsigned(RE4DC_STR_ENT_MAX)}){reset(count);assert(str_index_load());const off_t resume=(16+count*32+2047)/2048*2048;assert(opens==1&&closes==0&&g_strFile==7&&pos==resume);
#if RE4DC_GC_ASSET_GATE
 assert(hashed==disk&&published==1&&failed==0&&total_calls==1&&bookmark_calls==1&&zero_calls==1&&restore_calls==1);
#else
 assert(hashed.empty()&&published==0&&failed==0&&total_calls==0&&bookmark_calls==0&&zero_calls==0&&restore_calls==0);
#endif
 ++tests;}
 reset();open_fail=true;assert(!str_index_load()&&opens==1&&closes==0);++tests;
 reset();header_short=true;assert(!str_index_load()&&closes==1&&g_strFile==-1);++tests;
 reset();disk[0]^=1;assert(!str_index_load()&&closes==1);++tests;
 reset(RE4DC_STR_ENT_MAX+1);assert(!str_index_load()&&closes==1);++tests;
#if RE4DC_STR_ENT_MAX>63
 reset(70);long_short=true;assert(!str_index_load()&&closes==1);++tests;
#endif
#if RE4DC_GC_ASSET_GATE
 for(off_t size:{off_t(-1),off_t(0),off_t(0x20000000)}){reset();total_override=size;assert(str_index_load()&&opens==1&&closes==0&&pos==2048&&published==0&&failed==1&&zero_calls==0&&restore_calls==1);++tests;}
 reset();bookmark_fail=true;assert(str_index_load()&&pos==2048&&opens==1&&closes==0&&zero_calls==0&&restore_calls==0&&failed==1);++tests;
 reset();zero_fail=true;assert(str_index_load()&&pos==2048&&opens==1&&closes==0&&failed==1&&restore_calls==1);++tests;
 reset();hash_short=true;assert(str_index_load()&&pos==2048&&opens==1&&closes==0&&failed==1&&restore_calls==1);++tests;
 reset();restore_fail=true;assert(!str_index_load()&&g_strFile==-1&&closes==1&&opens==1&&published==0&&failed==1);++tests;
#endif
 std::printf("%u actual-function cases passed\n",tests);}
'''.replace('/*ACTUAL_FUNCTION*/',function)
assert len(harness)<40000
results=[]
with tempfile.TemporaryDirectory(prefix='gc-stream-handle-host-',dir='/dev/shm') as d:
 d=Path(d);p=d/'actual.cpp';p.write_text(harness)
 for gate in [0,1]:
  for ent in [63,255]:
   exe=d/f'test-{gate}-{ent}'
   cmd=['g++','-std=c++17','-O2','-Wall','-Wextra','-Werror',f'-DRE4DC_GC_ASSET_GATE={gate}',f'-DRE4DC_STR_ENT_MAX={ent}',str(p),'-o',str(exe)]
   subprocess.run(cmd,check=True,timeout=40)
   run=subprocess.run([str(exe)],capture_output=True,text=True,check=True,timeout=5)
   results.append({'gate':gate,'entries':ent,'result':run.stdout.strip()})
print(json.dumps({'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'scope':'Host fake IO over actual function, no SDK or guest acceptance','cases':results},indent=2))
