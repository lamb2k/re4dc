"""GC-ASSET Motion (bit 9, gc-catalog24b round 8): the runtime clip key equals the catalog builder's.

motion_use (gc_asset_members.cpp) and build_catalog.motion_clips must give every FCV/SEQ clip the same
"<crc32>-<fnv1a>" key: an inline FCV from its archive span with the in-place relocated key table read back
as offsets, a SEQ from its raw span, and an MTC-keyed proxy FCV from its MTC row. The fixture builds one
archive, relocates the FCV table as motion.cpp does, plays every clip twice and checks the flushed rows.
"""
import hashlib
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path

import build_catalog
from catalog_index import build

GAME = Path(__file__).resolve().parents[3] / 'game'


def fcv(parts, payload):
    # byte 2 = part count; header 3 + 2n kinds + n part numbers, aligned, one skipped word, n offsets
    head = bytearray(3 + 3 * parts)
    head[2] = parts
    while len(head) % 4:
        head.append(0)
    head += bytes(4)
    table_at = len(head)
    head += bytes(4 * parts)
    for i in range(parts):
        struct.pack_into('<I', head, table_at + 4 * i, len(head) + 4 * i)  # offsets into the clip
    return bytes(head) + payload


def archive(entries):
    """Tag archive: count, rel, pad; offsets; tags; bodies 32-aligned."""
    n = len(entries)
    at = (16 + 8 * n + 31) & ~31
    offsets, body = [], b''
    for _tag, data in entries:
        offsets.append(at + len(body))
        body += data + bytes((-len(data)) % 32)
    head = struct.pack('<4I', n, 0, 0, 0) + b''.join(struct.pack('<I', o) for o in offsets)
    head += b''.join(t for t, _ in entries)
    head += bytes(at - len(head))
    return bytearray(head + body), offsets


class MotionIdentityTests(unittest.TestCase):
    def test_runtime_key_equals_builder_key(self):
        inline = fcv(3, bytes(range(40)))
        proxy = fcv(2, bytes(8))
        seq = struct.pack('<4H', 3, 0, 1, 2) + bytes(24)
        mtc_row_key = (0x12345678, 0x9abcdef0)
        entries = [(b'FCV\0', inline), (b'SEQ\0', seq), (b'FCV\0', proxy), (b'MTC\0', bytes(32 + 20))]
        arc, offsets = archive(entries)
        m = offsets[3]
        arc[m:m + 8] = b'R4MOTBL\0'
        struct.pack_into('<5I', arc, m + 8, 2, 1, 20, 0, 0)          # version, rows, stride
        struct.pack_into('<5I', arc, m + 32, offsets[2], 64, *mtc_row_key, 0)
        keys = [k for k, _ in build_catalog.motion_clips(bytes(arc))]
        self.assertEqual(len(keys), 3)
        self.assertEqual(keys[2], '%08x-%08x' % mtc_row_key)
        rows = [dict(kind='motion', id=k, sha256=hashlib.sha256(k8).hexdigest(), provenance='gc' if i else 'ps2',
                     evidence='synthetic') for i, (k, k8) in enumerate(build_catalog.motion_clips(bytes(arc)))]
        blob, pin = build(rows)
        fixture = r'''
#include "gc_asset_gate.h"
#include "gc_asset_members.h"
#include <cassert>
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>
#include <sys/mman.h>
using namespace re4dc_gcasset;
std::string logs;
extern "C" void re4dc_log(const char* f,...){char s[512];va_list a;va_start(a,f);vsnprintf(s,sizeof s,f,a);va_end(a);logs+=s;}
namespace re4dc_gcasset{bool ensure_disc_catalog(){return true;}}
std::vector<unsigned char> blob={BLOB};
unsigned read_at(void*,unsigned o,void* t,unsigned n){if(o>blob.size()||n>blob.size()-o)return 0;memcpy(t,blob.data()+o,n);return n;}
const unsigned char arc_bytes[]={ARC};
int main(){
    // The archive sits at a Dreamcast main-RAM address, so a relocated word reads negative as on SH-4.
    auto* arc=static_cast<unsigned char*>(mmap(reinterpret_cast<void*>(0x8c400000UL),sizeof arc_bytes,PROT_READ|PROT_WRITE,
        MAP_PRIVATE|MAP_ANONYMOUS|MAP_FIXED_NOREPLACE,-1,0));
    assert(arc==reinterpret_cast<unsigned char*>(0x8c400000UL));memcpy(arc,arc_bytes,sizeof arc_bytes);
    Digest pin{{PIN}};assert(install_index(read_at,nullptr,blob.size(),pin));
    begin(0x101,1,Required);
    int owner;assert(member_adopt(&owner,arc,sizeof arc_bytes,false));
    unsigned char* clip=arc+OFF0;   // relocate the inline FCV's key table in place, as motion.cpp does
    const unsigned n=clip[2],head=((3+3*n+3)&~3U)+4+4*n;
    for(unsigned i=0;i<n;++i){unsigned w;memcpy(&w,clip+head-4*n+4*i,4);w+=unsigned(reinterpret_cast<std::uintptr_t>(clip));memcpy(clip+head-4*n+4*i,&w,4);}
    for(int pass=0;pass<2;++pass){motion_use(arc+OFF0);motion_use(arc+OFF1);motion_use(arc+OFF2);}
    motion_flush();end(1);
    assert(logs.find("kind=motion id=KEY0")==std::string::npos);   // ps2 rows are not logged
    assert(logs.find("kind=motion id=KEY1 ")!=std::string::npos && logs.find("kind=motion id=KEY2 ")!=std::string::npos);
    assert(logs.find("motion=3")!=std::string::npos && logs.find("errors=0")!=std::string::npos);
    printf("%s",logs.c_str());
}
'''
        fixture = (fixture.replace('BLOB', ','.join(map(str, blob))).replace('PIN', ','.join(map(str, pin)))
                   .replace('ARC', ','.join(map(str, arc))).replace('OFF0', str(offsets[0]))
                   .replace('OFF1', str(offsets[1])).replace('OFF2', str(offsets[2]))
                   .replace('KEY0', keys[0]).replace('KEY1', keys[1]).replace('KEY2', keys[2]))
        with tempfile.TemporaryDirectory(prefix='gc-motion-id-', dir='/dev/shm') as t:
            root = Path(t)
            (root / 'fixture.cpp').write_text(fixture)
            exe = root / 'fixture'
            out = subprocess.run(['g++', '-std=c++17', '-O1', '-w', '-DRE4DC_GC_ASSET_GATE=1',
                                  '-I', str(GAME / 'platform/include'), str(root / 'fixture.cpp'),
                                  str(GAME / 'platform/gc_asset_gate.cpp'), str(GAME / 'platform/gc_asset_members.cpp'),
                                  '-o', str(exe)], capture_output=True, text=True)
            self.assertEqual(out.returncode, 0, out.stderr[-3000:])
            run = subprocess.run(['/lib64/ld-linux-x86-64.so.2', str(exe)], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr + run.stdout)


if __name__ == '__main__':
    unittest.main()
