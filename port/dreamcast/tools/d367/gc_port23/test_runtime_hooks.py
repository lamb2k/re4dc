"""Compile the actual native_ui texture hook bodies with a tiny fake renderer."""
from pathlib import Path
import subprocess
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
GAME = HERE.parents[2] / 'game'


def function(source, marker):
    start = source.index(marker)
    opening = source.index('{', start)
    depth = 1
    cursor = opening + 1
    while depth:
        depth += (source[cursor] == '{') - (source[cursor] == '}')
        cursor += 1
    return source[start:cursor]


class RuntimeTextureTests(unittest.TestCase):
    def test_actual_direct_and_batched_end_bodies(self):
        ui = (GAME / 'platform/native_ui.cpp').read_text()
        static = (GAME / 'platform/native_static.cpp').read_text()
        marker = ui.index('// WORLD_SUBMIT_END_IMPLEMENTATION')
        begin = ui.index('#if RE4DC_TA_DIRECT', marker)
        close = ui.index('\n}\n#if RE4DC_SCENERY_SUBMIT_BATCH', begin) + 2
        body = ui[begin:close]
        prefix = r'''
#include <cassert>
#include <cstdint>
#include <cstdlib>
struct Re4dcWorldSubmitBatch { std::uint32_t* sq; };
bool sq_held,direct_open;
unsigned direct_parts,direct_slots,frame_pvr_bytes,stream_model_bytes,stream_peak_bytes,model_used;
unsigned notices;void* model_handle;
void sq_unlock(){assert(sq_held);sq_held=false;}
void re4dc_missing(const char*){std::abort();}
#define RE4DC_GCA_TEXTURE(...) (++notices)
'''
        for batch in (0, 1):
            if batch:
                declaration = 'static void model_direct_account(unsigned vertices){\n'
                remaining = ui.index('#if RE4DC_SCENERY_SUBMIT_BATCH', close)
                wrappers = '\n'.join(function(ui[remaining:], m) for m in (
                    'extern "C" void re4dc_model_direct_end(unsigned vertices)',
                    'extern "C" void re4dc_ps2_world_batch_close(',
                    'extern "C" void re4dc_ps2_world_direct_end_batch('))
                mesh_method = function(static, 'void end_direct(){if(sq){')
            else:
                declaration = 'extern "C" void re4dc_model_direct_end(unsigned vertices){\n'
                wrappers = ''
                mesh_method = function(static[static.index('#else\n    void end_direct'):], 'void end_direct(){if(sq){')
            fixture = prefix + declaration + body + '\n' + wrappers + r'''
struct Mesh {
  std::uint32_t* sq;unsigned slots;Re4dcWorldSubmitBatch* submit_batch;
''' + mesh_method + r'''
};
int main(){
  std::uint32_t dummy=0;Re4dcWorldSubmitBatch batch{&dummy};
  direct_open=sq_held=true;
  Mesh mesh{&dummy,0,nullptr};mesh.end_direct();assert(notices==0);assert(!sq_held);
  direct_open=sq_held=true;mesh.sq=&dummy;mesh.slots=3;mesh.end_direct();assert(notices==1);assert(!sq_held);
#if RE4DC_SCENERY_SUBMIT_BATCH
  direct_open=sq_held=true;mesh.sq=&dummy;mesh.slots=6;mesh.submit_batch=&batch;mesh.end_direct();
  assert(notices==2);assert(sq_held);assert(!direct_open); // account while the shared SQ remains locked
  re4dc_ps2_world_batch_close(&batch);assert(!sq_held);
#else
  (void)batch;
#endif
}
'''
            with tempfile.TemporaryDirectory(prefix='gc-port23-direct-', dir='/dev/shm') as temporary:
                root = Path(temporary)
                (root / 'fixture.cpp').write_text(fixture)
                executable = root / 'fixture'
                subprocess.run(['g++', '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror',
                                '-DRE4DC_TA_DIRECT=1', '-DRE4DC_SCENERY_SUBMIT_BATCH='+str(batch),
                                str(root / 'fixture.cpp'), '-o', str(executable)], check=True)
                subprocess.run(['/lib64/ld-linux-x86-64.so.2', str(executable)], check=True)

    def test_actual_texture_hook_bodies(self):
        ui = (GAME / 'platform/native_ui.cpp').read_text()
        emitted = function(ui, 'void gcasset_texture_emitted(')
        flush = function(ui, 'void gcasset_texture_flush(')
        packet = function(ui, 'void gcasset_packet_emitted(')
        state = ui[ui.index('struct GcAssetPacketState '):ui.index('void gcasset_packet_emitted(')]
        fixture = r'''
#include "gc_asset_gate.h"
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstdarg>
#include <string>
struct Package {
  struct Header { unsigned texture_count=1; } head;
  unsigned address;
  const Header& header() const { return head; }
  bool upload_complete() const { return true; }
  void* pvr_texture(unsigned) const { return reinterpret_cast<void*>(std::uintptr_t(address)); }
};
struct Entry { Package package;struct Key { unsigned crc,fnv; } key;bool valid;
  re4dc_gcasset::Digest asset_digest{};unsigned asset_consumers=0;
};
Entry entries[2];
bool sq_held;
std::string logs;
extern "C" void re4dc_log(const char* fmt,...) {
  assert(!sq_held);char buf[2048];va_list ap;va_start(ap,fmt);vsnprintf(buf,sizeof buf,fmt,ap);va_end(ap);logs+=buf;
}
''' + emitted + '\n' + flush + '\n' + state + '\n' + packet + r'''
int main() {
  using namespace re4dc_gcasset;
  entries[0].valid=true;entries[0].package.address=0x1000;entries[0].key={1,2};
  entries[1].valid=true;entries[1].package.address=0x2000;entries[1].key={3,4};
  install(nullptr,0);begin(0x111,1,Required);
  std::uint32_t header[8]={0x80000008,0,0,0x1000/8};
  std::uint32_t vertex[8]={0xe0000000};
  gcasset_packet_emitted(header,sizeof header,0,Texture);
  assert(entries[0].asset_consumers==0); // prepared header emits no vertices
  gcasset_packet_emitted(vertex,sizeof vertex,0,Texture);
  assert(entries[0].asset_consumers==(1U<<Texture)); // split packet uses carried header
  assert(logs.find("GC-ASSET v=")==std::string::npos); // no hash/log under emitter
  gcasset_texture_flush(entries[0]);
  assert(logs.find("id=00000001-00000002")!=std::string::npos);
  assert(logs.find("id=00000003-00000004")==std::string::npos); // loaded never emitted
  entries[0].asset_consumers=0;
  gcasset_packet_emitted(header,sizeof header,0,Texture);
  gcasset_packet_reset(); // real scene-open/retirement boundary must clear prior header
  gcasset_packet_emitted(vertex,sizeof vertex,0,Texture);
  assert(entries[0].asset_consumers==0);
  std::uint32_t picture[16]={0x80000008,0,0,0x1000/8};picture[8]=0xe0000000;
  gcasset_packet_emitted(picture,sizeof picture,2,EffectPicture);
  assert(entries[0].asset_consumers& (1U<<EffectPicture));
  sq_held=true;gcasset_texture_emitted(&entries[1]);sq_held=false;
  assert(entries[1].asset_consumers==(1U<<Texture)); // direct/batched path only latches
  gcasset_texture_flush(entries[0]);gcasset_texture_flush(entries[1]);
  for(unsigned i=0;i<ConsumerCount;++i) { checked(Consumer(i)); }
  end(1);
  assert(logs.find("unique=2 overflow=0 errors=0")!=std::string::npos);
  logs.clear();begin(0x111,2,Required);
  picture[3]=0x3000/8;gcasset_packet_emitted(picture,sizeof picture,2,Texture);end(1);
  assert(logs.find("unmapped-texture-address")!=std::string::npos);
  logs.clear();begin(0x111,3,Required);
  entries[1].package.address=0x1000;picture[3]=0x1000/8;
  gcasset_packet_emitted(picture,sizeof picture,2,Texture);end(1);
  assert(logs.find("ambiguous-texture-address")!=std::string::npos);
}
'''
        with tempfile.TemporaryDirectory(prefix='gc-port23-runtime-', dir='/dev/shm') as temporary:
            root = Path(temporary)
            (root / 'fixture.cpp').write_text(fixture)
            executable = root / 'fixture'
            subprocess.run(['g++', '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror',
                            '-DRE4DC_GC_ASSET_GATE=1', '-I', str(GAME / 'platform/include'),
                            str(root / 'fixture.cpp'), str(GAME / 'platform/gc_asset_gate.cpp'),
                            '-o', str(executable)], check=True)
            subprocess.run(['/lib64/ld-linux-x86-64.so.2', str(executable)], check=True)


if __name__ == '__main__':
    unittest.main()
