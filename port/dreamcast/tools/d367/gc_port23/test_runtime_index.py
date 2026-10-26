"""Exercise the real C++ catalog/token implementation with formatter bytes."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from catalog_index import build, sha
from test_runtime_hooks import function

HERE = Path(__file__).resolve().parent
GAME = HERE.parents[2] / 'game'


class RuntimeIndexTests(unittest.TestCase):
    def test_actual_disc_loader_and_texture_load_boundary(self):
        payload = b'immutable full RE4TEX member'
        blob, pin = build([dict(kind='texture', id='00000001-00000002', sha256=sha(payload).hex(), provenance='unknown', evidence='exact unproved bytes')])
        ui = (GAME / 'platform/native_ui.cpp').read_text()
        capture = function(ui, 'bool gcasset_texture_fingerprint(')
        fixture = r'''
#include "gc_asset_gate.h"
#include "native_io.h"
#include <kos/fs.h>
#include <fcntl.h>
#include <cassert>
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>
using namespace re4dc_gcasset;
std::vector<unsigned char> catalog={BLOB},texture={PAYLOAD};
unsigned offsets[3],opens,closes,io_depth,io_calls;bool missing,short_read;std::string logs;
extern "C" void* re4dc_io_begin(){assert(!io_depth);++io_depth;++io_calls;return &io_depth;}
extern "C" void re4dc_io_end(void* owner){assert(owner==&io_depth && io_depth==1);--io_depth;}
extern "C" void re4dc_log(const char* fmt,...){assert(!io_depth);char line[256];va_list ap;va_start(ap,fmt);vsnprintf(line,sizeof line,fmt,ap);va_end(ap);logs+=line;}
file_t fs_open(const char* path,int){assert(io_depth==1);++opens;if(missing)return FILEHND_INVALID;return !std::strcmp(path,"/cd/dc/gc-assets.idx")?1:2;}
int fs_close(file_t){assert(io_depth==1);++closes;return 0;}
off_t fs_total(file_t fd){assert(io_depth==1);return fd==1?catalog.size():texture.size();}
off_t fs_seek(file_t fd,off_t at,int){assert(io_depth==1);offsets[fd]=unsigned(at);return at;}
ssize_t fs_read(file_t fd,void* target,unsigned bytes){assert(io_depth==1);auto& source=fd==1?catalog:texture;unsigned& at=offsets[fd];if(short_read || at>source.size() || bytes>source.size()-at)return 0;memcpy(target,source.data()+at,bytes);at+=bytes;return bytes;}
#include <cstdint>
namespace re4dc{namespace storage{bool read_chunks(int f,std::size_t n,bool(*c)(const std::uint8_t*,std::size_t,void*),void* ctx){unsigned char b[1000];while(n){const unsigned k=n<1000?unsigned(n):1000u;if(fs_read(f,b,k)!=ssize_t(k))return false;if(!c(b,k,ctx))return false;n-=k;}return true;}}}
struct Key{unsigned crc,fnv;};struct Pkg{file_t stream_file()const{return FILEHND_INVALID;}};struct Entry{CheckedAsset asset;Key key;Pkg package;};
''' + capture + r'''
int main(){
    if(!std::strcmp(RE4DC_GC_ASSET_CATALOG_SHA256,"0")){
        assert(!ensure_disc_catalog());assert(!ensure_disc_catalog());assert(!opens);
        assert(logs.find("catalog-pin-missing")!=std::string::npos);assert(!io_depth && !io_calls);return 0;
    }
    Entry entry{};entry.key={99,99};const Key key{1,2};
    assert(gcasset_texture_fingerprint(entry,key,"/cd/member.tex",0,0));
    AssetDescription row;assert(describe_checked(entry.asset,&row));assert(!std::strcmp(row.id,"00000001-00000002"));
    assert(!memcmp(row.digest.bytes,fingerprint(texture.data(),texture.size()).bytes,32));
    // The source key comes from the actual successful request, never a stale
    // slot key assigned later by the production cache's publish operation.
    const unsigned opened=opens;assert(opened==2 && closes==1);
    begin(0x111,1,Required);emitted_checked(Texture,entry.asset);end(1);
    begin(0x113,2,Required);assert(ensure_disc_catalog());emitted_checked(Texture,entry.asset);end(1);
    assert(opens==opened);const CheckedAsset old=entry.asset;
    retire_disc_catalog();assert(closes==2);assert(!describe_checked(old,&row));
    assert(ensure_disc_catalog());assert(opens==opened+1);assert(!describe_checked(old,&row));
    logs.clear();begin(0x111,3,Required);emitted_checked(Texture,old);end(1);assert(logs.find("catalog-token")!=std::string::npos);
    retire_disc_catalog();missing=true;assert(!ensure_disc_catalog());const unsigned failed_opens=opens;
    assert(!ensure_disc_catalog() && opens==failed_opens); // failure is not an auto-learning/retry path
    retire_disc_catalog();missing=false;short_read=true;
    assert(!ensure_disc_catalog());assert(!io_depth); // failed install closes outside formatting
    retire_disc_catalog();short_read=false;assert(ensure_disc_catalog());
    short_read=true;const unsigned before_close=closes;
    assert(!gcasset_texture_fingerprint(entry,key,"/cd/member.tex",0,0));
    assert(!entry.asset.value && closes==before_close+1 && !io_depth);
    short_read=false;missing=true;
    assert(!gcasset_texture_fingerprint(entry,key,"/cd/member.tex",0,0));
    assert(!entry.asset.value && !io_depth);retire_disc_catalog();assert(!io_depth && io_calls);
}
'''
        fixture = fixture.replace('BLOB', ','.join(map(str, blob))).replace('PAYLOAD', ','.join(map(str, payload)))
        with tempfile.TemporaryDirectory(prefix='gc-port23-disc-', dir='/dev/shm') as temporary:
            root = Path(temporary)
            (root / 'kos').mkdir()
            (root / 'kos/fs.h').write_text('#pragma once\n#include <sys/types.h>\nusing file_t=int;\nconstexpr file_t FILEHND_INVALID=-1;\nfile_t fs_open(const char*,int);int fs_close(file_t);off_t fs_total(file_t);off_t fs_seek(file_t,off_t,int);ssize_t fs_read(file_t,void*,unsigned);\n')
            (root / 'fixture.cpp').write_text(fixture)
            for configured in ('0', pin.hex()):
                executable = root / ('fixture-' + configured[:8])
                subprocess.run(['g++', '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror',
                                '-DRE4DC_GC_ASSET_GATE=1', '-DRE4DC_GC_ASSET_CATALOG_SHA256="'+configured+'"',
                                '-I', str(root), '-I', str(GAME / 'platform/include'),
                                str(root / 'fixture.cpp'), str(GAME / 'platform/gc_asset_disc.cpp'),
                                str(GAME / 'platform/gc_asset_gate.cpp'), '-o', str(executable)], check=True)
                subprocess.run(['/lib64/ld-linux-x86-64.so.2', str(executable)], check=True)

    def test_actual_reader_tokens_and_disc_room_lifetimes(self):
        blob, pin = build([
            dict(kind='texture', id='gc-key', sha256=sha(b'PS2 pixels').hex(), provenance='ps2', evidence='exact proof'),
            dict(kind='model', id='member-a', sha256=sha(b'GC BIN').hex(), provenance='unknown', evidence='unproved')])
        fixture = r'''
#include "gc_asset_gate.h"
#include <cassert>
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>
using namespace re4dc_gcasset;
std::string output;unsigned reads=0;bool short_read=false;
extern "C" void re4dc_log(const char* fmt,...){
    char line[256];va_list args;va_start(args,fmt);int n=vsnprintf(line,sizeof line,fmt,args);va_end(args);
    assert(n>=0 && unsigned(n)<sizeof line);output+=line;
}
unsigned read_at(void* ctx,unsigned offset,void* target,unsigned count){
    ++reads;auto& data=*static_cast<std::vector<unsigned char>*>(ctx);
    if(offset>data.size() || count>data.size()-offset || short_read)return 0;
    memcpy(target,data.data()+offset,count);return count;
}
unsigned rows(){unsigned n=0;std::size_t at=0;while((at=output.find("GC-ASSET v=",at))!=std::string::npos){++n;++at;}return n;}
int main(){
    std::vector<unsigned char> data={BLOB};Digest pin{{PIN}};AssetDescription description;
    assert(install_index(read_at,&data,data.size(),pin));
    auto model=bind_checked("model","member-a",fingerprint("GC BIN",6));
    auto ps2=bind_checked("texture","gc-key",fingerprint("PS2 pixels",10));
    auto changed=bind_checked("texture","gc-key",fingerprint("changed pixels",14));
    assert(describe_checked(ps2,&description) && description.provenance==PS2);
    assert(describe_checked(changed,&description) && description.provenance==Unknown);
    begin(0x111,1,Required);emitted_checked(SourceGeometry,model);emitted_checked(Texture,ps2);emitted_checked(Texture,changed);
    const unsigned first_reads=reads;emitted_checked(Weapon,model);emitted_checked(EffectPicture,ps2);
    assert(reads==first_reads);
    // gc-catalog24b r8: Motion is wired like any consumer. A seen row needs no
    // read (cast-ps2-25 r17: a seen texture row given to Motion is a kind-mismatch
    // error, from the seen-row bit); a new motion identity binds (one catalog search).
    emitted_checked(Motion,ps2);assert(reads==first_reads);
    emitted(Motion,"motion","not-admitted",fingerprint("motion",6));
    assert(reads>first_reads);end(1);assert(rows()==3);
    assert(output.find("motion-unwired")==std::string::npos && output.find("motion=2")!=std::string::npos && output.find("errors=1")!=std::string::npos &&
           output.find("why=kind-mismatch consumer=9")!=std::string::npos);
    assert(output.find("kind=motion id=not-admitted")!=std::string::npos && output.find("consumer=motion")!=std::string::npos);
    assert(output.find("source_geometry=1 texture=2 effect_picture=1 weapon=1")!=std::string::npos);
    // Room retirement resets observations, not the immutable disc epoch. A
    // persistent live owner may reuse its original token in the next room.
    output.clear();begin(0x113,2,Required);emitted_checked(SourceGeometry,model);end(1);assert(rows()==1);
    assert(describe_checked(model,&description));
    // Disc replacement invalidates all tokens, even if record numbers repeat.
    assert(install_index(read_at,&data,data.size(),pin));assert(!describe_checked(model,&description));
    output.clear();begin(0x111,3,Required);emitted_checked(SourceGeometry,model);end(1);
    assert(output.find("why=catalog-token")!=std::string::npos && rows()==0);
    auto current=bind_checked("model","member-a",fingerprint("GC BIN",6));
    retire_catalog();assert(!describe_checked(current,&description));
    assert(install_index(read_at,&data,data.size(),pin));assert(!describe_checked(current,&description));
    // Neither an unknown record nor a failed install can supply a PS2 verdict.
    for(unsigned i=0;i<64;++i){char id[16];snprintf(id,sizeof id,"sound-%u",i);
        assert(bind_checked("sound",id,fingerprint(id,unsigned(strlen(id)))).value);}
    assert(!bind_checked("sound","overflow",fingerprint("x",1)).value);
    Digest badpin{};assert(!install_index(read_at,&data,data.size(),badpin));
    assert(!describe_checked(current,&description));
    short_read=true;assert(!install_index(read_at,&data,data.size(),pin));short_read=false;
    // Even a pinned malformed record order/duplicate/schema is rejected.
    auto malformed=data;memcpy(malformed.data()+128+112,malformed.data()+128,112);
    auto malformed_pin=fingerprint(malformed.data(),malformed.size());
    assert(!install_index(read_at,&malformed,malformed.size(),malformed_pin));
    malformed=data;malformed[128+97]=1;malformed_pin=fingerprint(malformed.data(),malformed.size());
    assert(!install_index(read_at,&malformed,malformed.size(),malformed_pin));
    malformed=data;malformed[128]='A';malformed_pin=fingerprint(malformed.data(),malformed.size());
    assert(!install_index(read_at,&malformed,malformed.size(),malformed_pin));
    // Missing reads at safe first use are explicit errors. No unobserved pass.
    assert(install_index(read_at,&data,data.size(),pin));current=bind_checked("model","member-a",fingerprint("GC BIN",6));
    output.clear();begin(0x111,4,Required);short_read=true;emitted_checked(SourceGeometry,current);short_read=false;end(1);
    assert(output.find("why=catalog-read")!=std::string::npos && rows()==0);
}
'''.replace('BLOB', ','.join(map(str, blob))).replace('PIN', ','.join(map(str, pin)))
        with tempfile.TemporaryDirectory(prefix='gc-port23-index-', dir='/dev/shm') as temporary:
            root = Path(temporary)
            (root / 'fixture.cpp').write_text(fixture)
            executable = root / 'fixture'
            subprocess.run(['g++', '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror',
                            '-DRE4DC_GC_ASSET_GATE=1', '-I', str(GAME / 'platform/include'),
                            str(root / 'fixture.cpp'), str(GAME / 'platform/gc_asset_gate.cpp'),
                            '-o', str(executable)], check=True)
            subprocess.run(['/lib64/ld-linux-x86-64.so.2', str(executable)], check=True)


if __name__ == '__main__':unittest.main()
