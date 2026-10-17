import json, sys, glob
# auditchk.py <tag> rooms: every render mismatch must be an approved castle VQ key (vq16-*.txt) or a known exception.
V = '/root/probe/lanes-20261016/ch4found/tree/port/dreamcast/tools/d367/vram/'
appr = set()
for f in glob.glob(V + 'vq16-*.txt'):
    for l in open(f):
        l = l.strip()
        if l and not l.startswith('#'):
            appr.add(l.split()[0])
KNOWN = {'2fd79943-712ad365'}   # r21b: tex-t12b.pak already holds the 6,144 B VQ Codex chose (CASTLE-ROUTE step 1)
tag = sys.argv[1]
for r in sys.argv[2:]:
    a = json.load(open('/root/probe/lanes-20261016/ch4found/fixtures/%s/cx-%s-%s.pack-audit.json' % (r, r, tag)))['rooms'][r]
    bad = [t['key'] for t in a['textures'] if t.get('selected_render_match') is False]
    other = [k for k in bad if k not in appr and k not in KNOWN]
    print(r, a.get('fixture_selection'), 'mismatch', len(bad), 'unapproved', other)
