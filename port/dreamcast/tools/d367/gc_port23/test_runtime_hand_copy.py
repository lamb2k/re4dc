"""Fail-closed fixed hand copy tickets; actual writer integration is separate."""
from pathlib import Path
import subprocess
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
GAME = HERE.parents[2] / 'game'


class HandCopyTests(unittest.TestCase):
    def test_child_proof_generation_catalog_and_silent_retirement(self):
        fixture = r'''
#include "gc_asset_payloads.h"
#include <cassert>
#include <cstdarg>
#include <cstdio>
#include <string>
using namespace re4dc_gcasset;
bool locked;std::string logs;
extern "C" void re4dc_log(const char* format,...){assert(!locked);char line[256];va_list args;va_start(args,format);vsnprintf(line,sizeof line,format,args);va_end(args);logs+=line;}
int main(){
 assert(install(nullptr,0));begin_startup_closed(1,Required);
 PayloadProof package,left,right;int package_owner,left_owner,right_owner,wrong_owner;unsigned char slots[2][64]{};
 Digest digest=fingerprint("whole-source",12);assert(payload_capture_digest(package,&package_owner,digest));
 assert(payload_copy_register(left,&left_owner,slots[0],64));assert(payload_copy_register(right,&right_owner,slots[1],64));
 assert(!payload_copy_current(left) && !left.serial);const unsigned source=package.serial;
 logs.clear();locked=true;assert(payload_copy_publish(left,&left_owner,package,source));
 assert(payload_copy_publish(right,&right_owner,package,source));assert(payload_copy_current(left));
 const unsigned old=left.serial,other=right.serial;payload_accept(&left,old,1U<<SourceGeometry);
 // Revocation cannot lose a previously accepted acknowledgement or emit under the lock.
 payload_copy_invalidate(left,&left_owner);assert(!payload_copy_current(left));locked=false;
 assert(logs.empty());payload_flush_all();assert(logs.find("kind=geometry")!=std::string::npos);
 logs.clear();locked=true;assert(payload_copy_publish(left,&left_owner,package,source));assert(left.serial!=old);
 // Saved/deferred old generation cannot follow a new blob in the same slot.
 payload_accept(&left,old,1U<<SourceGeometry);locked=false;payload_flush_all();
 assert(logs.find("unbound-accepted-payload")!=std::string::npos && logs.find("GC-ASSET v=")==std::string::npos);
 assert(payload_copy_current(right) && right.serial==other);
 // Invalid publication and wrong-owner revocation cannot retain an old positive.
 locked=true;assert(!payload_copy_publish(left,&left_owner,package,source));assert(!left.serial);
 assert(payload_copy_publish(left,&left_owner,package,source));payload_copy_invalidate(left,&wrong_owner);assert(!left.serial);
 assert(!payload_copy_publish(left,&wrong_owner,package,source));locked=false;
 // Retired/reissued package serial invalidates both inherited identities.
 payload_retire(package);assert(!payload_copy_current(right));
 assert(payload_capture_digest(package,&package_owner,digest));assert(package.serial!=source);
 locked=true;payload_copy_invalidate(left,&left_owner);assert(!payload_copy_publish(left,&left_owner,package,source));
 assert(payload_copy_publish(left,&left_owner,package,package.serial));locked=false;
 end(1);assert(install(nullptr,0));begin_startup_closed(2,Required);
 locked=true;assert(!payload_copy_current(left));payload_copy_invalidate(left,&left_owner);
 assert(!payload_copy_publish(left,&left_owner,package,package.serial));locked=false;
 // Catalog index values cannot silently regain validity in a new epoch.
 payload_flush_all();end(2);
}
'''
        with tempfile.TemporaryDirectory(prefix='gc-port23-hand-child-', dir='/dev/shm') as temporary:
            root = Path(temporary);(root / 'fixture.cpp').write_text(fixture);executable = root / 'fixture'
            subprocess.run(['g++', '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror', '-DRE4DC_GC_ASSET_GATE=1',
                            '-I', str(GAME / 'platform/include'), str(root / 'fixture.cpp'),
                            str(GAME / 'platform/gc_asset_gate.cpp'), str(GAME / 'platform/gc_asset_members.cpp'),
                            str(GAME / 'platform/gc_asset_payloads.cpp'), '-o', str(executable)], check=True)
            subprocess.run(['/lib64/ld-linux-x86-64.so.2', str(executable)], check=True)

    def test_complete_copy_epoch_blob_and_overwrite_controls(self):
        fixture = r'''
#include "gc_asset_hand_copy.h"
#include <cassert>
using namespace re4dc_gcasset;
int main(){unsigned serial=0;const unsigned source=77;
 auto read=hand_read_begin(serial,source,3,64,32,512);assert(read.source && !hand_read_complete(read,source,3,false).source);
 auto origin=hand_read_complete(read,source,3,true);assert(hand_copy_valid(origin,source,3));assert(!hand_copy_valid(origin,source+1,3) && !hand_copy_valid(origin,source,4));
 assert(!hand_read_begin(serial,source,3,500,32,512).source);assert(!hand_read_begin(serial,source,24,0,32,512).source);assert(!hand_read_begin(serial,0,3,0,32,512).source);
 HandCopyProof cell,slot;auto to_cell=hand_copy_begin(cell,origin,serial,source,3);assert(!cell.source);assert(hand_copy_complete(cell,to_cell,source,3,true));
 // Exact AICA write/readback chain preserves original source, with new owned generations.
 auto to_slot=hand_copy_begin(slot,cell,serial,source,3);assert(hand_copy_complete(slot,to_slot,source,3,true));assert(slot.source==origin.source && slot.token!=origin.token);
 // A partial failed write invalidates the old positive before any completion.
 auto failed=hand_copy_begin(slot,cell,serial,source,3);assert(!hand_copy_complete(slot,failed,source,3,false) && !slot.source);
 // Paused old completion cannot resurrect a newer overwritten/reused slot.
 auto old=hand_copy_begin(slot,cell,serial,source,3);auto newer=hand_copy_begin(slot,cell,serial,source,3);assert(!hand_copy_complete(slot,old,source,3,true));assert(hand_copy_complete(slot,newer,source,3,true));
 auto stale=hand_copy_begin(slot,cell,serial,source,3);assert(!hand_copy_complete(slot,stale,source+1,3,true));hand_copy_invalidate(slot);assert(!hand_copy_complete(slot,stale,source,3,true));
 auto wrong=hand_copy_begin(slot,cell,serial,source,4);assert(!wrong.source && !slot.source);hand_copy_invalidate(cell);auto missing=hand_copy_begin(slot,cell,serial,source,3);assert(!missing.source && !slot.source);
 serial=0x07ffffffU;assert(!hand_read_begin(serial,source,3,0,32,512).source);assert(!hand_copy_begin(slot,origin,serial,source,3).source && !slot.source);
}
'''
        with tempfile.TemporaryDirectory(prefix='gc-port23-hand-copy-', dir='/dev/shm') as temporary:
            root = Path(temporary);(root / 'fixture.cpp').write_text(fixture);executable = root / 'fixture'
            subprocess.run(['g++', '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror', '-DRE4DC_GC_ASSET_GATE=1',
                            '-I', str(GAME / 'platform/include'), str(root / 'fixture.cpp'), '-o', str(executable)], check=True)
            subprocess.run(['/lib64/ld-linux-x86-64.so.2', str(executable)], check=True)


if __name__ == '__main__':unittest.main()
