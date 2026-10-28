import re, sys
R = sys.argv[1] + '/port/dreamcast/tools/d367/'
p = R + 'test11/t11-fix.py'
s = open(p).read()
a = "    AFTER += [('fxc26', 'fxp26')]\n"
assert s.count(a) == 1
s = s.replace(a, a + """# fxc26b (lane cast-ps2-25 10-26): fxc26's tex.pak with the last three GC etc/core.das EFF #25 ids route rooms load (0x0e
# strip, 0x31 bulb, 0x61 panel) as PS2 Core.dat EFF entry 25 pictures under the GC keys (castps2-26/fx_core_id.py). Every
# other EFF #25 id is already PS2 or loaded by no route room; EFF #16 is empty. After fxc26. Store: re4-assets-private/fxc26b-20261026.
FXC26BD = os.environ.get('FXC26BD', '/root/re4data/private/fxc26b-20261026')
if os.path.isdir(FXC26BD):
    DATA['fxc26b'] = {'dc/tex.pak': FXC26BD + '/dc/tex.pak'}
    PAK_DERIVED['fxc26b'] = FXC26BD + '/pak-derived.json'
    AFTER += [('fxc26b', 'fxc26')]
""")
open(p, 'w').write(s)
p = R + 'rr/recipe.conf'
s = open(p).read()
assert s.count(',fxc26"') == 1
open(p, 'w').write(s.replace(',fxc26"', ',fxc26,fxc26b"'))
p = R + 'rr/member-claims.tsv'
s = open(p).read()
assert s.count(',fxc26\t') == 1
open(p, 'w').write(s.replace(',fxc26\t', ',fxc26,fxc26b\t'))
print('ok')
