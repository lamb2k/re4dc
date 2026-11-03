#!/usr/bin/env python3
# lane bakeall: ps2_room_extract.py with the surviving JADERLINK tools (the pinned dat.exe is gone; sky27's
# DATUDAS_TOOL.exe ebc69dae.. is used instead; the SMD tool matches its pin 9fc3d21b..). Validate with --compare.
import sys
sys.path.insert(0, '/root/work/lanes/bakeall/port/dreamcast/tools')
from pathlib import Path
import ps2_room_extract as x
x.DAT_EXE = Path('/root/probe/lanes/sky27/tools/dat/JADERLINK_DATUDAS_TOOL.exe')
x.SMD_EXE = Path('/root/probe/lanes/sky27/tools/smd/RE4_PS2_SCENARIO_SMD_TOOL.exe')
x.PINS['dat'] = x.sha(x.DAT_EXE) if hasattr(x, 'sha') else x.PINS['dat']
sys.argv[0] = 'ps2_room_extract.py'
x.main()
