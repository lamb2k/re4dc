"""c3r_aichdr.py FILE...: print each AIC1 block header (cap, slot, layout) found in a converted bank file."""
import struct, sys
HDR = struct.Struct('<IHHIIIIII9I7I')
for f in sys.argv[1:]:
    d = open(f, 'rb').read(); i = 0; seen = set()
    while True:
        i = d.find(b'AIC1', i)
        if i < 0: break
        if i % 4 == 0 and i + HDR.size <= len(d):
            v = HDR.unpack_from(d, i)
            if v[1] == 1:
                lay = v[9:18]
                print(f.split('/')[-1], hex(i), 'cap', v[2], 'slot', v[7], 'layout', ','.join(map(str, lay)))
                seen.add(lay)
        i += 4
    print(f.split('/')[-1], 'distinct layouts', len(seen))
