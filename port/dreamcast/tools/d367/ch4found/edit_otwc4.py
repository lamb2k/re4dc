T = '/root/probe/lanes-20261016/ch4found/tree/'
def sub(s, old, new):
    assert s.count(old) == 1, old[:70]
    return s.replace(old, new)
NL = chr(92) + 'n'

# trans_ot.cpp: data is opaque (Filter00 passes 0xCDCDCDCD), so only node + func are checked; the entry being called
# is kept in globals so a fault inside the call can name it (re4dc_otwc_fault, called by fault.cpp).
p = T + 'src/game/trans_ot.cpp'; s = open(p).read()
s = sub(s, """            if (!re4dc_otwc_ok(p, 4) ||
                (p->data && (!re4dc_otwc_ok((const void*) p->func, 2) || !re4dc_otwc_ok(p->data, 2)))) {""",
"""            if (!re4dc_otwc_ok(p, 4) || (p->data && !re4dc_otwc_ok((const void*) p->func, 2))) {""")
s = sub(s, """            otwc_prev = p;
#endif""", """            otwc_prev = p;
            re4dc_otwc_cur = p; re4dc_otwc_cur_type = type; re4dc_otwc_cur_n = count;
#endif""")
s = sub(s, """static void re4dc_otwc_report(int type, int count, OtWork* w, OtData* prev, OtData* p)
{""", """static OtData* re4dc_otwc_cur;
static int re4dc_otwc_cur_type = -1, re4dc_otwc_cur_n;
static void re4dc_otwc_report(int type, int count, OtWork* w, OtData* prev, OtData* p);
// fault.cpp (OT_WALK_CHECK): a fault names the ExecOt entry being called, if any, and the slots that cover it.
extern "C" void re4dc_otwc_fault()
{
    if (g_NowExecOtType == OT_MAX || re4dc_otwc_cur_type < 0) {
        re4dc_log("OTWC fault: outside ExecOt (last table %d)""" + NL + """", re4dc_otwc_cur_type);
        return;
    }
    OtData* p = re4dc_otwc_cur;
    re4dc_log("OTWC fault in ExecOt: table %d entry %d node %08x""" + NL + """", re4dc_otwc_cur_type, re4dc_otwc_cur_n,
              (unsigned) (u32) p);
    if (re4dc_otwc_ok(p, 4)) {
        re4dc_log("OTWC   node data %08x func %08x next %08x kind %04x""" + NL + """", (unsigned) (u32) p->data,
                  (unsigned) (u32) p->func, (unsigned) (u32) p->next, (unsigned) p->kind);
        const u32* q = (const u32*) p - 8;
        for (int i = 0; i < 24; i += 8) {
            re4dc_log("OTWC   %08x: %08x %08x %08x %08x %08x %08x %08x %08x""" + NL + """", (unsigned) (u32) (q + i), q[i],
                      q[i + 1], q[i + 2], q[i + 3], q[i + 4], q[i + 5], q[i + 6], q[i + 7]);
        }
        re4dc_otwc_tags("node", (u32) p);
        if (re4dc_otwc_ok((const void*) p->func, 4)) re4dc_otwc_tags("func", (u32) p->func);
    }
}
static void re4dc_otwc_report(int type, int count, OtWork* w, OtData* prev, OtData* p)
{""")
open(p, 'w').write(s)

# fault.cpp: call the hook after the register dump (only in an OT_WALK_CHECK build)
p = T + 'port/dreamcast/game/platform/fault.cpp'; s = open(p).read()
s = sub(s, """    re4dc_set_stage(0xDEAD0000ul | (unsigned long) code);
#if RE4DC_VMU_DEBUG_SLOT""", """#if defined(RE4DC_OT_WALK_CHECK) && RE4DC_OT_WALK_CHECK
    re4dc_otwc_fault();  // trans_ot.cpp: the ExecOt entry being called, if any
#endif
    re4dc_set_stage(0xDEAD0000ul | (unsigned long) code);
#if RE4DC_VMU_DEBUG_SLOT""")
s = sub(s, """static void onFault(irq_t code, irq_context_t* ctx, void* data)
{""", """#if defined(RE4DC_OT_WALK_CHECK) && RE4DC_OT_WALK_CHECK
extern "C" void re4dc_otwc_fault();
#endif
static void onFault(irq_t code, irq_context_t* ctx, void* data)
{""")
open(p, 'w').write(s)

p = T + 'port/dreamcast/game/game30.mk'; s = open(p).read()
s = sub(s, """# call (node, func and data pointers), reports the first bad one with the entry that links to it ("OTWC" log lines)
# and the GetPrimBuff slots that cover them (trans.cpp tags each slot: frame, caller) and stops that table's walk
# (src/game/trans_ot.cpp). For the r229 ExecOt fault; never in a release recipe.
OT_WALK_CHECK ?= 0
ifneq ($(OT_WALK_CHECK),0)
$(OBJDIR)/src/game/trans_ot.o $(OBJDIR)/src/game/trans.o: GAME_CPPFLAGS += -DRE4DC_OT_WALK_CHECK=$(OT_WALK_CHECK)
endif
""", """# call (node and func pointers; data is opaque), reports the first bad one with the entry that links to it ("OTWC" log
# lines) and the GetPrimBuff slots that cover them (trans.cpp tags each slot: frame, caller) and stops that table's
# walk (src/game/trans_ot.cpp); a fault names the entry being called (fault.cpp). For the r229 ExecOt fault; never in
# a release recipe.
OT_WALK_CHECK ?= 0
ifneq ($(OT_WALK_CHECK),0)
$(OBJDIR)/src/game/trans_ot.o $(OBJDIR)/src/game/trans.o: GAME_CPPFLAGS += -DRE4DC_OT_WALK_CHECK=$(OT_WALK_CHECK)
$(OBJDIR)/platform/fault.o: PLATFORM_CPPFLAGS += -DRE4DC_OT_WALK_CHECK=$(OT_WALK_CHECK)
endif
# OT_PRIM_BUFFERS=2 (lane ch4found16 2026-10-16; experiment, default 1 = image unchanged): the GameCube's two primitive
# buffers (one per frame, flipped by SetPrimBuffPtr) instead of the port's one (native_primitive.h). Twice the room's
# primitive buffer in heap 4. A discriminator for the r229 OT corruption: a writer through a previous frame's
# primitive pointer hits this frame's OT nodes with one buffer, the idle half with two.
OT_PRIM_BUFFERS ?= 1
ifneq ($(OT_PRIM_BUFFERS),1)
$(OBJDIR)/src/game/game.o $(OBJDIR)/src/game/trans.o: GAME_CPPFLAGS += -DRE4DC_PRIMITIVE_BUFFERS=$(OT_PRIM_BUFFERS)
endif
""")
open(p, 'w').write(s)
print('ok')
