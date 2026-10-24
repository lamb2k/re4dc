"""Fail-closed fixed hand copy tickets; actual writer integration is separate."""
from pathlib import Path
import subprocess
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
GAME = HERE.parents[2] / 'game'


class HandCopyTests(unittest.TestCase):
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
