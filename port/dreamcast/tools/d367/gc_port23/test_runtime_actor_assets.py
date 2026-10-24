"""Bounded exact actor source proofs, without origin inference from adapters."""
from pathlib import Path
import hashlib
import struct
import subprocess
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
GAME = HERE.parents[2] / 'game'


class ActorAssetTests(unittest.TestCase):
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
        with tempfile.TemporaryDirectory(prefix='gc-port23-actor-source-', dir='/dev/shm') as temporary:
            root = Path(temporary);(root / 'fixture.cpp').write_text(fixture);executable = root / 'fixture'
            subprocess.run(['g++', '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror',
                            '-DRE4DC_GC_ASSET_GATE=1', '-I', str(GAME / 'platform/include'),
                            str(root / 'fixture.cpp'), str(GAME / 'platform/gc_asset_gate.cpp'),
                            str(GAME / 'platform/gc_asset_members.cpp'), str(GAME / 'platform/gc_asset_payloads.cpp'),
                            '-o', str(executable)], check=True)
            subprocess.run(['/lib64/ld-linux-x86-64.so.2', str(executable)], check=True)


if __name__ == '__main__':unittest.main()
