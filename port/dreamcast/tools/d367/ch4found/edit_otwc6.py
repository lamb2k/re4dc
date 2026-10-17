T = '/root/probe/lanes-20261016/ch4found/tree/'
p = T + 'src/game/trans.cpp'; s = open(p).read()
old1 = """static u32* re4dc_otwc_pad;
static u32 re4dc_otwc_pad_prev, re4dc_otwc_pad_reports;"""
new1 = """static u32* re4dc_otwc_pad;
static u32 re4dc_otwc_pad_prev, re4dc_otwc_pad_reports, re4dc_otwc_pad_owner;"""
assert s.count(old1) == 1; s = s.replace(old1, new1)
old2 = """    re4dc_otwc_pad = pad;
    for (u32 i = 0; i < kOtwcPadWords; i++) pad[i] = kOtwcPadFill;"""
new2 = """    re4dc_otwc_pad = pad;
    re4dc_otwc_pad_owner = (u32) pG->prim_cnt;   // a room's new primitive buffer drops the old pad unchecked
    for (u32 i = 0; i < kOtwcPadWords; i++) pad[i] = kOtwcPadFill;"""
assert s.count(old2) == 1; s = s.replace(old2, new2)
old3 = """    u32* pad = re4dc_otwc_pad;
    if (!pad) return;"""
new3 = """    u32* pad = re4dc_otwc_pad;
    if (!pad) return;
    if ((u32) pG->prim_cnt != re4dc_otwc_pad_owner) { re4dc_otwc_pad = 0; return; }"""
assert s.count(old3) == 1; s = s.replace(old3, new3)
open(p, 'w').write(s); print('ok')
