#!/usr/bin/env python3
"""Tiny real host compilation/behavior checks; no target build, assets or guest."""
from pathlib import Path
import os
import subprocess
import tempfile
from source_guards import check

here = Path(__file__).resolve().parent
game = here.parents[2] / 'game'
cxx = os.environ.get('CXX', 'g++')
check(game)

def run(args, **kwargs):
    return subprocess.run(args, check=True, text=True, capture_output=True, **kwargs)

with tempfile.TemporaryDirectory(prefix='world-meter23-') as scratch:
    tmp = Path(scratch)
    common = [cxx, '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror', '-I'+str(game)]
    run(common + [str(here/'test_meter.cpp'), '-o', str(tmp/'meter')])
    print(run([str(tmp/'meter')]).stdout.strip())
    run(common + ['-DRE4DC_WORLD_DRAW_METER=1', '-I'+str(here/'stubs'),
                  str(here/'test_runtime.cpp'), str(game/'world_draw_meter.cpp'), '-o', str(tmp/'runtime')])
    print(run([str(tmp/'runtime')]).stdout.strip())
    # Actual object identity of the disabled expression wrapper (including undefined
    # pass/view tokens), default and explicit off. No synthetic expected string match.
    fixture = str(here/'off_fixture.cpp')
    for name, flags in [('base',['-DBASELINE']), ('default',[]), ('off',['-DRE4DC_WORLD_DRAW_METER=0'])]:
        run(common + flags + ['-c', fixture, '-o', str(tmp/(name+'.o'))])
    assert (tmp/'base.o').read_bytes() == (tmp/'default.o').read_bytes() == (tmp/'off.o').read_bytes()
    run(common + ['-c', str(game/'world_draw_meter.cpp'), '-o', str(tmp/'empty.o')])
    assert not run(['nm', str(tmp/'empty.o')]).stdout.strip()
    print('world meter: default/explicit-off wrapper objects identical; disabled runtime has zero symbols PASS')
    # Real Make evaluation verifies off adds no object/flags and malformed activation fails.
    mk = f'''.DEFAULT_GOAL := all
OBJDIR := {tmp}/obj
TARGET := {tmp}/program
include {game}/worldmeter.mk
$(info OBJS=$(PLATFORM_OBJS))
all: ; @:
'''
    off = run(['make','--no-print-directory','-f','-','WORLD_DRAW_METER=0'], input=mk)
    assert 'OBJS=\n' in off.stdout
    on = run(['make','--no-print-directory','-f','-','WORLD_DRAW_METER=1','PS2_WORLD_DRAW=1'], input=mk)
    assert 'world_draw_meter.o' in on.stdout
    for flags in [['WORLD_DRAW_METER=2'], ['WORLD_DRAW_METER=1','PS2_WORLD_DRAW=0']]:
        result = subprocess.run(['make','--no-print-directory','-f','-']+flags, input=mk, text=True, capture_output=True)
        assert result.returncode != 0
    print('world meter: real Make off/on/invalid/dependency evaluation PASS')
print('No target object/link, full-program identity, Flycast, console or timing acceptance is implied.')
