#!/usr/bin/env python3
# In Git from test 17 (lane pak17, 10-16; was /root/probe/lanes-20261011/test8/t8-pkgtree.py, outside Git, which the
# older package scripts still call): test16/t16-package.sh uses this copy. Same behaviour for every older fixture; a
# fixture that removes disc files (data set pak17) gets them unlinked from the hard-link package tree.
"""t8-pkgtree.py <play-label> [fixture]: build test8/pkgtree (the GDEMU disc's data tree) from the test 6 combo pkgtree
(hard links) with the test 8 changes: this arm's overlays, then every file of the play fixture (pkg-<label>.json)
that differs from the tree. Then verify: every fixture replace entry is byte-identical in the tree, no fixture remove
entry and no warp / padscript file is present. Prints the changed paths."""
import filecmp, json, os, shutil, sys
from pathlib import Path
import os as _os
K = Path(_os.environ.get('PKG_K', '/root/probe/lanes-20261011/test8'))
SRC = Path(_os.environ.get('PKG_SRC', '/root/probe/lanes-20261010/combo/pkgtree'))
lab = sys.argv[1]
fix = json.load(open(sys.argv[2] if len(sys.argv) > 2 else Path('/root/probe/lanes-20261011/test8/fix') / ('pkg-%s.json' % lab)))
out = K / 'pkgtree'
if out.exists():
    shutil.rmtree(out)
os.system('cp -al "%s" "%s"' % (SRC, out))
O = Path('/root/probe/lanes/route/out-' + lab)
changed = []
def put(rel, src):
    dst = out / rel
    if dst.exists() and filecmp.cmp(dst, src, shallow=False):
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        dst.unlink()  # break the hard link
    shutil.copyfile(src, dst)
    changed.append(rel)
for m in ('pl0f', 'em2f', 'em22', 'em2b', 'pl11', 'sscrn'):
    put('dc/%s.ovl' % m, O / ('%s.ovl' % m))
for rel, src in fix['replace'].items():
    put(rel, src)
# honour the fixture removals (lane pak17, 10-16: data set pak17 drops the base tree's loose dc/tex files; until then
# every removal was absent from the base, so this deletes nothing for older fixtures). The out tree is a hard-link copy:
# unlinking leaves the base tree intact.
removed = []
for rel in fix['remove']:
    if (out / rel).is_file():
        (out / rel).unlink(); removed.append(rel)
print('removed %d' % len(removed))
bad = []
for rel, src in fix['replace'].items():
    if not filecmp.cmp(out / rel, src, shallow=False):
        bad.append('differs ' + rel)
for rel in fix['remove']:
    if (out / rel).exists():
        bad.append('present (removed in fixture) ' + rel)
for rel in ('dc/warp.txt', 'dc/padscript.txt', 'dc/crashtest.txt'):
    if (out / rel).exists():
        bad.append('present ' + rel)
print('changed %d:' % len(changed))
for c in changed:
    print('  ' + c)
print('PKGTREE_OK' if not bad else 'PKGTREE_BAD\n' + '\n'.join(bad))
