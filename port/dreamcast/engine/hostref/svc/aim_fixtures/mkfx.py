"""mkfx.py <bell-ganado.txt> <out dir>: the aim fixtures (lane eng-e1g) from bell-ganado, 600 ticks. Leon resumes facing
yaw -2.0 (towards where the walking Ganado 0x14 circles 2000-3000 units away) and aims (R) from tick 150 to 590, the
stick sweeping the laser left for 30 ticks, resting 10, right for 30, resting 10, ...; aimfire-ganado adds a shot
(A held two ticks) every 10 ticks from 160, the stick kept as the sweep has it."""
import sys, os
src, out = sys.argv[1], sys.argv[2]
base = [l for l in open(src) if not l.startswith('#') and not l.startswith('pad')]
base = [l.replace('ticks 300', 'ticks 600') for l in base]
base = [(' '.join(l.split()[:4] + ['0xc0000000'] + l.split()[5:]) + '\n') if l.startswith('resume') else l for l in base]

def stick(t):
    if t < 150 or t >= 590: return 0
    k = (t - 150) % 80
    if k < 30: return -80
    if 40 <= k < 70: return 80
    return 0

def pads(fire):
    rows, last = [], None
    for t in range(0, 600):
        b = 0x20 if 150 <= t < 590 else 0
        if fire and b and t >= 160 and (t - 160) % 10 < 2: b |= 0x100
        s = stick(t)
        st = (b, s)
        if st != last:
            trig = ' 0 0 0 192' if b & 0x20 else ''
            rows.append(f'pad {t} 0x{b:04x} {s} 0{trig}\n')
            last = st
    return rows

hdr = ['# %s (lane eng-e1g, s/mkfx.py): bell-ganado (fixtures/bell-ganado.txt, its header there), 600 ticks. Leon resumes\n',
       '# facing yaw -2.0 (0xc0000000), towards where the walking Ganado 0x14 circles, and aims (R) from tick 150 to 590,\n',
       '# the stick sweeping the laser across it (left 30 ticks, rest 10, right 30, rest 10). %s\n']
for name, fire, note in (('aim-ganado', False, 'No shot.'),
                         ('aimfire-ganado', True, 'A shot (A held two ticks) every 10 ticks from 160; run with a magazine.')):
    with open(os.path.join(out, name + '.txt'), 'w') as f:
        f.write(hdr[0] % name + hdr[1] + hdr[2] % note)
        f.writelines(base)
        f.writelines(pads(fire))
    print(name, len(pads(fire)), 'pad lines')
