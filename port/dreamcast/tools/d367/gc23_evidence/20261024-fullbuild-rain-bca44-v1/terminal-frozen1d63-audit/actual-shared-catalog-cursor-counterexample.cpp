
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
unsigned disc_read(void*,unsigned offset,void* destination,unsigned bytes){
    Re4dcIoScope io;
    if(disc_catalog==FILEHND_INVALID || fs_seek(disc_catalog,offset,SEEK_SET)!=off_t(offset))return 0;
    const ssize_t count=fs_read(disc_catalog,destination,bytes);return count<0?0:unsigned(count);
}
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
