import sys, struct, hashlib
T, W = sys.argv[1:3]; sys.path[:0] = [T, T + '/d367']
import le_mirror as m
ref = open('/mnt/c/Game Dev/Emulators/re4-assets-private/ch2regen-20261018/discmatch/em/pl11.drs', 'rb').read()
st = open('/mnt/c/Game Dev/Emulators/re4-assets-private/p2d3-ch22-20261012/aica/em/pl11.drs', 'rb').read()
r11f = open(W + '/pl11-r11f/pl11.arc', 'rb').read()
slot = m.native_payload_slot(ref)
_, n, _, off = struct.unpack_from('<4I', ref, slot)
pay = ref[off:off + n]
print('ref payload', n, 'mine r11f', len(r11f), 'equal', pay == r11f)
if pay != r11f:
    d = next(i for i in range(min(n, len(r11f))) if pay[i] != r11f[i]); print('first diff', hex(d))
c = m.replace_native_payload(st, pay)
print('staged+refpayload == ref', c == ref, len(c), len(ref))
if c != ref:
    d = next(i for i in range(min(len(c), len(ref))) if c[i] != ref[i]); print('container first diff', hex(d), 'slot', hex(slot), 'off', hex(off))
