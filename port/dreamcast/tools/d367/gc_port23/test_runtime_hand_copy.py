"""Fail-closed fixed hand copy tickets; actual writer integration is separate."""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
GAME = HERE.parents[2] / 'game'


class HandCopyTests(unittest.TestCase):
    def test_actual_hand_off_preprocessor_identity_and_safe_pump_placement(self):
        path = 'port/dreamcast/game/coarse_actor_leon_hands.inc'
        original = subprocess.check_output(['git', '-C', str(GAME.parents[2]), 'show', '2de46ed66:' + path], text=True)
        current = (GAME / 'coarse_actor_leon_hands.inc').read_text()
        with tempfile.TemporaryDirectory(prefix='gc-port23-hand-off-', dir='/dev/shm') as temporary:
            root = Path(temporary)
            for header in ['kos/fs.h', 'dc/spu.h', 'dc/sound/sound.h', 'arch/timer.h', 'kos/thread.h', 'kos/mutex.h']:
                target = root / header;target.parent.mkdir(parents=True, exist_ok=True);target.write_text('')
            outputs = []
            for name, source in [('old', original), ('new', current)]:
                target = root / (name + '.cpp');target.write_text(source)
                outputs.append(subprocess.check_output(['g++', '-E', '-P', '-DRE4DC_GC_ASSET_GATE=0',
                    '-I', str(root), '-I', str(GAME), str(target)], text=True))
            # Existing one-line blocks gain diagnostic-only lines. Compare
            # exact preprocessor tokens, retaining complete string literals.
            tokens = lambda text: re.findall(r'"(?:\\.|[^"\\])*"|[A-Za-z_]\w*|\d+|\S', text)
            self.assertEqual(tokens(outputs[0]), tokens(outputs[1]))
        from test_runtime_hooks import function
        for signature in ['extern "C" void re4dc_leon_hands_room_enter()', 'extern "C" void re4dc_leon_hands_weapon(']:
            body = function(current, signature)
            self.assertLess(body.rindex('mutex_unlock(&lh_mutex)'), body.index('gcasset_hand_directory_pump()'))

    def test_actual_cold_source_and_retained_directory_binding(self):
        source = (GAME / 'platform/include/gc_asset_hand_source.inc').read_text()
        fixture = r'''
#include "gc_asset_payloads.h"
#include <cassert>
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <string>
#include <sys/types.h>
using namespace re4dc_gcasset;
std::string logs;bool locked;unsigned io,position,read_bytes,mode;unsigned char disk[256]{};
extern "C" void re4dc_log(const char* fmt,...){assert(!locked && !io);char text[256];va_list args;va_start(args,fmt);vsnprintf(text,sizeof text,fmt,args);va_end(args);logs+=text;}
struct Re4dcIoScope{Re4dcIoScope(){assert(!locked);++io;}~Re4dcIoScope(){--io;}};
using file_t=int;constexpr int FILEHND_INVALID=-1,O_RDONLY=0;
file_t fs_open(const char*,int){assert(io);position=0;return mode==4?-1:7;}
off_t fs_total(file_t){assert(io);return sizeof disk;}
ssize_t fs_read(file_t,void* out,unsigned bytes){assert(io);if(mode==1 && bytes>32)return bytes-1;if(position+bytes>sizeof disk)return -1;memcpy(out,disk+position,bytes);position+=bytes;read_bytes+=bytes;return bytes;}
off_t fs_seek(file_t,unsigned offset,int){assert(io);position=offset;if(mode==2)disk[0]^=1;return offset;}
int fs_close(file_t){assert(io);return 0;}
namespace re4dc_gcasset{bool ensure_disc_catalog(){return true;}}
namespace leon_hand_pack{
constexpr unsigned kMagic=0x3150484c,kVersion=1,kRows=24,kBlobs=24,kSources=48,kSlotBytes[2]={64,64};
unsigned char slot_data[2][64],*slot[2]={slot_data[0],slot_data[1]};
unsigned char rows[24][12],blobs[24][24],srcs[48][4];unsigned nrows,nblobs,nsrcs,file_bytes;
const char* package(){return "/cd/immutable-source";}
''' + source + r'''
}
int main(int argc,char**argv){using namespace leon_hand_pack;mode=argc>1?unsigned(argv[1][0]-'0'):0;
 unsigned header[8]={kMagic,(1U<<16)|kVersion,(1U<<16)|2U,64,64,128,sizeof disk,0};
 memcpy(disk,header,32);for(unsigned i=32;i<sizeof disk;++i)disk[i]=i;
 assert(install(nullptr,0));begin_startup_closed(1,Required);gcasset_hand_startup();
 if(mode==1 || mode==2 || mode==4){assert(!gcasset_hand_source.serial);assert(logs.find(mode==4?"hand-source-open":"hand-source-read")!=std::string::npos);return 0;}
 assert(gcasset_hand_source.serial && !gcasset_hand_slot[0].serial && !gcasset_hand_ready);
 AssetDescription row;assert(describe_checked(gcasset_hand_source.asset,&row));assert(!memcmp(row.digest.bytes,fingerprint(disk,sizeof disk).bytes,32));
 assert(!memcmp(gcasset_hand_directory_sha.bytes,fingerprint(disk,96).bytes,32));
 assert(read_bytes==sizeof disk+32); // full hash and directory prefix share one read
 nrows=1;nblobs=2;nsrcs=1;file_bytes=sizeof disk;
 memcpy(rows,disk+32,12);memcpy(blobs,disk+44,48);memcpy(srcs,disk+92,4);
 locked=true;gcasset_hand_directory_candidate(header);locked=false;assert(gcasset_hand_candidate);
 if(mode==3)rows[0][0]^=1;
 if(mode==5)nrows=0xffffffffU;
 if(mode==6)retire_catalog();
 gcasset_hand_directory_pump();
 if(mode==3 || mode==5 || mode==6)assert(!gcasset_hand_ready && logs.find("hand-directory-")!=std::string::npos);
 else {assert(gcasset_hand_ready);assert(logs.find("GC-ASSET v=")==std::string::npos);}
}
'''
        with tempfile.TemporaryDirectory(prefix='gc-port23-hand-source-', dir='/dev/shm') as temporary:
            root = Path(temporary);(root / 'fixture.cpp').write_text(fixture);executable = root / 'fixture'
            subprocess.run(['g++', '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror', '-DRE4DC_GC_ASSET_GATE=1',
                            '-DRE4DC_LEON_HAND_RETAIN=0', '-I', str(GAME / 'platform/include'), str(root / 'fixture.cpp'),
                            str(GAME / 'platform/gc_asset_gate.cpp'), str(GAME / 'platform/gc_asset_members.cpp'),
                            str(GAME / 'platform/gc_asset_payloads.cpp'), '-o', str(executable)], check=True)
            for mode in range(7):
                subprocess.run(['/lib64/ld-linux-x86-64.so.2', str(executable), str(mode)], check=True)

    def test_controlled_derivation_pending_abort_nested_and_reload(self):
        fixture = r'''
#include "gc_asset_hand_derivation.h"
#include <cassert>
#include <cstdarg>
using namespace re4dc_gcasset;
bool locked;extern "C" void re4dc_log(const char*,...){assert(!locked);}
int main(){assert(install(nullptr,0));begin_startup_closed(1,Required);
 PayloadProof source,slot;int owner;unsigned char bytes[64]{};assert(payload_capture_digest(source,&source,fingerprint("pack",4)));
 assert(payload_copy_register(slot,&owner,bytes,64));unsigned clock=0;
 auto copy=hand_read_complete(hand_read_begin(clock,source.serial,3,128,64,512),source.serial,3,true);
 assert(payload_copy_publish(slot,&owner,source,source.serial));const unsigned original=slot.serial;HandDerivationState pending;
 locked=true;auto ticket=hand_derive_begin(pending,slot,copy,source.serial,3,bytes+16,32,bytes+16,32);
 assert(ticket==original && !slot.serial);bytes[16]=1;
 assert(hand_derive_end(pending,slot,copy,source.serial,3,ticket,true));assert(slot.serial==original);
 // An early failure/abort never restores even the same original copy.
 ticket=hand_derive_begin(pending,slot,copy,source.serial,3,bytes+16,32,bytes+16,32);
 assert(!hand_derive_end(pending,slot,copy,source.serial,3,ticket,false) && !slot.serial);
 assert(payload_copy_publish(slot,&owner,source,source.serial));
 // Unrecognized stream extent and nested writes permanently revoke readiness.
 assert(!hand_derive_begin(pending,slot,copy,source.serial,3,bytes+16,32,bytes+15,32) && !slot.serial);
 assert(payload_copy_publish(slot,&owner,source,source.serial));ticket=hand_derive_begin(pending,slot,copy,source.serial,3,bytes+16,32,bytes+16,32);
 assert(!hand_derive_begin(pending,slot,copy,source.serial,3,bytes+16,32,bytes+16,32));
 assert(!hand_derive_end(pending,slot,copy,source.serial,3,ticket,true));
 assert(payload_copy_publish(slot,&owner,source,source.serial));ticket=hand_derive_begin(pending,slot,copy,source.serial,3,bytes+16,32,bytes+16,32);
 // A copied/reused slot cannot be resurrected by an old preparation end.
 payload_copy_invalidate(slot,&owner);
 copy=hand_read_complete(hand_read_begin(clock,source.serial,3,128,64,512),source.serial,3,true);
 assert(payload_copy_publish(slot,&owner,source,source.serial));assert(slot.serial!=ticket);
 assert(!hand_derive_end(pending,slot,copy,source.serial,3,ticket,true) && !slot.serial);
 assert(payload_copy_publish(slot,&owner,source,source.serial));ticket=hand_derive_begin(pending,slot,copy,source.serial,3,bytes+16,32,bytes+16,32);locked=false;
 retire_catalog();locked=true;assert(!hand_derive_end(pending,slot,copy,source.serial,3,ticket,true));locked=false;
}
'''
        with tempfile.TemporaryDirectory(prefix='gc-port23-hand-derive-', dir='/dev/shm') as temporary:
            root = Path(temporary);(root / 'fixture.cpp').write_text(fixture);executable = root / 'fixture'
            subprocess.run(['g++', '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror', '-DRE4DC_GC_ASSET_GATE=1',
                            '-I', str(GAME / 'platform/include'), str(root / 'fixture.cpp'),
                            str(GAME / 'platform/gc_asset_gate.cpp'), str(GAME / 'platform/gc_asset_members.cpp'),
                            str(GAME / 'platform/gc_asset_payloads.cpp'), '-o', str(executable)], check=True)
            subprocess.run(['/lib64/ld-linux-x86-64.so.2', str(executable)], check=True)

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
