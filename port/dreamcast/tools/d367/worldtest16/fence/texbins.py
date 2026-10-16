#!/usr/bin/env python3
"""texbins.py <mesh> <sidecar> KEY... (env MAXV: only meshes with at most MAXV source vertices): mesh bins that have a
part using one of these texture keys (R4PW meta crc). Prints the csv on stdout, bin:source_vertices on stderr."""
import os, sys, struct, importlib.util
T = '/root/probe/codex-cpu-t15-20261016/tree/port/dreamcast/tools'
sys.path.insert(0, T)
spec = importlib.util.spec_from_file_location('F', T + '/ps2_world_far_lod.py')
F = importlib.util.module_from_spec(spec); spec.loader.exec_module(F)
p = F.read(open(sys.argv[1], 'rb').read()); b = open(sys.argv[2], 'rb').read()
keys = {int(k, 16) for k in sys.argv[3:]}
MAXV = int(os.environ.get('MAXV', '1000000'))
tex = [struct.unpack_from('<I', b, 32 + 16 * i)[0] for i in range(len(p['parts']))]
sel = [m for m in p['meshes'] if m[3] <= MAXV and any(tex[pi] in keys for pi in range(m[6], m[6] + m[7]))]
sys.stderr.write(' '.join('0x%x:%d' % (m[0], m[3]) for m in sel) + '\n')
print(','.join('0x%x' % x for x in sorted({m[0] for m in sel})))
