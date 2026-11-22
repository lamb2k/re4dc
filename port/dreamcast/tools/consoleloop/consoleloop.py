#!/usr/bin/env python3
"""consoleloop.py: RE4's entry to the console link (lane eng-loop, 2026-11-19; a thin wrapper since lane ql-core,
2026-11-22). The protocol, the PC tool and its host tests are dc-qalink 0.2's (the submodule
port/dreamcast/engine/loader/dc-qalink, pinned by this repository; docs/engine/CONSOLE_LOOP.md section 16). This file
only finds that tool and runs it with the same arguments, so RE4's scripts keep one name:

  python consoleloop.py --udp <console> status
  python consoleloop.py --udp <console> run PROG/E1.BIN --args "..." --deadline 900 --files <pack folder> --out <dir>
  python consoleloop.py relay-local            (Flycast: before the loader boots)
  python consoleloop.py --help                 (dc-qalink's own help: every sub-command)

The loader refuses a PC tool of another protocol version and the tool refuses the loader's: the submodule pin keeps
the two the same commit.
"""
import os, runpy, sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.normpath(os.path.join(HERE, '..', '..', 'engine', 'loader', 'dc-qalink', 'pc', 'dcql_loop.py'))

if __name__ == '__main__':
    if not os.path.isfile(TOOL):
        sys.exit('consoleloop: %s is missing (git submodule update --init port/dreamcast/engine/loader/dc-qalink)' % TOOL)
    sys.argv[0] = TOOL
    sys.path.insert(0, os.path.dirname(TOOL))
    runpy.run_path(TOOL, run_name='__main__')
