import sys
from pathlib import Path
sys.path.insert(0, '/root/work/lanes/fxproof26')
T = '/root/work/lanes/fxproof26/wt/port/dreamcast/tools'
sys.path[:0] = [T, T + '/d367/vram', T + '/d367/test12fx']
import fx_ps2_sheet as SH
from assetpipe.rooms import GcIso
import sigs
E = Path('/root/work/lanes/purge-audit26/ev')
want = set(l.split()[0] for l in open(E / 'keys15.txt'))
p = E / 'core.das'
if not p.exists():
    g = GcIso('/root/work/re4-dreamcast/orig/G4BE08/re4_debug_disc1.iso')
    p.write_bytes(g.read(g.find('etc/core.das') or 'etc/core.das'))
pics = SH.gc_pictures([('etc/core.das', p)])
fs, ft = open(E / 'gc15.sig', 'wb'), open(E / 'gc15.tsv', 'w')
n = 0
for ctx, l in sorted(pics.items()):
    for key, w, h, px in l:
        if key in want:
            fs.write(sigs.sig_rgba(w, h, px)); ft.write('%s\t%s\t%d\t%d\n' % (key, ctx, w, h)); n += 1
print('rows', n)
