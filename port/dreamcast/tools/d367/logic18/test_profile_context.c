/* Synthetic control-flow tests. These check attribution, never model timings. */
#include <assert.h>
#include "profile_context.h"

static void setup(void) {
    static L18Symbol symbols[5] = {
        {0}, {0x100,0x180,1,0,"player"}, {0x200,0x280,0,0,"child"},
        {0x300,0x380,0,0,"tail"}, {0x400,0x480,0,1,"thread_barrier"}
    };
    l18_symbols=symbols; l18_nsymbols=5;
    if(!l18_flat) l18_flat=calloc(5,sizeof(*l18_flat));
    l18_enabled=1; l18_vbr=0x1000;
    l18_begin("synthetic");
}
static unsigned execute(uint32_t pc,uint16_t op) {
    l18_before(pc,op); l18_charge(l18_current,pc,16); return l18_current;
}
static unsigned call(uint32_t pc,uint32_t target) {
    execute(pc,0x400b); execute(pc+2,0x0009); return execute(target,0x0009);
}
static void ret(uint32_t pc,uint32_t target) {
    execute(pc,0x000b); execute(pc+2,0x0009); execute(target,0x0009);
}
static void nested_and_delayed(void) {
    setup(); unsigned outer=call(0x80,0x100);
    assert(l18_nodes[outer].owner==1);
    execute(0x102,0x400b);
    unsigned delay=execute(0x104,0x0009);
    assert(delay==outer); /* Call's delay instruction stays with caller. */
    unsigned inner=execute(0x200,0x0009);
    assert(inner!=outer && l18_nodes[inner].parent==outer);
    ret(0x210,0x106); assert(l18_nodes[inner].complete);
    uint64_t before=l18_nodes[inner].self;
    l18_charge(inner,0x210,7); /* Deferred return redirect retains immutable invocation. */
    assert(l18_nodes[inner].self==before+7 && l18_current==outer);
    ret(0x110,0x84); assert(l18_nodes[outer].complete);
    uint64_t sum=0,flat=0;
    for(unsigned i=0;i<l18_count;i++) sum+=l18_nodes[i].self;
    for(unsigned i=0;i<l18_nsymbols;i++) flat+=l18_flat[i];
    assert(sum==flat && sum==l18_charged);
}
static void recursive(void) {
    setup(); unsigned a=call(0x80,0x100), b=call(0x102,0x100);
    assert(a!=b && l18_nodes[b].parent==a && l18_nodes[a].symbol==l18_nodes[b].symbol);
    ret(0x110,0x106); assert(l18_nodes[b].complete && l18_current==a);
    ret(0x114,0x84); assert(l18_nodes[a].complete);
}
static void tail_and_sparse_cut(void) {
    setup(); unsigned a=call(0x80,0x100);
    execute(0x102,0xa000); execute(0x104,0x0009); execute(0x300,0x0009);
    assert(l18_nodes[a].invalid && !l18_nodes[a].complete);
    assert(l18_nodes[l18_current].kind==L18_TAIL && l18_nodes[l18_current].owner==0);
    setup(); execute(0x210,0x000b); execute(0x212,0x0009); execute(0x106,0x0009);
    assert(l18_nodes[l18_current].kind==L18_THREAD); /* No stack guessed at sparse cut. */
}
static void interrupt_and_thread(void) {
    setup(); unsigned a=call(0x80,0x100); execute(0x102,0x0009);
    unsigned irq=execute(0x1600,0x0009); assert(l18_nodes[irq].owner==5);
    unsigned handler=call(0x1602,0x200); assert(l18_nodes[handler].owner==5);
    ret(0x210,0x1606); assert(l18_nodes[handler].complete);
    execute(0x1608,0x002b); execute(0x160a,0x0009); execute(0x104,0x0009);
    assert(l18_current==a && !l18_nodes[a].invalid);
    execute(0x106,0x0009); execute(0x1600,0x0009);
    execute(0x1602,0x002b); execute(0x1604,0x0009); execute(0x234,0x0009);
    assert(l18_nodes[a].invalid && l18_nodes[l18_current].kind==L18_THREAD);
    setup(); a=call(0x80,0x100); call(0x102,0x400);
    assert(l18_nodes[a].invalid && l18_nodes[l18_current].owner==0);
}
static void no_nearest_symbol_guess(void) {
    setup(); assert(l18_function(0x180)==0 && l18_function(0x1ff)==0);
    uint32_t saved=l18_symbols[2].end; l18_symbols[2].end=0x200;
    assert(l18_entry(0x200)==2 && l18_function(0x200)==0);
    l18_symbols[2].end=saved;
}
static void conservative_jumps(void) {
    uint32_t targets[]={0x234,0x500,0x100};
    for(unsigned i=0;i<3;i++) {
        setup(); unsigned a=call(0x80,0x100);
        execute(0x102,0x402b); execute(0x104,0x0009); execute(targets[i],0x0009);
        assert(l18_nodes[a].invalid && !l18_nodes[a].complete);
        assert(l18_nodes[l18_current].kind==L18_TAIL && !l18_nodes[l18_current].owner);
    }
    setup(); unsigned a=call(0x80,0x100);
    execute(0x102,0xa000); execute(0x104,0x0009); execute(0x120,0x0009);
    assert(l18_current==a && !l18_nodes[a].invalid);
    execute(0x122,0x8900); execute(0x124,0x0009); /* not taken */
    assert(l18_current==a && !l18_nodes[a].invalid);
    execute(0x126,0x8b00); execute(0x234,0x0009);
    assert(l18_nodes[a].invalid && !l18_nodes[l18_current].owner);
    setup(); a=call(0x80,0x100);
    execute(0x102,0x8d00); assert(execute(0x104,0x0009)==a);
    execute(0x500,0x0009); assert(l18_nodes[a].invalid);
}
int main(void) {
    nested_and_delayed(); conservative_jumps(); recursive(); tail_and_sparse_cut(); interrupt_and_thread(); no_nearest_symbol_guess();
    puts("PASS nested recursive tail delay-slot deferred-charge IRQ context-switch sparse-cut exact-range conservation");
    return 0;
}
