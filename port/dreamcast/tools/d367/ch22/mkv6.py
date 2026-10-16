import json
L = '/root/probe/lanes-20261014/ch22/fix/'
d = json.load(open(L + 'route-v5.json'))
d['replace']['em/pl11.drs'] = '/root/probe/codex-em35-cap128-20261013/motion-assets/em/pl11.drs'
d['provenance'] = dict(d['provenance']) if isinstance(d['provenance'], dict) else {'v5': d['provenance']}
d['provenance']['route-v6'] = ('route-v5 + em/pl11.drs = Codex bounded pl11 (motion-assets, version-3 MTC, MRAM 384064 instead of '
    '1069792; first 1385728 bytes equal the r117 AICA pl11 except 5 header bytes, so the audio is the same). Needs MOTION_BOUNDED_R11F=1: '
    'r11f em35 bind needs ~123 KB heap 4 and the old pl11 left 114 KB.')
json.dump(d, open(L + 'route-v6.json', 'w'), indent=1)
print(len(d['replace']), 'replace', len(d.get('remove', [])), 'remove')
