"""c3r_pl11b.py TOOLS W: pl11c2.sh with the staged r117 AICA container recovered from the Codex r11f container
(ch2regen discmatch em/pl11.drs = replace_native_payload(staged, r11f arc)): staged = ref[:payload offset]."""
import sys, struct, hashlib
T, W = sys.argv[1:3]; sys.path[:0] = [T, T + '/d367']
import le_mirror as m
ref = open('/mnt/c/Game Dev/Emulators/re4-assets-private/ch2regen-20261018/discmatch/em/pl11.drs', 'rb').read()
slot = m.native_payload_slot(ref); _, n, _, off = struct.unpack_from('<4I', ref, slot)
staged = bytearray(ref[:off])
struct.pack_into('<4I', staged, slot, 0, 0, 0, m.HEADER_TABLE)   # any valid range; replace_native_payload rewrites it
staged = bytes(staged)
r11f = open(W + '/pl11-r11f/pl11.arc', 'rb').read()
print('method reproduces r11f container:', m.replace_native_payload(staged, r11f) == ref)
hot = open(W + '/pl11-hot/pl11.arc', 'rb').read()
c = m.replace_native_payload(staged, hot); open(W + '/pl11.drs', 'wb').write(c)
print('pl11-hot.drs', len(c), hashlib.sha256(c).hexdigest())
