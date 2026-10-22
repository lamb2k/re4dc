"""Supplemental call-site guards; behavioral/compiler tests live in run_tests.py."""
from pathlib import Path
import re

def check(game: Path):
    world=(game/'platform/native_ps2_world.cpp').read_text()
    calls=re.findall(r'RE4DC_WORLD_MEASURE\((Opaque|PunchThrough|Translucent|FarShell),state\.far,',world)
    assert len(calls)==14, len(calls)
    # Every actual world draw call (not declarations) is nested in a measurement.
    for line in world.splitlines():
        if re.search(r'(?:=|;|\{)(?:draw\.draw(?:_kernel)?\([012]\)|re4dc_ps2_mesh_draw\([012],state\.far\)|re4dc_far_shell_draw\(state\.far,full\))',line):
            raise AssertionError('unwrapped world draw: '+line)
    ui=(game/'platform/native_ui.cpp').read_text()
    skip=ui.split('extern "C" void re4dc_ui_begin_skip(){',1)[1].split('#endif\n#if RE4DC_DOOR_FREEZE',1)[0]
    assert 're4dc_world_meter_' not in skip
    assert '++frame;\n#if defined(RE4DC_WORLD_DRAW_METER)' in ui
    assert 'world_meter_begin_discards=stream_discards' in ui
    assert 'stream_discards==world_meter_begin_discards' in ui
    assert 'const unsigned world_meter_discards=stream_discards' not in ui
    assert 'shown && meter_resolved>=0' in ui
    assert 'present && meter_post>=0' in ui
    assert 're4dc_world_meter_outcome(meter_token,meter_frame,present && !failure)' in ui
    qa=(game/'qa_menu.cpp').read_text()
    assert qa.count('re4dc_world_meter_snapshot(g_game.room)')==1
    assert 'world transformed=NA submitted=NA bytes=NA strips=NA' in qa
    print('world meter: all 14 pass call sites wrapped; skip paths excluded; snapshot and unknown-counter guards PASS')
