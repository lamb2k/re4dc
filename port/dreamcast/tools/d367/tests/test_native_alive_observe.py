#!/usr/bin/env python3
"""Compile the actual native-load census guards against protected game-state stubs."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[3] / "game/dbgwarp_bridge.cpp"


def function(source, name):
    start = source.index(name + "()")
    begin = source.index("{", start)
    depth = 1
    end = begin + 1
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    return source[source.rfind("\n", 0, start) + 1:end]


class NativeLoadAliveObserve(unittest.TestCase):
    def test_lifetime_and_no_gameplay_mutation(self):
        compiler = shutil.which("c++") or shutil.which("g++")
        self.assertIsNotNone(compiler, "host C++ compiler required")
        source = SOURCE.read_text()
        actual = "\n".join(function(source, name) for name in (
            "native_alive_observe_enabled", "native_alive_room_enter", "native_alive_poll"))
        program = r"""
#include <cassert>
#include <cstdint>
#include <cstring>
#include <cstdarg>
#include <cstdio>
#include <string>
#include <vector>
struct Global {
    std::uint16_t room_id;
    std::uint8_t Rno0, Rno1;
    std::uint32_t flags, chapter, inventory, life;
};
struct Warp {
    bool active, observe_ready;
    unsigned room, alive_period, room_frames, alive_last, observe_room;
};
Global game{}, *pG = nullptr;
void* pPL = nullptr;
Warp wp{};
unsigned actor_reads, reports;
std::vector<std::string> messages;
void re4dc_log(const char* format, ...) {
    char line[256];
    va_list a; va_start(a, format); vsnprintf(line, sizeof(line), format, a); va_end(a);
    messages.emplace_back(line);
}
void alive_log_poll() {
    if (wp.alive_period && wp.room_frames % wp.alive_period == 0 &&
        wp.room_frames != wp.alive_last) {
        wp.alive_last = wp.room_frames;
        ++actor_reads; ++reports;
    }
}
""" + actual + r"""
void reset() {
    wp = Warp{}; game = Global{0x200, 3, 0, 0xabcdef01, 6, 0x300006, 1440};
    pG = &game; pPL = &game; actor_reads = reports = 0; messages.clear();
}
int main() {
    reset();
    native_alive_room_enter(); native_alive_poll();
    assert(!wp.observe_ready && !wp.active && !actor_reads && !wp.room_frames);
    wp.alive_period = 30; pG = nullptr;
    native_alive_room_enter(); native_alive_poll(); assert(!wp.observe_ready);
    pG = &game; const Global original = game;
    native_alive_room_enter();
    assert(wp.observe_ready && wp.observe_room == 0x200 && wp.room_frames == 0);
    assert(!wp.active && wp.room == 0 && messages.size() == 1);
    assert(messages.back().back() == '\n');
    // Inactive title/card/room-jump phases must not touch the actor manager.
    for (unsigned phase : {0u, 1u, 2u, 4u, 5u, 6u}) {
        game.Rno0 = phase; native_alive_poll(); assert(!actor_reads && !wp.room_frames);
    }
    game.Rno0 = 3; game.Rno1 = 1; native_alive_poll();
    assert(!actor_reads && !wp.room_frames);
    game.Rno1 = 0; pPL = nullptr; native_alive_poll();
    assert(!actor_reads && !wp.room_frames);
    pPL = &game; game.room_id = 0x202; native_alive_poll();
    assert(!actor_reads && !wp.room_frames);  // requires that room's entry hook
    game = original;
    for (unsigned i = 0; i < 60; ++i) native_alive_poll();
    assert(actor_reads == 2 && reports == 2 && wp.room_frames == 60);
    assert(std::memcmp(&game, &original, sizeof(game)) == 0);
    assert(!wp.active && wp.room == 0);  // title/placement/input/damage guards stay closed
    game.room_id = 0x202; native_alive_room_enter();
    assert(wp.room_frames == 0 && wp.observe_room == 0x202);
    for (unsigned i = 0; i < 30; ++i) native_alive_poll();
    assert(actor_reads == 3 && reports == 3);  // new room's independent clock
    // A real warp, including pending after-reset room directives, retains its old path.
    reset(); wp.alive_period = 30; wp.active = true;
    native_alive_room_enter(); native_alive_poll();
    assert(!wp.observe_ready && !actor_reads && !wp.room_frames);
    reset(); wp.alive_period = 30; wp.room = 0x201;
    native_alive_room_enter(); native_alive_poll();
    assert(!wp.observe_ready && !wp.active && !actor_reads && !wp.room_frames);
    return 0;
}
"""
        with tempfile.TemporaryDirectory(prefix="native-alive-observe-") as folder:
            cpp = Path(folder) / "guard.cpp"
            binary = Path(folder) / "guard"
            cpp.write_text(program)
            build = subprocess.run([compiler, "-std=c++11", "-Wall", "-Wextra", "-Werror",
                                    str(cpp), "-o", str(binary)], capture_output=True, text=True)
            self.assertEqual(build.returncode, 0, build.stderr)
            run = subprocess.run([str(binary)], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)


if __name__ == "__main__":
    unittest.main()
