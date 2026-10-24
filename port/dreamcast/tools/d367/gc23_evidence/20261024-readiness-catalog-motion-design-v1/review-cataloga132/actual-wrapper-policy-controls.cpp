
#include "gc_asset_gate.h"
#include "native_io.h"
#include <cassert>
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>
#include <sys/types.h>
using namespace re4dc_gcasset;
unsigned char initial_file[]={71,67,73,68,88,48,48,49,1,0,0,0,3,0,0,0,112,0,0,0,128,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,103,101,111,109,101,116,114,121,0,0,0,0,0,0,0,0,97,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,74,100,161,7,240,203,50,83,110,91,206,108,152,195,147,219,33,204,167,244,234,24,123,168,196,220,168,181,29,78,168,10,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,103,101,111,109,101,116,114,121,0,0,0,0,0,0,0,0,98,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,242,153,121,28,221,211,214,102,79,102,112,132,40,18,239,96,83,235,101,1,189,98,130,164,118,187,191,62,233,30,117,12,2,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,103,101,111,109,101,116,114,121,0,0,0,0,0,0,0,0,99,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,171,137,127,189,237,250,80,43,45,131,155,106,86,16,8,135,220,205,197,7,85,92,40,46,89,88,158,6,48,10,98,226,2,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0};
std::vector<unsigned char> file(initial_file,initial_file+sizeof initial_file);
std::string logs;unsigned cursor,io_depth,opens,closes,seeks,reads;int live_fd;
bool short_read,close_failure,nested_failed;CheckedAsset other;Digest other_digest;
enum Hook{NoHook,Interleave,RetireDiscSeek,RetireDiscRead,RetireCoreRead,EnsureOpen,RetireOpen,RetireTotal,InterleaveBind,CoreReplace,OpenFail,TotalShort,SeekFail,ReadFail};Hook hook=NoHook;
extern "C" void re4dc_log(const char* fmt,...){assert(!io_depth);char s[256];va_list a;va_start(a,fmt);vsnprintf(s,sizeof s,fmt,a);va_end(a);logs+=s;}
extern "C" void* re4dc_io_begin(){++io_depth;return &io_depth;}
extern "C" void re4dc_io_end(void* p){assert(p==&io_depth&&io_depth);--io_depth;}
int fs_open(const char*,int){assert(!live_fd);if(hook==OpenFail){hook=NoHook;++opens;return -1;}live_fd=100+int(++opens);cursor=0;
 if(hook==EnsureOpen){hook=NoHook;nested_failed=!ensure_disc_catalog();}
 if(hook==RetireOpen){hook=NoHook;retire_disc_catalog();}
 return live_fd;}
int fs_close(int fd){assert(fd==live_fd);++closes;if(close_failure)return -1;live_fd=0;return 0;}
off_t fs_total(int fd){assert(fd==live_fd);if(hook==TotalShort){hook=NoHook;return 127;}if(hook==RetireTotal){hook=NoHook;retire_disc_catalog();}return file.size();}
off_t fs_seek(int fd,off_t at,int){assert(fd==live_fd);++seeks;cursor=unsigned(at);if(hook==SeekFail){hook=NoHook;return at+1;}
 if(hook==Interleave){hook=NoHook;AssetDescription d;memset(&d,0xff,sizeof d);nested_failed=!describe_checked(other,&d);assert(nested_failed&&!d.kind[0]&&!d.id[0]);}
 if(hook==InterleaveBind){hook=NoHook;nested_failed=!bind_checked("geometry","b",other_digest).value;assert(nested_failed);}
 if(hook==RetireDiscSeek){hook=NoHook;retire_disc_catalog();assert(closes==0&&live_fd==fd);}
 return at;}
ssize_t fs_read(int fd,void* p,unsigned n){assert(fd==live_fd);++reads;if(hook==ReadFail){hook=NoHook;return -1;}if(hook==CoreReplace){hook=NoHook;retire_catalog();const unsigned char byte=17;const CatalogRow newer={"geometry","a",fingerprint(&byte,1),PS2};assert(install(&newer,1));}if(cursor+n>file.size())return 0;memcpy(p,file.data()+cursor,n);cursor+=n;
 if(hook==RetireDiscRead){hook=NoHook;retire_disc_catalog();assert(closes==0&&live_fd==fd);}
 if(hook==RetireCoreRead){hook=NoHook;retire_catalog();}
 return short_read?n-1:n;}
#include "gc_asset_disc.cpp"
Digest digest(unsigned i){const unsigned char byte=17+i;return fingerprint(&byte,1);}
CheckedAsset bind_a(){return bind_checked("geometry","a",digest(0));}
void disc_setup(){assert(ensure_disc_catalog());assert(opens==1&&live_fd&&io_depth==0);assert(disc_state.load()==Ready);}
void explicit_reinstall(CheckedAsset old){
 const int fd=live_fd;const unsigned old_closes=closes;
 assert(!ensure_disc_catalog());assert(opens==1&&live_fd==fd&&closes==old_closes);
 retire_disc_catalog();assert(!live_fd&&closes==old_closes+1&&disc_state.load()==FreshInstall&&!checked_current(old));
 assert(ensure_disc_catalog()&&opens==2&&disc_state.load()==Ready);
 const auto fresh=bind_a();assert(fresh.value&&fresh.value!=old.value&&checked_current(fresh)&&!checked_current(old));
}
struct Reader {unsigned phase=0,action=0;bool fired=false;};
CatalogRow replacement;Reader nested_reader;
unsigned independent_read(void* opaque,unsigned off,void* dst,unsigned n){
 auto& r=*static_cast<Reader*>(opaque);if(off>file.size()||n>file.size()-off)return 0;
 memcpy(dst,file.data()+off,n);
 const bool trigger=(r.phase==1&&off==0&&n==file.size())||(r.phase==2&&off==0&&n==128)||(r.phase==3&&off==128&&n==112)||(r.phase==4&&n==112);
 if(r.action&&trigger){const unsigned action=r.action;r.action=0;r.fired=true;retire_catalog();
  if(action==2)assert(install(&replacement,1));
  if(action==3){nested_reader={};const auto pin=fingerprint(file.data(),file.size());assert(install_index(independent_read,&nested_reader,file.size(),pin));}
 }
 return n;
}
void core_case(unsigned phase,unsigned action,bool binding,bool describing){
 replacement={"geometry","a",digest(0),PS2};Reader r;
 const auto pin=fingerprint(file.data(),file.size());
 if(binding||describing){assert(install_index(independent_read,&r,file.size(),pin));const auto old=bind_a();assert(old.value);
  r.phase=4;r.action=action;
  if(binding){const auto result=bind_a();assert(r.fired&&!result.value);}
  if(describing){AssetDescription desc;memset(&desc,0xff,sizeof desc);assert(!describe_checked(old,&desc));assert(r.fired&&!desc.kind[0]&&!desc.id[0]);}
  assert(!checked_current(old));
 }else{r.phase=phase;r.action=action;assert(!install_index(independent_read,&r,file.size(),pin));assert(r.fired);}
 if(action==1){assert(!bind_a().value);}
 else{const auto token=bind_a();AssetDescription desc;assert(token.value&&describe_checked(token,&desc));assert(desc.provenance==(action==2?PS2:GameCube));}
}

int main(int argc,char**argv){assert(argc==2);const unsigned n=std::stoi(argv[1]);
 if(n==0){hook=CoreReplace;assert(!ensure_disc_catalog());assert(disc_state.load()==Failed&&!bind_a().value&&live_fd&&opens==1&&!closes);assert(!ensure_disc_catalog());retire_disc_catalog();assert(!live_fd&&closes==1&&disc_state.load()==FreshInstall);assert(ensure_disc_catalog()&&opens==2&&bind_a().value);}
 if(n==1){disc_setup();const auto old=bind_a();hook=CoreReplace;AssetDescription d;memset(&d,0xff,sizeof d);assert(!describe_checked(old,&d)&&!d.kind[0]&&!d.id[0]);assert(disc_state.load()==Ready&&!checked_current(old));const auto fresh=bind_a();assert(fresh.value&&fresh.value!=old.value&&describe_checked(fresh,&d)&&d.provenance==PS2);}
 if(n==2){hook=OpenFail;assert(!ensure_disc_catalog()&&disc_state.load()==Failed&&!live_fd&&opens==1);assert(!ensure_disc_catalog()&&opens==1);retire_disc_catalog();assert(disc_state.load()==FreshInstall&&!closes);assert(ensure_disc_catalog()&&opens==2&&bind_a().value);}
 if(n==3){hook=TotalShort;assert(!ensure_disc_catalog()&&disc_state.load()==Failed&&live_fd&&opens==1);const int oldfd=live_fd;assert(!ensure_disc_catalog()&&live_fd==oldfd&&opens==1&&!closes);retire_disc_catalog();assert(!live_fd&&closes==1);assert(ensure_disc_catalog()&&opens==2&&bind_a().value);}
 if(n==4||n==5){disc_setup();const auto old=bind_a();hook=n==4?SeekFail:ReadFail;AssetDescription d;memset(&d,0xff,sizeof d);assert(!describe_checked(old,&d)&&!d.kind[0]&&!d.id[0]);assert(disc_state.load()==Failed&&!checked_current(old)&&live_fd&&!closes);explicit_reinstall(old);}
 assert(!io_depth);
}
