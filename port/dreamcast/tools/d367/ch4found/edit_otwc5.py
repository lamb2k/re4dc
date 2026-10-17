T = '/root/probe/lanes-20261016/ch4found/tree/'
def sub(s, old, new):
    assert s.count(old) == 1, old[:70]
    return s.replace(old, new)
NL = chr(92) + 'n'

# OT_WALK_CHECK=2: the first 4 KB of each frame's primitive buffer is a guard pad (pattern-filled at the flip, never
# handed out); every GetPrimBuff call and every ExecOt start checks it, so a stray write into those fixed addresses
# (r229: 0x8cecbd80..0x8cecc300, the same absolute addresses with one or two buffers) is caught between two
# checkpoints, with the words written.
p = T + 'src/game/trans.cpp'; s = open(p).read()
s = sub(s, """static inline void re4dc_prim_tag(const void* a, u32 size, u32 caller)
{""", """#if RE4DC_OT_WALK_CHECK >= 2
extern "C" void re4dc_log(const char*, ...);
static u32* re4dc_otwc_pad;
static u32 re4dc_otwc_pad_prev, re4dc_otwc_pad_reports;
static const u32 kOtwcPadWords = 1024, kOtwcPadFill = 0xA5A5A5A5u;
static void re4dc_otwc_pad_fill(u32* pad)
{
    re4dc_otwc_pad = pad;
    for (u32 i = 0; i < kOtwcPadWords; i++) pad[i] = kOtwcPadFill;
}
// A checkpoint: `where` (a caller address) is the code about to run; the previous checkpoint ran before the write.
extern "C" void re4dc_otwc_pad_check(u32 where)
{
    u32* pad = re4dc_otwc_pad;
    if (!pad) return;
    u32 first = kOtwcPadWords;
    for (u32 i = 0; i < kOtwcPadWords; i++) if (pad[i] != kOtwcPadFill) { first = i; break; }
    if (first < kOtwcPadWords) {
        if (re4dc_otwc_pad_reports++ < 8) {
            u32 n = 0, last = first;
            for (u32 i = first; i < kOtwcPadWords; i++) if (pad[i] != kOtwcPadFill) { n++; last = i; }
            re4dc_log("OTWC pad write: frame %u room %03x %u words %08x..%08x between checkpoint %08x and %08x""" + NL + """",
                      (unsigned) pG->Frame_cnt, (unsigned) pG->room_id, (unsigned) n, (unsigned) (u32) (pad + first),
                      (unsigned) (u32) (pad + last), (unsigned) re4dc_otwc_pad_prev, (unsigned) where);
            for (u32 i = first & ~7u; i <= last && i < kOtwcPadWords; i += 8) {
                re4dc_log("OTWC   %08x: %08x %08x %08x %08x %08x %08x %08x %08x""" + NL + """", (unsigned) (u32) (pad + i),
                          pad[i], pad[i + 1], pad[i + 2], pad[i + 3], pad[i + 4], pad[i + 5], pad[i + 6], pad[i + 7]);
            }
        }
        for (u32 i = 0; i < kOtwcPadWords; i++) pad[i] = kOtwcPadFill;
    }
    re4dc_otwc_pad_prev = where;
}
#endif
static inline void re4dc_prim_tag(const void* a, u32 size, u32 caller)
{""")
s = sub(s, """#if defined(RE4DC_OT_WALK_CHECK) && RE4DC_OT_WALK_CHECK
    re4dc_prim_tag(gx->prim, 0, pG->nPrim | (u32) pG->vtx_buf_no << 31);
#endif""", """#if defined(RE4DC_OT_WALK_CHECK) && RE4DC_OT_WALK_CHECK
#if RE4DC_OT_WALK_CHECK >= 2
    re4dc_otwc_pad_check((u32) __builtin_return_address(0));
    re4dc_otwc_pad_fill((u32*) gx->prim);
    gx->prim += kOtwcPadWords * 4;
#endif
    re4dc_prim_tag(gx->prim, 0, pG->nPrim | (u32) pG->vtx_buf_no << 31);
#endif""")
s = sub(s, """    gx->prim = next;
#if defined(RE4DC_OT_WALK_CHECK) && RE4DC_OT_WALK_CHECK
    re4dc_prim_tag(p, (u32) size, (u32) __builtin_return_address(0));""", """    gx->prim = next;
#if defined(RE4DC_OT_WALK_CHECK) && RE4DC_OT_WALK_CHECK
#if RE4DC_OT_WALK_CHECK >= 2
    re4dc_otwc_pad_check((u32) __builtin_return_address(0));
#endif
    re4dc_prim_tag(p, (u32) size, (u32) __builtin_return_address(0));""")
open(p, 'w').write(s)

p = T + 'src/game/trans_ot.cpp'; s = open(p).read()
s = sub(s, """int ExecOt(int type)
{""", """#if defined(RE4DC_OT_WALK_CHECK) && RE4DC_OT_WALK_CHECK >= 2
extern "C" void re4dc_otwc_pad_check(u32 where);   // trans.cpp
#endif
int ExecOt(int type)
{
#if defined(RE4DC_OT_WALK_CHECK) && RE4DC_OT_WALK_CHECK >= 2
    re4dc_otwc_pad_check(0xE0000000u | (u32) type);   // checkpoint "ExecOt(type)"
#endif""")
open(p, 'w').write(s)

p = T + 'port/dreamcast/game/game30.mk'; s = open(p).read()
s = sub(s, """# walk (src/game/trans_ot.cpp); a fault names the entry being called (fault.cpp). For the r229 ExecOt fault; never in
# a release recipe.
""", """# walk (src/game/trans_ot.cpp); a fault names the entry being called (fault.cpp). =2 also keeps the first 4 KB of each
# frame's primitive buffer as a pattern-filled guard pad, checked at every GetPrimBuff call and ExecOt start ("OTWC pad
# write": the words, between which two checkpoints). For the r229 ExecOt fault; never in a release recipe.
""")
open(p, 'w').write(s)
print('ok')
