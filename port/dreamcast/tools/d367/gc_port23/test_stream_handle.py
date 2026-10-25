"""Exercise the actual str_index_load and per-entry stream identity functions with faulting, owned file IO.

gc-catalog24b (coordinator 10-24 option a): the index load no longer hashes the
container; each entry is hashed at its first open (record + intro + loop groups)."""
from pathlib import Path
import subprocess,tempfile,json,hashlib,resource
root=Path(__file__).resolve().parents[3]
src=root/'game/platform/audio_aica.cpp'
s=src.read_text();function=s[s.index('bool str_index_load()'):s.index('\nAXVPBView* vpb_of',s.index('bool str_index_load()'))]
entry_start=s.index('re4dc_gcasset::Digest g_strEntDigest[kStrEntMax];')
entry_fn=s[entry_start:s.index('#endif\nbool str_index_load()')]
harness=r'''
#include <cassert>
#include <cstdint>
#include <cstring>
#include <cstdio>
#include <vector>
#include <algorithm>
#include <sys/types.h>
using u8=unsigned char;using u32=uint32_t;using file_t=int;
struct StrEnt {u32 sbb_ofs,rate,flags,nch,a_samples,b_samples,a_ofs,b_ofs;};
const u32 kStrMagic=0x12345678;
u8 storage[8192+32];u8* g_strCache=storage+4;StrEnt g_strEnt[255];u32 g_strEntN;file_t g_strFile=-1;u32 g_strCacheOfs;const int kStrEntMax_i=RE4DC_STR_ENT_MAX;
#define kStrEntMax kStrEntMax_i
std::vector<u8> disk,hashed;off_t pos,total_override=-2;int opens,closes,total_calls,bookmark_calls,zero_calls,restore_calls,published,failed;
bool open_fail,header_short,long_short,bookmark_fail,zero_fail,zero_wrong,restore_fail,restore_wrong,hash_short;
void re4dc_log(const char*,...){}
file_t fs_open(const char*,int){++opens;return open_fail?-1:7;}
int fs_close(file_t f){assert(f==7);++closes;return 0;}
off_t fs_total(file_t f){assert(f==7);++total_calls;return total_override==-2?off_t(disk.size()):total_override;}
off_t fs_seek(file_t f,off_t to,int whence){assert(f==7);if(whence==SEEK_CUR){++bookmark_calls;assert(to==0);return bookmark_fail?-1:pos;}assert(whence==SEEK_SET);if(to==0){++zero_calls;if(zero_fail)return -1;if(zero_wrong){pos=1;return 1;}}else{++restore_calls;if(restore_fail)return -1;if(restore_wrong){pos=to-1;return pos;}}pos=to;return pos;}
ssize_t fs_read(file_t f,void* target,unsigned bytes){assert(f==7);if((pos==0&&bytes==2048&&header_short)||(pos==2048&&bytes>512&&long_short))return 0;
 if(hash_short&&bytes<=512&&zero_calls)return 0;
 const size_t n=std::min<size_t>(bytes,pos>=off_t(disk.size())?0:disk.size()-pos);std::memcpy(target,disk.data()+pos,n);pos+=n;return n;}
namespace re4dc_gcasset {struct Digest {u8 bytes[32];};struct DigestStream{int x;};
 void digest_begin(DigestStream&){hashed.clear();}void digest_update(DigestStream&,const void* p,unsigned n){hashed.insert(hashed.end(),(const u8*)p,(const u8*)p+n);}
 Digest digest_finish(DigestStream&){Digest d{};d.bytes[0]=u8(hashed.size());return d;}
 void stream_source(const Digest&){++published;}void stream_source_failed(){++failed;}}
#define O_RDONLY 0
#if RE4DC_GC_ASSET_GATE
/*ENTRY_FUNCTIONS*/
#endif
/*ACTUAL_FUNCTION*/
void reset(unsigned count=2){disk.resize(8192);for(unsigned i=0;i<disk.size();++i)disk[i]=u8(i*13+3);std::memcpy(disk.data(),&kStrMagic,4);std::memcpy(disk.data()+4,&count,4);pos=0;total_override=-2;opens=closes=total_calls=bookmark_calls=zero_calls=restore_calls=published=failed=0;open_fail=header_short=long_short=bookmark_fail=zero_fail=zero_wrong=restore_fail=restore_wrong=hash_short=false;g_strFile=-1;hashed.clear();
#if RE4DC_GC_ASSET_GATE
 memset(g_strEntHashed,0,sizeof g_strEntHashed);
#endif
}
int main(){unsigned tests=0;
 std::vector<unsigned> counts{2u,63u,unsigned(RE4DC_STR_ENT_MAX)};
#if RE4DC_STR_ENT_MAX>63
 counts.push_back(70);
#endif
 for(unsigned count:counts){reset(count);assert(str_index_load());const off_t resume=(16+count*32+2047)/2048*2048;assert(opens==1&&closes==0&&g_strFile==7&&pos==resume);
#if RE4DC_GC_ASSET_GATE
 assert(hashed.empty()&&published==0&&failed==0&&total_calls==0&&bookmark_calls==0&&zero_calls==0&&restore_calls==0);
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
 // per-entry identity: record + intro groups + loop groups, hashed once, then republished
 {reset(1);g_strFile=7;StrEnt& e=g_strEnt[0];e={0,0,0,2,4096,2048,2048,6144};   // sbb,rate,flags,nch,a,b,a_ofs,b_ofs
  disk.resize(16384);for(unsigned i=0;i<disk.size();++i)disk[i]=u8(i*7+1);
  std::vector<u8> want((const u8*)&e,(const u8*)&e+sizeof e);
  want.insert(want.end(),disk.begin()+2048,disk.begin()+2048+4096);want.insert(want.end(),disk.begin()+6144,disk.begin()+6144+4096);
  gcasset_stream_entry(&e);assert(published==1&&failed==0&&hashed==want);
  ++tests;
  gcasset_stream_entry(&e);assert(published==2&&g_strEntHashed[0]==1);++tests;
  reset(1);g_strFile=7;g_strEnt[0]=e;g_strEnt[0].a_ofs=0x7fffff00;gcasset_stream_entry(&g_strEnt[0]);assert(failed==1&&published==0&&g_strEntHashed[0]==2);++tests;
  }
#endif
 std::printf("%u actual-function cases passed\n",tests);}
'''.replace('/*ACTUAL_FUNCTION*/',function).replace('/*ENTRY_FUNCTIONS*/',entry_fn)
assert len(harness)<40000
results=[]
with tempfile.TemporaryDirectory(prefix='gc-stream-handle-host-',dir='/dev/shm') as d:
 d=Path(d);p=d/'actual.cpp';p.write_text(harness)
 for gate in [0,1]:
  for ent in [63,255]:
   exe=d/f'test-{gate}-{ent}'
   cmd=['g++','-std=c++17','-O2','-Wall','-Wextra','-Werror',f'-DRE4DC_GC_ASSET_GATE={gate}',f'-DRE4DC_STR_ENT_MAX={ent}',str(p),'-o',str(exe)]
   subprocess.run(cmd,check=True,timeout=40)
   run=subprocess.run([str(exe)],capture_output=True,text=True,timeout=5)
   assert run.returncode==0,(gate,ent,run.stdout,run.stderr)
   results.append({'gate':gate,'entries':ent,'result':run.stdout.strip()})
print(json.dumps({'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'scope':'Host fake IO over actual function, no SDK or guest acceptance','cases':results},indent=2))
