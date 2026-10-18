"""aica_search.py TOOLS IN TARGET_SHA CACHE OUT [--layout a,b,...]... [--slots 8,6,5]
Reproduce a prebuilt AICA disc file whose recipe output is lost: convert the unconverted sound blocks of IN with every
combination of caps (aica_banks.CAPS or 'raw' = left unconverted) under each candidate layout, exactly as
aica_banks.fit / build write a block (HDR + image, zero pad), and stop at the combination whose sha256 equals TARGET.
Only an exact sha match is accepted (it proves the caps and layout)."""
import hashlib, itertools, struct, sys, os
tools = sys.argv[1]; sys.path.insert(0, tools)
import aica_banks as A
inp, target, cache, out = sys.argv[2:6]
layouts = []; slots = None; blocks_filter = None
a = sys.argv[6:]
i = 0
while i < len(a):
    if a[i] == '--layout':
        layouts.append([int(x) for x in a[i + 1].split(',')]); i += 2
    elif a[i] == '--types':
        blocks_filter = {int(x) for x in a[i + 1].split(',')}; i += 2
    else:
        raise SystemExit('arg? ' + a[i])
d0 = open(inp, 'rb').read()
todo = []
for (t, mo, ms, ao, asz) in A.sound_blocks(d0, 0) or []:
    if struct.unpack_from('<I', d0, ao)[0] == A.MAGIC:
        continue
    if blocks_filter is not None and t not in blocks_filter:
        continue
    table, samples, coefs = A.wavetable(d0, t, mo, ms)
    if samples:
        todo.append(dict(t=t, mo=mo, ms=ms, ao=ao, asz=asz, samples=samples, coefs=coefs, fnv=A.fnv1a(table),
                         loops=A.sample_loops(d0, t, mo, ms, len(samples))))
print('blocks', [(b['t'], b['asz'], len(b['samples'])) for b in todo])
imgs = {}
def img(b, cap):
    k = (b['ao'], cap)
    if k not in imgs:
        imgs[k] = A.cached_convert(cache, d0[b['ao']:b['ao'] + b['asz']], b['samples'], b['coefs'], cap, False, b['loops'])[0]
    return imgs[k]
opts = list(A.CAPS) + [4000, "raw"]
for lay in layouts:
    for combo in itertools.product(opts, repeat=len(todo)):
        d = bytearray(d0)
        ok = True
        for b, cap in zip(todo, combo):
            if cap == 'raw':
                continue
            im = img(b, cap)
            blob = A.HDR.pack(A.MAGIC, A.VERSION, cap, len(im), len(b['samples']), b['fnv'], b['asz'], A.slot_of(b['t']), 0,
                              *lay, *([0] * 7)) + im
            if len(blob) > b['asz']:
                ok = False; break
            d[b['ao']:b['ao'] + b['asz']] = blob + bytes(b['asz'] - len(blob))
        if not ok:
            continue
        if hashlib.sha256(d).hexdigest() == target:
            open(out, 'wb').write(d)
            print('MATCH layout', lay, 'caps', [(b['t'], c) for b, c in zip(todo, combo)])
            sys.exit(0)
print('NO MATCH'); sys.exit(1)
