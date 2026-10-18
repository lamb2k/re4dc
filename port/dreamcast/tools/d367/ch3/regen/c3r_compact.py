"""c3r_compact.py TOOLS MIRROR_PY SRC_DAS TEXDIR DEST: compact31.py/compact32.py compaction step only
(ui.compact_room(src, tex, dest, compact_mips=True)) with ui.mirror swapped to MIRROR_PY ('-' keeps the tree's)."""
import sys, importlib.util, hashlib
from pathlib import Path
tools, mpy, src, tex, dest = sys.argv[1:6]
sys.path[:0] = [tools]
import prepare_native_ui as ui
if mpy != '-':
    sp = importlib.util.spec_from_file_location('le_mirror_alt', mpy); m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m); ui.mirror = m
r = ui.compact_room(Path(src), Path(tex), Path(dest), compact_mips=True)
for p in sorted(Path(dest).glob('*.[ad]ar')):
    print(p.name, hashlib.sha256(p.read_bytes()).hexdigest()[:16])
