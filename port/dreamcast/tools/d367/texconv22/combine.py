#!/usr/bin/env python3
"""texconv22: add-on manifest + combined pack (1760 pack + exact-base repeat members)."""
import collections, hashlib, json, struct, sys, zlib
from pathlib import Path
T = '/root/work/lanes/texconv22/tree/port/dreamcast/tools'
sys.path[:0] = [T + '/d367', T, T + '/d367/vram']
import texpack
from vq_pak import read_pak
H = lambda b: hashlib.sha256(b).hexdigest()
D = Path(sys.argv[1]); BASE = Path('/root/re4data/private/texture-append1760-20261022-v1-native-c/tex.pak')
base = BASE.read_bytes(); assert H(base) == '1838d97ae07637fa47beed574033e2d4f79595f86fb024ace6e6e7cc752f6477'
pk = read_pak(base); n0 = len(pk)
rep = json.load(open(D / 'repeat/repeat6.json'))
add = json.load(open('/root/re4data/private/texture-rect21-final142-additions-packet-20261022-v2/ADDITIONS142.json'))['selected']
pol = {x['original_key']: x for x in json.load(open('/root/re4data/private/texture-rect21-next142-alpha-20261022-v1/policy-classification.json'))['checks']}
route = json.load(open('/root/work/lanes/texconv22/s/route.json'))['rooms']

# 1) the 23 held keys as they sit in the 1760 pack
held = [k for k, c in pol.items() if not c['qualified']]
assert len(held) == 23
by_orig = {x['original_key']: x for x in add}
man = []
for ok in held:
    a = by_orig[ok]; k = tuple(int(x, 16) for x in a['scoped_key'].split('-')); blob = pk[k]
    in_pack_ok = H(blob) == a['sha256'] and struct.unpack_from('<I', blob, 36)[0] == zlib.crc32(blob[48:]) & 0xffffffff
    r = next((r for r in rep if r['original_key'] == ok), None)
    drift = a['semantic_source'] == 'repeat16'
    if drift:
        dec, why = 'convert-shipped-material-exact', 'exact-base repeat (Codex repeat16), class restored = shipped R4TC; in 1760 pack'
        cls = 'class-drift' + ('+missing-profile' if any(x['shipped_class'] is None for x in pol[ok]['refs']) else '')
    elif r and r['decision'] == 'convert-exact-base-repeat':
        dec, why, cls = 'convert-exact-base (replaces compact)', 'compact base changed pixels; new exact-base repeat chain in add-on', 'missing-profile'
    else:
        dec, why, cls = 'approx-keep-compact (look check)', r['reason'] if r else '', 'missing-profile'
    man.append(dict(original_key=ok, pack_key_1760=a['scoped_key'], class_=cls, decision=dec, why=why,
                    levels=(r['mip_levels'] if r and 'mip_levels' in r and dec.startswith('convert-exact-base') else a['mip_levels']),
                    addon_key=(r['scoped_key'] if r and dec.startswith('convert-exact-base') else None), in_1760_pack_sha_and_strict_crc=in_pack_ok))

# 2) add the new members, keep every 1760 member exact
new = {}
for r in rep:
    if r['decision'] != 'convert-exact-base-repeat': continue
    b = (D / 'repeat/textures' / (r['scoped_key'] + '.re4tex')).read_bytes(); assert H(b) == r['sha256']
    k = tuple(int(x, 16) for x in r['scoped_key'].split('-')); assert k not in pk; new[k] = b
allp = dict(pk); allp.update(new)
out, _ = texpack.build(allp); texpack.verify(out)
chk = read_pak(out); assert len(chk) == n0 + len(new) and all(chk[k] == v for k, v in allp.items())
(D / 'tex.pak').write_bytes(out)

# 3) per route room change if the world binds the add-on keys instead of the compact keys
rooms = collections.defaultdict(lambda: dict(keys=0, vram_req_delta=0, package_bytes_delta=0))
for r in rep:
    if r['decision'] != 'convert-exact-base-repeat': continue
    a = by_orig[r['original_key']]
    for room in sorted({x['room'] for x in pol[r['original_key']]['refs']}):
        e = rooms[room]; e['keys'] += 1
        e['vram_req_delta'] += r['repeat_request_rounded'] - r['compact_request_rounded']
        e['package_bytes_delta'] += r['package_bytes'] - a['package_bytes']
table = {room: rooms.get(room, dict(keys=0, vram_req_delta=0, package_bytes_delta=0)) for room in list(route) + ['r200']}
inc = ''.join('{0x%sU,0x%sU,%dU,%dU,{%dU,%dU,%dU,%dU,%dU,%dU,0x%08xU},%.9ff,%.9ff},\n' % (
    r['scoped_key'][:8], r['scoped_key'][9:], r['logical'][0], r['logical'][1], r['descriptor']['width'], r['descriptor']['height'],
    r['descriptor']['format'], r['descriptor']['flags'], r['descriptor']['payload'], r['descriptor']['bytes'], r['descriptor']['checksum'],
    r['uv_scale'][0], r['uv_scale'][1]) for r in rep if r['decision'] == 'convert-exact-base-repeat')
(D / 'addon_scoped_representations.inc').write_text('// texconv22 add-on: exact-base repeat replacements for 6 compact keys (private proposal)\n' + inc)
res = dict(base_pack=str(BASE), base_pack_sha256=H(base), base_members=n0, combined_pack=str(D / 'tex.pak'), combined_sha256=H(out),
           combined_bytes=len(out), base_bytes=len(base), members=len(chk), added_members=len(new), held23=man,
           pal622=json.load(open(D / 'pal622.json'))['summary'] if (D / 'pal622.json').exists() else None,
           per_route_room=table)
(D / 'addon-manifest.json').write_text(json.dumps(res, indent=1) + '\n')
print(json.dumps({k: v for k, v in res.items() if k not in ('held23', 'per_route_room')}, indent=1))
for m in man: print(m['original_key'], m['class_'], '|', m['decision'], m['levels'], m['in_1760_pack_sha_and_strict_crc'])
for room, e in table.items():
    if e['keys']: print(room, e)
