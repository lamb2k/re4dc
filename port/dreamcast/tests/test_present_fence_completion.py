"""Check the actual async presentation fence across timeout/completion races."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]

def function(source, signature):
    start = source.index(signature)
    pos = source.index('{', start) + 1
    depth = 1
    while depth:
        depth += (source[pos] == '{') - (source[pos] == '}')
        pos += 1
    return source[start:pos]

class PresentFenceCompletion(unittest.TestCase):
    def test_actual_async_fence(self):
        source = (ROOT / 'port/dreamcast/game/platform/native_ui.cpp').read_text()
        code = r"""
#include <cassert>
#include <cstdint>
#include <stdexcept>
unsigned present_submitted, present_resolved, present_failures, present_reported;
unsigned fence_blocked, fence_timeouts, waits, reports;
std::uint64_t fence_wait_us, clock_us;
bool pending, complete_before_return;
int wait_result;
int pvr_present_pending() { return pending; }
int pvr_present_wait() {
    ++waits;
    clock_us += 100000;
    if(complete_before_return) pending = false;
    return wait_result;
}
std::uint64_t timer_us_gettime64() { return clock_us; }
void re4dc_missing(const char*) { ++reports; throw std::runtime_error("fatal"); }
""" + function(source, 'void present_report()') + "\n" + function(source, 'void present_fence()') + r"""
void reset() {
    present_submitted=17; present_resolved=16; present_failures=present_reported=0;
    fence_blocked=fence_timeouts=waits=reports=0; fence_wait_us=clock_us=0;
    pending=true; complete_before_return=true; wait_result=0;
}
int main() {
    reset(); pending=false; present_resolved=present_submitted;
    present_fence(); assert(waits==0 && fence_blocked==0 && reports==0);

    reset(); present_fence();
    assert(waits==1 && !pending && present_resolved==17 && reports==0);
    assert(fence_blocked==1 && fence_wait_us==100000 && fence_timeouts==0);

    // KOS times out and queues the waiter with a negative saved return value.
    // The IRQ then completes presentation before that waiter resumes.
    reset(); wait_result=-1;
    present_fence();
    assert(waits==1 && !pending && present_resolved==17 && reports==0);
    assert(fence_blocked==1 && fence_wait_us==100000 && fence_timeouts==0);

    // A genuinely pending frame must still halt before the caller uploads VRAM.
    reset(); wait_result=-1; complete_before_return=false;
    bool fatal=false, upload=false;
    try { present_fence(); upload=true; } catch(const std::runtime_error&) { fatal=true; }
    assert(fatal && !upload && pending && reports==1);
    assert(fence_timeouts==1 && (present_failures&1));
}
"""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            (path / 'check.cpp').write_text(code)
            subprocess.run(['g++', '-std=c++17', '-fsanitize=address,undefined',
                            '-fno-omit-frame-pointer', str(path / 'check.cpp'),
                            '-o', str(path / 'check')], check=True)
            subprocess.run([str(path / 'check')], check=True)

if __name__ == '__main__':
    unittest.main()
