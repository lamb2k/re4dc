#!/usr/bin/env python3
"""Exercise the source retrace watchdog and QA pause-exit statements on the host.

No game assets or Dreamcast hardware are needed. This tests the 60-second boundary,
including the first retrace after the menu, rather than weakening the watchdog.
"""
import pathlib
import re
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[5]
bridge = (ROOT / "port/dreamcast/game/dbgwarp_bridge.cpp").read_text()
main = (ROOT / "src/game/main.cpp").read_text()


def function(text, name):
    start = text.index("void " + name + "()")
    begin = text.index("{", start)
    depth = 1
    end = begin + 1
    while depth:
        depth += (text[end] == "{") - (text[end] == "}")
        end += 1
    return re.sub(r"^#line[^\n]*\n", "", text[start:end], flags=re.M)


qa = bridge[bridge.index("bool qa_poll()"):]
repair = re.search(r"vsync_cnt = 0;\s*pG->System_flg = [^;]+;", qa).group()
watchdog = function(main, "haltExecCheck")
retrace = function(main, "postVSyncCallback")
program = r"""
#include <cassert>
#include <cstdio>
#include <cstdint>
using u32 = uint32_t;
struct Global { u32 System_flg; } global, *pG = &global;
volatile int vsync_cnt;
bool halted;
int DBIsDebuggerPresent() { return 0; }
int GetSystemVcnt() { return 2; }
void iTaskSuspend() {}
#define RE4DC_TAIL_VB() ((void)0)
#define HALT() (halted = true)
""" + watchdog + "\n" + retrace + r"""
void resume(u32 keep) {
""" + repair + r"""
}
int main() {
    constexpr u32 disabled = 0x20000000, unrelated = 0x04012345;
    unsigned cases = 0;
    // Source watchdog still stops a real stalled frame, exactly at the original boundary.
    for (int start : {0, 3598, 3599, 3600, 7200}) {
        vsync_cnt = start; pG->System_flg = unrelated; halted = false;
        postVSyncCallback();
        assert(halted == (start + 1 > 3599)); ++cases;
    }
    // A long intentional menu suppresses the check. The old exit reproduces the report.
    vsync_cnt = 4000; pG->System_flg = unrelated | disabled; halted = false;
    postVSyncCallback(); assert(!halted);
    pG->System_flg &= ~disabled;
    postVSyncCallback(); assert(halted); ++cases;
    for (u32 keep : {0u, disabled}) {
        for (int elapsed : {0, 3599, 3600, 4000, 7200}) {
            pG->System_flg = unrelated | disabled; vsync_cnt = elapsed; halted = false;
            resume(keep);
            assert(vsync_cnt == 0);
            assert(pG->System_flg == (unrelated | keep));
            postVSyncCallback(); assert(!halted); ++cases;
            // Restoring normal play must not leave the watchdog disabled.
            if (!keep) {
                vsync_cnt = 3599;
                postVSyncCallback(); assert(halted); ++cases;
            }
        }
    }
    std::printf("PASS %u source watchdog / QA pause-exit cases\n", cases);
}
"""
program = "#include <initializer_list>\n" + program
with tempfile.TemporaryDirectory(prefix="qa-menu-heartbeat-") as folder:
    cpp = pathlib.Path(folder) / "test.cpp"
    exe = pathlib.Path(folder) / "test"
    cpp.write_text(program)
    subprocess.run(["g++", "-std=c++20", "-O2", "-fsanitize=undefined,address",
                    str(cpp), "-o", str(exe)], check=True)
    subprocess.run([str(exe)], check=True)
