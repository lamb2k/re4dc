T = '/root/probe/lanes-20261016/ch4found/tree/'
def sub(s, old, new):
    assert s.count(old) == 1, old[:70]
    return s.replace(old, new)
p = T + 'src/game/trans_ot.cpp'; s = open(p).read()
s = sub(s, """// Runs table `type` from the farthest bucket to the nearest, calling each entry's func(data)""",
"""#if defined(RE4DC_OT_WALK_CHECK) && RE4DC_OT_WALK_CHECK
// OT_WALK_CHECK (lane ch4found16 2026-10-16, debug arm, default 0): before each entry's call, the walk checks the
// node (4-byte aligned, in main RAM) and its func (2-byte aligned, in main RAM). The first bad node is reported with
// the entry before it (whose `next` points at it: its owner's func / data / kind and the words around it) and the
// table's walk stops there instead of faulting (r229: ExecOt node 0x8ce3xxxx odd, callback 0x23708b0d).
static int re4dc_otwc_reports;
static bool re4dc_otwc_ok(const void* a, u32 align)
{
    const u32 v = (u32) a;
    return (v & (align - 1)) == 0 && v >= RE4_MEM_LO && v <= RE4_MEM_HI;
}
static void re4dc_otwc_report(int type, int count, OtWork* w, OtData* prev, OtData* p)
{
    if (re4dc_otwc_reports++ >= 6) return;
    re4dc_log("OTWC bad node: table %d entry %d frame %u room %03x node %08x list %08x..%08x max %d\n", type, count,
              (unsigned) pG->Frame_cnt, (unsigned) pG->room_id, (unsigned) (u32) p, (unsigned) (u32) w->list,
              (unsigned) (u32) (w->list + w->max), (int) w->max);
    if (re4dc_otwc_ok(p, 4)) {
        re4dc_log("OTWC   node data %08x func %08x next %08x kind %04x\n", (unsigned) (u32) p->data,
                  (unsigned) (u32) p->func, (unsigned) (u32) p->next, (unsigned) p->kind);
    }
    if (prev && re4dc_otwc_ok(prev, 4)) {
        const bool head = prev >= w->list && prev < w->list + w->max;
        re4dc_log("OTWC   prev %08x (%s %d) data %08x func %08x kind %04x\n", (unsigned) (u32) prev,
                  head ? "bucket" : "entry", head ? (int) (prev - w->list) : -1, (unsigned) (u32) prev->data,
                  (unsigned) (u32) prev->func, (unsigned) prev->kind);
        const u32* q = (const u32*) prev - 8;
        if (re4dc_otwc_ok(q, 4)) {
            for (int i = 0; i < 24; i += 8) {
                re4dc_log("OTWC   %08x: %08x %08x %08x %08x %08x %08x %08x %08x\n", (unsigned) (u32) (q + i), q[i],
                          q[i + 1], q[i + 2], q[i + 3], q[i + 4], q[i + 5], q[i + 6], q[i + 7]);
            }
        }
    }
}
#endif

// Runs table `type` from the farthest bucket to the nearest, calling each entry's func(data)""")
s = sub(s, """    p = &w->list[w->max - 1];
    w->prev_kind = 0;
    if (p) {
        for (; p; p = p->next) {
            if (p->data) {
""", """    p = &w->list[w->max - 1];
    w->prev_kind = 0;
#if defined(RE4DC_OT_WALK_CHECK) && RE4DC_OT_WALK_CHECK
    OtData* otwc_prev = 0;
#endif
    if (p) {
        for (; p; p = p->next) {
#if defined(RE4DC_OT_WALK_CHECK) && RE4DC_OT_WALK_CHECK
            if (!re4dc_otwc_ok(p, 4) || (p->data && !re4dc_otwc_ok((const void*) p->func, 2))) {
                re4dc_otwc_report(type, count, w, otwc_prev, p);
                break;
            }
            otwc_prev = p;
#endif
            if (p->data) {
""")
open(p, 'w').write(s)
p = T + 'port/dreamcast/game/game30.mk'; s = open(p).read()
s = sub(s, "GAME_OT_MASK ?= 0\n", """GAME_OT_MASK ?= 0
# OT_WALK_CHECK=1 (lane ch4found16 2026-10-16; debug arm, default 0): ExecOt checks each node and its func before the
# call, reports the first bad one with the entry that links to it ("OTWC" log lines) and stops that table's walk
# (src/game/trans_ot.cpp). For the r229 ExecOt fault; never in a release recipe.
OT_WALK_CHECK ?= 0
ifneq ($(OT_WALK_CHECK),0)
$(OBJDIR)/src/game/trans_ot.o: GAME_CPPFLAGS += -DRE4DC_OT_WALK_CHECK=$(OT_WALK_CHECK)
endif
""")
open(p, 'w').write(s)
print('ok')
