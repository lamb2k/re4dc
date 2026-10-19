#!/usr/bin/env python3
"""Run the actual opt-in warp phase transition against completed/pending source events."""
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[5]
GAME = ROOT / 'port/dreamcast/game'
source = (GAME / 'dbgwarp_bridge.cpp').read_text()

def function(name):
    start = source.index('static ', source.index(name) - 20)
    brace = source.index('{', start)
    depth = 1
    end = brace + 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end]

code = r'''
#include <cassert>
#include <cstdint>
using u32 = uint32_t; using u16 = uint16_t; using u8 = uint8_t;
struct Global {u16 room_id; u32 Status_flg[4];} global, *pG = &global;
struct Scene {int event_start_cnt;} SceSys;
struct Warp {
 bool kill_next_pending, has_kill, kill_done;
 u32 kill_next_id, kill_next_frame, kill_next_room, kill_next_kind, kill_next_rep, kill_next_gap;
 u32 room_frames; int kill_id; u32 kill_frame; u16 kill_room; u8 kill_kind;
 u32 kill_rep, kill_gap; void* kill_em; u32 kill_hits, kill_watch; short kill_part; bool kill_near;
} wp;
int logs;
void re4dc_log(const char*, ...) {++logs;}
'''
code += function('kill_phase_args_valid') + '\n' + function('kill_phase_poll')
code += r'''
void setup() {
 wp = {}; global = {}; SceSys = {}; pG = &global; logs = 0;
 wp.kill_next_pending = wp.has_kill = wp.kill_done = true;
 wp.kill_next_id = 0x2d; wp.kill_next_frame = 600; wp.kill_next_room = 0x213;
 wp.kill_next_kind = 1; wp.kill_next_rep = 30; wp.kill_next_gap = 30;
 wp.room_frames = 600; global.room_id = 0x213;
 wp.kill_id = 0x4d; wp.kill_frame = 80; wp.kill_room = 0x213; wp.kill_kind = 13;
 wp.kill_em = reinterpret_cast<void*>(1234); wp.kill_hits = 94; wp.kill_watch = 40;
 wp.kill_part = 5; wp.kill_near = true;
}
void unchanged() {
 kill_phase_poll(); assert(logs == 0 && wp.kill_id == 0x4d && wp.kill_hits == 94);
 assert(wp.kill_em == reinterpret_cast<void*>(1234));
}
int main() {
 assert(kill_phase_args_valid(0x2d,600,0x213,1,30,30));
 assert(!kill_phase_args_valid(0x60,600,0x213,1,30,30));
 assert(!kill_phase_args_valid(0x2d,0,0x213,1,30,30));
 assert(!kill_phase_args_valid(0x2d,0xffffffff,0x213,1,30,30));
 assert(!kill_phase_args_valid(0x2d,600,0,1,30,30));
 assert(!kill_phase_args_valid(0x2d,600,0x400,1,30,30));
 assert(!kill_phase_args_valid(0x2d,600,0x213,256,30,30));
 assert(!kill_phase_args_valid(0x2d,600,0x213,1,256,30));
 assert(!kill_phase_args_valid(0x2d,600,0x213,1,30,0));
 assert(!kill_phase_args_valid(0x2d,600,0x213,1,30,60001));
 setup(); wp.kill_next_pending = false; unchanged();
 setup(); wp.has_kill = false; unchanged();
 setup(); wp.kill_done = false; unchanged();
 setup(); pG = nullptr; unchanged();
 setup(); global.room_id = 0x205; unchanged();
 setup(); wp.room_frames = 599; unchanged();
 setup(); global.Status_flg[1] = 0x10000000; unchanged();
 setup(); SceSys.event_start_cnt = 1; unchanged();
 setup(); kill_phase_poll();
 assert(logs == 1 && !wp.kill_next_pending && !wp.kill_done);
 assert(wp.kill_id == 0x2d && wp.kill_frame == 600 && wp.kill_room == 0x213 && wp.kill_kind == 1);
 assert(wp.kill_rep == 30 && wp.kill_gap == 30 && !wp.kill_em && !wp.kill_hits && !wp.kill_watch);
 assert(!wp.kill_part && !wp.kill_near);
 wp.kill_done = true; kill_phase_poll(); assert(logs == 1); // cannot execute twice
}
'''
with tempfile.TemporaryDirectory(prefix='castle18-warp-phase-') as d:
    d = Path(d)
    cpp = d / 'test.cpp'
    exe = d / 'test'
    cpp.write_text(code)
    subprocess.run(['g++', '-std=c++11', '-Wall', '-Wextra', '-Werror', str(cpp), '-o', str(exe)], check=True)
    subprocess.run([str(exe)], check=True)
    makefile = d / 'test.mk'
    makefile.write_text(f'OBJDIR={d}/obj\nTARGET=phase-test\nall:; @true\ninclude {GAME}/dbgwarp.mk\n')
    for args, good in [([], True), (['DBG_WARP=1','WARP_KILL_PHASE=1'], True),
                       (['DBG_WARP=0','WARP_KILL_PHASE=1'], False), (['WARP_KILL_PHASE=2'], False)]:
        p = subprocess.run(['make','-s','-f',str(makefile),'-n','all',*args], cwd=GAME, capture_output=True, text=True)
        assert (p.returncode == 0) == good, (args, p.stdout, p.stderr)
print('PASS: actual phase waits for death, room, frame and complete source event; executes once; invalid arguments/build modes refuse')
