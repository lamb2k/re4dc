#!/usr/bin/env python3
"""chain.py <2|3> [--recipe recipe.conf]: the FINAL source file of every enemy archive and room registry package of Disc 2 / 3
(lane srcgeo 11-17): the content tree (D2_CASTLE_TREE / D3_ISLAND_TREE) overlaid by the recipe's D2_DATA / D3_DATA sets in order,
exactly the order t11-fix DATA / castle_fixture.py / disc3_fixture.py stage them. Prints `arch name path` and `pkg room[/partner] path`
lines for gen.sh. The srcgeo sets themselves are excluded (they are the output)."""
import importlib.util, os, re, sys
from pathlib import Path

D367 = Path(__file__).resolve().parents[1]
disc = sys.argv[1]
recipe = Path(sys.argv[sys.argv.index('--recipe') + 1]) if '--recipe' in sys.argv else D367 / 'rr/recipe.conf'
spec = importlib.util.spec_from_file_location('t11fix', D367 / 'test11/t11-fix.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
conf = recipe.read_text()
var = 'D%s_DATA' % disc
names = ''
for m in re.finditer(r'^%s="([^"]*)"' % var, conf, re.M):
    sub = re.fullmatch(r'\$\{%s/([^/}]*)/([^}]*)\}' % var, m.group(1))   # D2_DATA="${D2_DATA/pmcgca26,/pmcgca26,em14lc,}"
    if sub:
        names = names.replace(sub.group(1), sub.group(2), 1)
        continue
    names = m.group(1).replace('${%s}' % var, names).replace('$' + var, names)
    names = re.sub(r'\$\{(\w+):\+([^}]*)\}', '', names)  # default-off sets are not part of the input chain
names = [n for n in names.split(',') if n and not n.startswith('srcgeo')]
tree = re.search(r'^D%s_%s_TREE=(?:\$\{[A-Z0-9_]+:-([^}]+)\}|([^\s#]+))' % (disc, 'CASTLE' if disc == '2' else 'ISLAND'), conf, re.M)
tree = Path(tree.group(1) or tree.group(2))
final = {}
for f in sorted(tree.rglob('*')):
    if f.is_file():
        rel = f.relative_to(tree).as_posix()
        if re.fullmatch(r'em/[a-z0-9]+\.drs|dc/native/r[0-9a-f]+/(registry|partner)\.re4nmr', rel):
            final[rel] = (str(f), 'tree')
missing = []
for n in names:
    if n not in mod.DATA:
        missing.append(n)
        continue
    for k, src in mod.DATA[n].items():
        if re.fullmatch(r'em/[a-z0-9]+\.drs|dc/native/r[0-9a-f]+/(registry|partner)\.re4nmr', k):
            src = src if isinstance(src, str) else list(src)[-1]
            if os.path.isfile(src):
                final[k] = (src, n)
for k, (src, who) in sorted(final.items()):
    if k.startswith('em/'):
        print('arch', k[3:-4], src, who)
    else:
        room = k.split('/')[2]
        kind = os.path.basename(k)[:-len('.re4nmr')]
        print('pkg', room if kind == 'registry' else room + '/' + kind, src, who)
if missing:
    print('# sets without a store here:', ','.join(missing), file=sys.stderr)
