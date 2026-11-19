import sys
sys.path.insert(0, '/root/work/lanes/world-ch31/port/dreamcast/tools')
import ps2_objects as po
pb = po.pb
W = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1].endswith('/') else '/root/work/lanes/world-ch31-scratch/cp32/ps2/'
for r in [a for a in sys.argv[1:] if not a.endswith('/')]:
    b = open(W + r + '.dat', 'rb').read()
    pe = {i + 4: (t, x) for i, t, x in pb.dat_entries(b)}
    etm = next((x for t, x in pe.values() if t == 'ETM'), None)
    names = [n for n, s, e in po.etm_entries(etm, '<')] if etm else None
    print(r, names)
