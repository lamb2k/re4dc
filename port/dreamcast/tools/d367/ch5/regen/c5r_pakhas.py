import json, struct, sys
fx = json.load(open(sys.argv[1]))
p = fx['replace'].get('dc/tex.pak'); print('tex.pak', p)
d = open(p, 'rb').read(); n, io = struct.unpack_from('<II', d, 12)
ks = {'%08x-%08x' % struct.unpack_from('<II', d, io + 16 * i) for i in range(n)}
for k in sys.argv[2:]:
    print(k, k in ks, 'loose' if any(k in x for x in fx['replace']) else '')
