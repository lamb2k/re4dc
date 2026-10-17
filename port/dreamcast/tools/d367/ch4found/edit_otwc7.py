T = '/root/probe/lanes-20261016/ch4found/tree/'
def sub(s, old, new):
    assert s.count(old) == 1, old[:70]
    return s.replace(old, new)
NL = chr(92) + 'n'

# OT_WALK_CHECK=2: CalculateShape_new reports a delta whose vertex lies outside dst's nVtx vertices (r229 OT corruption:
# s16 xyz read-modify-write at an 8-byte vertex stride, 0x248..0x1220 bytes into the frame's primitive buffer start).
p = T + 'src/game/shape.cpp'; s = open(p).read()
s = sub(s, """                    for (n = 0; n < num; n++) {
                        s16* vtx = (s16*) (dst + *src++ * 8);""", """#if defined(RE4DC_OT_WALK_CHECK) && RE4DC_OT_WALK_CHECK >= 2
                    {
                        static u32 reports;
                        s32 lo = 0x7fffffff, hi = -0x7fffffff - 1;
                        const s16* q = src;
                        for (n = 0; n < num; n++, q += 4) { if (*q < lo) lo = *q; if (*q > hi) hi = *q; }
                        if (num > 0 && (lo < 0 || hi >= (s32) info->pData->nVtx) && reports++ < 8) {
                            re4dc_log("OTWC shape out of range: info %08x data %08x channel %u entries %d index %d..%d nVtx %u "
                                      "dst %08x pPosBuf %08x/%08x caller %08x""" + NL + """", (unsigned) (u32) info, (unsigned) (u32) data,
                                      (unsigned) i, (int) num, (int) lo, (int) hi, (unsigned) info->pData->nVtx,
                                      (unsigned) (u32) dst, (unsigned) (u32) info->pPosBuf[0], (unsigned) (u32) info->pPosBuf[1],
                                      (unsigned) (u32) __builtin_return_address(0));
                        }
                    }
#endif
                    for (n = 0; n < num; n++) {
                        s16* vtx = (s16*) (dst + *src++ * 8);""")
s = sub(s, """// Restore the original vertex positions.
void ResetShape(cModelInfo* info, void* dst)""", """#if defined(RE4DC_OT_WALK_CHECK) && RE4DC_OT_WALK_CHECK >= 2
extern "C" void re4dc_log(const char*, ...);
#endif
// Restore the original vertex positions.
void ResetShape(cModelInfo* info, void* dst)""")
open(p, 'w').write(s)

p = T + 'port/dreamcast/game/game30.mk'; s = open(p).read()
s = sub(s, "$(OBJDIR)/src/game/trans_ot.o $(OBJDIR)/src/game/trans.o: GAME_CPPFLAGS += -DRE4DC_OT_WALK_CHECK=$(OT_WALK_CHECK)\n",
        "$(OBJDIR)/src/game/trans_ot.o $(OBJDIR)/src/game/trans.o $(OBJDIR)/src/game/shape.o: GAME_CPPFLAGS += -DRE4DC_OT_WALK_CHECK=$(OT_WALK_CHECK)\n")
open(p, 'w').write(s)
print('ok')
