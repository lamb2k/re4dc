"""partner_pack_test.py (lane ps2cast 2026-10-15, PS2_ASHLEY_ROOMS) <game dir> <out dir> <room> <room package|-> <partner package> [extra -D flags...]
Host check of PS2_ASHLEY_ROOMS: the target's validator (coarse_actor_registry_pack_check.inc) on a room package and its
partner package (types extracted as model_registry_pack_test.py does)."""
import os, subprocess, sys
G, out, room, a, b = sys.argv[1:6]
extra = sys.argv[6:]
os.makedirs(out, exist_ok=True)
mat = open(os.path.join(G, 'coarse_actor_material.inc')).read()
reg = open(os.path.join(G, 'coarse_actor_owner_registry.inc')).read()
x, y = mat.index('struct Digest'), mat.index('struct SourceBlob'); y = mat.index('\n', y) + 1
c = reg.index('namespace nmr {'); d = reg.index('constexpr unsigned kRegDescriptors=16'); d = reg.index('\n', d) + 1
types = ('#pragma once\n#include <cstdint>\nnamespace re4dc_material {\n' + mat[x:y] + '#include "actor_material_records.inc"\n}\n'
         + reg[c:d])
s = reg.index('nmr::Chunk registry_geom_view('); e = reg.index('\n}', s) + 2
types += '\n' + reg[s:e] + '\n'
open(os.path.join(out, 'pack_test_types.h'), 'w').write(types)
exe = os.path.join(out, 'ptest')
cc = ['g++', '-std=c++17', '-O1', '-w', '-DRE4DC_NMR_ASHLEY=2', '-DRE4DC_NMR_SLOTS=1', '-DRE4DC_NMR_MASK=1',
      '-DRE4DC_NMR_DROP_BUMP=1', '-DRE4DC_NMR_BONES=64', '-DRE4DC_NMR_FACTS=72', '-DRE4DC_ACTOR_PL08=1',
      '-DRE4DC_NMR_PARTNER=1'] + extra + ['-I', out, '-I', G, '-I', os.path.join(G, 'platform', 'include'),
      os.path.join(G, '..', 'tools', 'd367', 'model_registry_pack_test.cpp'), '-o', exe]
r = subprocess.run(cc, capture_output=True, text=True)
if r.returncode:
    sys.exit('build failed:\n' + r.stderr[-3000:])
args = [exe, room] + ([a] if a != '-' else []) + ['+' + b if a != '-' else b]
print(subprocess.run(args, capture_output=True, text=True).stdout, end='')
