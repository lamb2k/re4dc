"""Exercise the real C++ catalog/token implementation with formatter bytes."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from catalog_index import build, sha

HERE = Path(__file__).resolve().parent
GAME = HERE.parents[2] / 'game'


class RuntimeIndexTests(unittest.TestCase):
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
    assert(reads==first_reads);end(1);assert(rows()==2);
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
    for(unsigned i=0;i<8;++i){char id[16];snprintf(id,sizeof id,"sound-%u",i);
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
