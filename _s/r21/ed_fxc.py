import sys
p = sys.argv[1] + '/port/dreamcast/tools/d367/test11/t11-fix.py'
s = open(p).read()
a = "    AFTER += [('fxp26', 'pfx26')]\n"
assert s.count(a) == 1
b = a + """# fxc26 (lane cast-ps2-25 10-26, GC asset purge: the r106 census row ef2f7909): fxp26's tex.pak with the 15 frames of GC
# etc/core.das EFF #25 id 0x27 (seven-segment digits 0-9 M : . - X, 16x24) as PS2 Core.dat EFF entry 25 id 0x27 (16x32,
# same frames), PAL4 under the GC keys (tools/d367/castps2-26/fx_core_id.py = fx_ps2_pack.convert_set; fx_ps2_pack lib
# converts only core EFF #1). Needs FX_PS2_PACK=1 (cover flags). After fxp26. Store: re4-assets-private/fxc26-20261026.
FXC26D = os.environ.get('FXC26D', '/root/re4data/private/fxc26-20261026')
if os.path.isdir(FXC26D):
    DATA['fxc26'] = {'dc/tex.pak': FXC26D + '/dc/tex.pak'}
    PAK_DERIVED['fxc26'] = FXC26D + '/pak-derived.json'
    AFTER += [('fxc26', 'fxp26')]
"""
open(p, 'w').write(s.replace(a, b))
print('ok')
