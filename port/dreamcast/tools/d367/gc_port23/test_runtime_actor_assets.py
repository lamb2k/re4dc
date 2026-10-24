"""Bounded exact actor source proofs, without origin inference from adapters."""
from pathlib import Path
import hashlib
import struct
import subprocess
import tempfile
import unittest
from test_runtime_hooks import function

HERE = Path(__file__).resolve().parent
GAME = HERE.parents[2] / 'game'


class ActorAssetTests(unittest.TestCase):
    def test_actual_registry_and_pl08_capture_retire_hooks(self):
        registry = (GAME / 'coarse_actor_registry_pack.inc').read_text()
        pl08 = (GAME / 'coarse_actor_pl08_pack.inc').read_text()
        fixture = r'''
#include "gc_asset_payloads.h"
#include <cassert>
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <string>
using namespace re4dc_gcasset;
std::string logs;
extern "C" void re4dc_log(const char*fmt,...){char text[256];va_list ap;va_start(ap,fmt);vsnprintf(text,sizeof text,fmt,ap);va_end(ap);logs+=text;}
namespace re4dc_gcasset{bool ensure_disc_catalog(){return true;}}
PayloadProof gcasset_registry[2],gcasset_pl08;
''' + function(registry, 'void gcasset_registry_capture(') + '\n' + function(registry, 'void gcasset_registry_retire(') + r'''
namespace leon4k{struct Weight{};struct Chunk{unsigned source_info,position_count,normal_count,palette_count,triangles,stream_bytes;const unsigned char*positions,*normals,*uv,*stream;const Weight*weights;};}
struct Pl08ChunkView{const unsigned char*array[5];unsigned bytes[5];unsigned source_info,position_count,normal_count,palette_count,triangles;};
struct Pl08PackLife{unsigned char*base;}pl08_pack;
constexpr unsigned kPl08PackBytes=64;leon4k::Chunk pl08_pack_chunks[3];
unsigned frees;void re4dc_static_free(unsigned char*){assert(!gcasset_pl08.serial);++frees;}
''' + function(pl08, 'void pl08_hook_published(const Pl08ChunkView* v) {') + '\n' + function(pl08, 'void pl08_hook_free(') + r'''
int main(){assert(install(nullptr,0));begin(0x111,1,Required);unsigned char a[64]={1},b[64]={2},c[64]={3};
 gcasset_registry_capture(0,a,sizeof a);gcasset_registry_capture(1,b,sizeof b);assert(gcasset_registry[0].serial && gcasset_registry[1].serial);assert(logs.find("GC-ASSET v=")==std::string::npos);
 AssetDescription row;assert(describe_checked(gcasset_registry[1].asset,&row));assert(!memcmp(row.digest.bytes,fingerprint(b,sizeof b).bytes,32));
 const unsigned old=gcasset_registry[0].serial;gcasset_registry_retire();assert(!gcasset_registry[0].serial && !gcasset_registry[1].serial);
 a[0]=4;gcasset_registry_capture(0,a,sizeof a);assert(gcasset_registry[0].serial>old);assert(describe_checked(gcasset_registry[0].asset,&row));assert(!memcmp(row.digest.bytes,fingerprint(a,sizeof a).bytes,32));gcasset_registry_retire();
 pl08_pack.base=c;Pl08ChunkView view[3]{};pl08_hook_published(view);assert(gcasset_pl08.serial);const unsigned p8serial=gcasset_pl08.serial;assert(describe_checked(gcasset_pl08.asset,&row));assert(!memcmp(row.digest.bytes,fingerprint(c,sizeof c).bytes,32));
 pl08_hook_published(nullptr);assert(!gcasset_pl08.serial);c[0]=5;pl08_hook_published(view);assert(gcasset_pl08.serial>p8serial);assert(describe_checked(gcasset_pl08.asset,&row));assert(!memcmp(row.digest.bytes,fingerprint(c,sizeof c).bytes,32));pl08_hook_free(c);assert(frees==1);
}
'''
        self.compile_run(fixture)
        # Actual capture is before preflight/skin work; actual failure/free and
        # room leave revoke the two proofs. This audit complements the executed
        # hook bodies; it is not a claim that accepted actor paths are complete.
        self.assertLess(registry.index('gcasset_registry_capture(0,base,a.size)'), registry.index('why=pack_preflight(base,detail,geometries)'))
        leave = function(registry, 'extern "C" void re4dc_registry_room_leave()')
        self.assertLess(leave.index('gcasset_registry_retire()'), leave.index('re4dc_static_free(pack.cell)'))

    def compile_run(self, fixture):
        with tempfile.TemporaryDirectory(prefix='gc-port23-actor-source-', dir='/dev/shm') as temporary:
            root = Path(temporary);(root / 'fixture.cpp').write_text(fixture);executable = root / 'fixture'
            subprocess.run(['g++', '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror',
                            '-DRE4DC_GC_ASSET_GATE=1', '-I', str(GAME / 'platform/include'),
                            str(root / 'fixture.cpp'), str(GAME / 'platform/gc_asset_gate.cpp'),
                            str(GAME / 'platform/gc_asset_members.cpp'), str(GAME / 'platform/gc_asset_payloads.cpp'),
                            '-o', str(executable)], check=True)
            subprocess.run(['/lib64/ld-linux-x86-64.so.2', str(executable)], check=True)

    def test_compiled_fragment_identity_and_retirement(self):
        spans = [b'ab', b'c']
        encoded = b'GCFRAG01'+struct.pack('<II', len(spans), 0)
        encoded += b''.join(struct.pack('<I', len(span))+span for span in spans)
        digest = hashlib.sha256(encoded).digest()
        large = [b'x'*513, b'y'*900]
        large_digest = hashlib.sha256(b'GCFRAG01'+struct.pack('<II', 2, 0)+b''.join(struct.pack('<I', len(s))+s for s in large)).digest()
        fixture = r'''
#include "gc_asset_payloads.h"
#include <cassert>
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <string>
using namespace re4dc_gcasset;
std::string logs;bool sq;
extern "C" void re4dc_log(const char*fmt,...){assert(!sq);char text[256];va_list ap;va_start(ap,fmt);vsnprintf(text,sizeof text,fmt,ap);va_end(ap);logs+=text;}
int main(){assert(install(nullptr,0));begin(0x111,1,Required);int owner,other;PayloadProof proof,alias;
 PayloadSpan spans[]={{"ab",2},{"c",1}};assert(payload_capture_fragments(proof,&owner,spans,2));
 AssetDescription row;assert(describe_checked(proof.asset,&row));unsigned char expected[]={DIGEST};assert(!memcmp(expected,row.digest.bytes,32));assert(row.provenance==Unknown);
 const unsigned serial=proof.serial;{PayloadScope scope(proof,&owner);sq=true;payload_accept(source_use.payload,source_use.serial,1U<<SourceGeometry);sq=false;}payload_flush_all();assert(logs.find("consumer=source_geometry")!=std::string::npos);
 payload_retire(proof);logs.clear();sq=true;payload_accept(&proof,serial,1U<<Weapon);sq=false;payload_flush_all();assert(logs.find("unbound-accepted-payload")!=std::string::npos);
 PayloadSpan other_split[]={{"a",1},{"bc",2}};assert(payload_capture_fragments(proof,&owner,other_split,2));assert(describe_checked(proof.asset,&row));assert(memcmp(expected,row.digest.bytes,32)); // lengths are authoritative
 assert(!payload_capture_fragments(alias,&owner,spans,2));assert(!proof.serial); // conflicting same owner revokes old
 assert(!payload_capture_fragments(proof,&owner,nullptr,2));assert(!payload_capture_fragments(proof,&owner,spans,49));
 PayloadSpan bad[]={{nullptr,1}};assert(!payload_capture_fragments(proof,&owner,bad,1));bad[0]={"a",0};assert(!payload_capture_fragments(proof,&owner,bad,1));bad[0]={"a",40U*1024*1024};assert(!payload_capture_fragments(proof,&owner,bad,1));
 char large_a[513],large_b[900];memset(large_a,'x',sizeof large_a);memset(large_b,'y',sizeof large_b);PayloadSpan large[]={{large_a,sizeof large_a},{large_b,sizeof large_b}};
 assert(payload_capture_fragments(proof,&other,large,2));assert(proof.serial>serial);assert(describe_checked(proof.asset,&row));unsigned char expected_large[]={LARGE_DIGEST};assert(!memcmp(expected_large,row.digest.bytes,32));
 retire_catalog();logs.clear();payload_accept(&proof,proof.serial,1U<<SourceGeometry);payload_flush_all();assert(logs.find("catalog-token")!=std::string::npos);
}
'''.replace('LARGE_DIGEST', ','.join(map(str, large_digest))).replace('DIGEST', ','.join(map(str, digest)))
        self.compile_run(fixture)


if __name__ == '__main__':unittest.main()
