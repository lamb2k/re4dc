T = '/root/probe/lanes-20261016/ch4found/tree/'
def sub(s, old, new):
    assert s.count(old) == 1, old[:70]
    return s.replace(old, new)

# trans.cpp: tag every GetPrimBuff slot (address, size, frame, caller) in a ring, and the buffer flips
p = T + 'src/game/trans.cpp'; s = open(p).read()
s = sub(s, """// Allocates `size` bytes (32-byte aligned) from this frame's primitive buffer; 0 when exhausted.
void* GetPrimBuff(int size)
{""", """#if defined(RE4DC_OT_WALK_CHECK) && RE4DC_OT_WALK_CHECK
// OT_WALK_CHECK (lane ch4found16, debug arm): every GetPrimBuff slot is tagged (address, size, frame, caller) in a
// 2048-entry ring, and every buffer flip (SetPrimBuffPtr) too (size 0, caller = the new start), so the ExecOt check
// can name the allocations that cover a bad node (trans_ot.cpp re4dc_otwc_report).
struct Re4dcPrimTag { u32 addr, size, frame, caller; };
extern "C" { Re4dcPrimTag re4dc_prim_tags[2048]; u32 re4dc_prim_tag_n; }
static inline void re4dc_prim_tag(const void* a, u32 size, u32 caller)
{
    Re4dcPrimTag& t = re4dc_prim_tags[re4dc_prim_tag_n++ & 2047];
    t.addr = (u32) a; t.size = size; t.frame = pG->Frame_cnt; t.caller = caller;
}
#endif
// Allocates `size` bytes (32-byte aligned) from this frame's primitive buffer; 0 when exhausted.
void* GetPrimBuff(int size)
{""")
s = sub(s, """    gx->prim = next;
    return p;
}""", """    gx->prim = next;
#if defined(RE4DC_OT_WALK_CHECK) && RE4DC_OT_WALK_CHECK
    re4dc_prim_tag(p, (u32) size, (u32) __builtin_return_address(0));
#endif
    return p;
}""")
s = sub(s, """    gx->prim = (u8*) pG->prim_cnt + pG->nPrim * pG->vtx_buf_no;
#if RE4DC_PRIM_WATER
    primw_start = gx->prim;
#endif
}""", """    gx->prim = (u8*) pG->prim_cnt + pG->nPrim * pG->vtx_buf_no;
#if RE4DC_PRIM_WATER
    primw_start = gx->prim;
#endif
#if defined(RE4DC_OT_WALK_CHECK) && RE4DC_OT_WALK_CHECK
    re4dc_prim_tag(gx->prim, 0, pG->nPrim | (u32) pG->vtx_buf_no << 31);
#endif
}""")
open(p, 'w').write(s)

# trans_ot.cpp: data pointer checked too; the report lists the tags covering the bad node's and its owner's slots
p = T + 'src/game/trans_ot.cpp'; s = open(p).read()
s = sub(s, """static void re4dc_otwc_report(int type, int count, OtWork* w, OtData* prev, OtData* p)
{
    if (re4dc_otwc_reports++ >= 6) return;""", """struct Re4dcPrimTag { u32 addr, size, frame, caller; };
extern "C" { extern Re4dcPrimTag re4dc_prim_tags[2048]; extern u32 re4dc_prim_tag_n; }
// The newest tags (up to 6) whose slot covers `a`, newest first, and the newest buffer flip before each.
static void re4dc_otwc_tags(const char* what, u32 a)
{
    int shown = 0;
    const u32 n = re4dc_prim_tag_n;
    for (u32 k = 0; k < 2048 && k < n && shown < 6; k++) {
        const Re4dcPrimTag& t = re4dc_prim_tags[(n - 1 - k) & 2047];
        if (t.size && a >= t.addr && a < t.addr + t.size) {
            re4dc_log("OTWC   %s %08x in slot %08x+%u frame %u caller %08x (tag -%u)\\n", what, (unsigned) a,
                      (unsigned) t.addr, (unsigned) t.size, (unsigned) t.frame, (unsigned) t.caller, (unsigned) k);
            ++shown;
        }
    }
    for (u32 k = 0; k < 2048 && k < n; k++) {
        const Re4dcPrimTag& t = re4dc_prim_tags[(n - 1 - k) & 2047];
        if (!t.size) {
            re4dc_log("OTWC   last flip: start %08x frame %u nPrim %u buf %u (tag -%u), now frame %u\\n", (unsigned) t.addr,
                      (unsigned) t.frame, (unsigned) (t.caller & 0x7FFFFFFF), (unsigned) (t.caller >> 31), (unsigned) k,
                      (unsigned) pG->Frame_cnt);
            break;
        }
    }
    if (!shown) re4dc_log("OTWC   %s %08x: no GetPrimBuff slot in the last 2048 tags\\n", what, (unsigned) a);
}
static void re4dc_otwc_report(int type, int count, OtWork* w, OtData* prev, OtData* p)
{
    if (re4dc_otwc_reports++ >= 6) return;""")
s = sub(s, """        const u32* q = (const u32*) prev - 8;""", """        re4dc_otwc_tags("prev", (u32) prev);
        const u32* q = (const u32*) prev - 8;""")
s = sub(s, """    if (re4dc_otwc_ok(p, 4)) {
        re4dc_log("OTWC   node data""", """    if (re4dc_otwc_ok(p, 4)) {
        re4dc_otwc_tags("node", (u32) p);
        re4dc_log("OTWC   node data""")
s = sub(s, """            if (!re4dc_otwc_ok(p, 4) || (p->data && !re4dc_otwc_ok((const void*) p->func, 2))) {""",
"""            if (!re4dc_otwc_ok(p, 4) ||
                (p->data && (!re4dc_otwc_ok((const void*) p->func, 2) || !re4dc_otwc_ok(p->data, 2)))) {""")
open(p, 'w').write(s)

p = T + 'port/dreamcast/game/game30.mk'; s = open(p).read()
s = sub(s, "$(OBJDIR)/src/game/trans_ot.o: GAME_CPPFLAGS += -DRE4DC_OT_WALK_CHECK=$(OT_WALK_CHECK)\n",
"$(OBJDIR)/src/game/trans_ot.o $(OBJDIR)/src/game/trans.o: GAME_CPPFLAGS += -DRE4DC_OT_WALK_CHECK=$(OT_WALK_CHECK)\n")
s = sub(s, "# call, reports the first bad one with the entry that links to it (\"OTWC\" log lines) and stops that table's walk\n",
"# call (node, func and data pointers), reports the first bad one with the entry that links to it (\"OTWC\" log lines)\n# and the GetPrimBuff slots that cover them (trans.cpp tags each slot: frame, caller) and stops that table's walk\n")
open(p, 'w').write(s)
print('ok')
