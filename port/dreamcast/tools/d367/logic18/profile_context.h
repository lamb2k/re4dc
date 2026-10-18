/* Host-only execution-context accounting. No instruction timing decisions.
 * A node is an observed invocation, not a guessed nearest-symbol owner.
 * Unknown returns, tail transfers, thread changes and sparse cuts fail closed.
 * All charges use immutable invocation IDs captured at instruction execution.
 */
#ifndef LOGIC18_PROFILE_CONTEXT_H
#define LOGIC18_PROFILE_CONTEXT_H
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum { L18_UNKNOWN, L18_CALL, L18_IRQ, L18_TAIL, L18_THREAD, L18_CUT };
enum { L18_NONE, L18_DO_CALL, L18_DO_RETURN, L18_DO_JUMP, L18_DO_COND, L18_DO_RTE };
typedef struct { uint32_t start, end; int owner, barrier; char name[512]; } L18Symbol;
typedef struct {
    unsigned parent, symbol, kind, owner, complete, invalid;
    uint32_t ret;
    uint64_t self, inclusive;
} L18Node;
typedef struct { int action, slots; uint32_t ret, branch; } L18Pending;
typedef struct {
    unsigned stack[256], depth; L18Pending pending; uint32_t resume;
} L18Saved;
static L18Symbol *l18_symbols;
static unsigned l18_nsymbols;
static L18Node *l18_nodes;
static unsigned l18_count, l18_capacity, l18_stack[256], l18_depth;
static L18Saved l18_saved[8]; static unsigned l18_irqdepth;
static L18Pending l18_pending;
static unsigned l18_current, l18_charge_token, l18_floor_token, l18_branch_token;
static uint32_t l18_vbr, l18_lastpc;
static uint64_t *l18_flat, l18_charged;
static unsigned l18_sample;
static FILE *l18_node_out, *l18_flat_out, *l18_audit_out;
static const char *l18_trace;
static int l18_enabled;

static void l18_die(const char *message) { fprintf(stderr,"logic18: %s\n",message); exit(2); }
static unsigned l18_entry(uint32_t pc) {
    unsigned lo=1, hi=l18_nsymbols;
    while(lo<hi) { unsigned mid=lo+(hi-lo)/2; if(l18_symbols[mid].start<pc) lo=mid+1; else hi=mid; }
    return lo<l18_nsymbols && l18_symbols[lo].start==pc ? lo : 0;
}
static unsigned l18_function(uint32_t pc) {
    unsigned lo=1, hi=l18_nsymbols;
    while(lo<hi) { unsigned mid=lo+(hi-lo)/2; if(l18_symbols[mid].start<=pc) lo=mid+1; else hi=mid; }
    if(lo<=1) return 0;
    unsigned n=lo-1;
    /* Size-zero symbols deliberately have no inferred PC range. */
    return pc<l18_symbols[n].end ? n : 0;
}
static unsigned l18_new(unsigned parent,unsigned symbol,unsigned kind,uint32_t ret) {
    if(l18_count==l18_capacity) {
        l18_capacity=l18_capacity?l18_capacity*2:4096;
        l18_nodes=realloc(l18_nodes,l18_capacity*sizeof(*l18_nodes));
        if(!l18_nodes) l18_die("node allocation failed");
    }
    unsigned n=l18_count++;
    memset(&l18_nodes[n],0,sizeof(l18_nodes[n]));
    l18_nodes[n].parent=parent; l18_nodes[n].symbol=symbol;
    l18_nodes[n].kind=kind; l18_nodes[n].ret=ret;
    if(parent<n) l18_nodes[n].owner=l18_nodes[parent].owner;
    if(kind==L18_IRQ || l18_irqdepth) l18_nodes[n].owner=5;
    else if(symbol && l18_symbols[symbol].owner) l18_nodes[n].owner=l18_symbols[symbol].owner;
    return n;
}
static void l18_abandon(unsigned kind) {
    for(unsigned i=0;i<l18_depth;i++) l18_nodes[l18_stack[i]].invalid=1;
    l18_depth=1; l18_stack[0]=l18_new(0,0,kind,0);
    l18_pending.action=L18_NONE;
}
static void l18_tail(unsigned target_entry) {
    unsigned old=l18_stack[l18_depth-1];
    l18_nodes[old].invalid=1;
    if(l18_depth<=1) { l18_abandon(L18_TAIL); return; }
    /* Keep proven caller ancestry, but never claim this tail's function identity.
     * Only its observed eventual return address can validate rejoining callers. */
    unsigned n=l18_new(l18_stack[l18_depth-2],0,L18_TAIL,l18_nodes[old].ret);
    if(!l18_irqdepth && target_entry && l18_symbols[target_entry].owner)
        l18_nodes[n].owner=l18_symbols[target_entry].owner;
    l18_stack[l18_depth-1]=n;
}
static int l18_irq_entry(uint32_t pc) {
    return l18_vbr && (pc==l18_vbr+0x100 || pc==l18_vbr+0x400 || pc==l18_vbr+0x600);
}
static void l18_before(uint32_t pc,uint16_t op) {
    if(!l18_enabled) return;
    if(l18_irq_entry(pc)) {
        if(l18_irqdepth>=8) l18_die("IRQ nesting overflow");
        L18Saved *s=&l18_saved[l18_irqdepth++];
        memcpy(s->stack,l18_stack,l18_depth*sizeof(unsigned)); s->depth=l18_depth;
        s->pending=l18_pending; s->resume=l18_lastpc+2;
        l18_depth=1; l18_stack[0]=l18_new(0,0,L18_IRQ,0);
        memset(&l18_pending,0,sizeof(l18_pending));
    } else if(l18_pending.action && !l18_pending.slots) {
        L18Pending p=l18_pending; l18_pending.action=L18_NONE;
        unsigned entry=l18_entry(pc);
        if(p.action==L18_DO_RTE) {
            if(!l18_irqdepth) l18_abandon(L18_THREAD);
            else {
                for(unsigned i=0;i<l18_depth;i++) l18_nodes[l18_stack[i]].invalid=1;
                L18Saved *s=&l18_saved[--l18_irqdepth];
                memcpy(l18_stack,s->stack,s->depth*sizeof(unsigned)); l18_depth=s->depth;
                l18_pending=s->pending;
                /* Context-changing RTE must not resume a guessed owner stack. */
                if(pc!=s->resume || l18_pending.action) l18_abandon(L18_THREAD);
            }
        } else if(p.action==L18_DO_RETURN) {
            unsigned n=l18_stack[l18_depth-1];
            if(l18_depth>1 && l18_nodes[n].ret==pc) {
                l18_nodes[n].complete=1; --l18_depth;
            } else l18_abandon(L18_THREAD);
        } else if(p.action==L18_DO_CALL) {
            if(entry && l18_symbols[entry].barrier) l18_abandon(L18_THREAD);
            if(l18_depth>=256) l18_die("call depth overflow");
            unsigned n=l18_new(l18_stack[l18_depth-1],entry,L18_CALL,p.ret);
            l18_stack[l18_depth++]=n;
        } else if((p.action==L18_DO_JUMP || p.action==L18_DO_COND) && entry && l18_symbols[entry].barrier) {
            l18_abandon(L18_THREAD);
        } else if(p.action==L18_DO_JUMP || p.action==L18_DO_COND) {
            L18Node *active=&l18_nodes[l18_stack[l18_depth-1]];
            unsigned symbol=active->symbol;
            int inside=symbol && pc>=l18_symbols[symbol].start && pc<l18_symbols[symbol].end;
            /* A same-entry unconditional transfer may be tail recursion. */
            if(active->kind==L18_CALL && (!inside || (p.action==L18_DO_JUMP && entry)))
                l18_tail(entry);
        }
    } else if(l18_pending.action && l18_pending.slots) --l18_pending.slots;
    l18_current=l18_stack[l18_depth-1];
    l18_charge_token=l18_current;
    if((op&0xf000)==0xb000 || (op&0xf0ff)==0x400b || (op&0xf0ff)==0x0003)
        l18_pending=(L18Pending){L18_DO_CALL,1,pc+4,pc};
    else if(op==0x000b) l18_pending=(L18Pending){L18_DO_RETURN,1,0,pc};
    else if(op==0x002b) l18_pending=(L18Pending){L18_DO_RTE,1,0,pc};
    else if((op&0xf000)==0xa000 || (op&0xf0ff)==0x402b || (op&0xf0ff)==0x0023)
        l18_pending=(L18Pending){L18_DO_JUMP,1,0,pc};
    else if((op&0xff00)==0x8900 || (op&0xff00)==0x8b00)
        l18_pending=(L18Pending){L18_DO_COND,0,0,pc};
    else if((op&0xff00)==0x8d00 || (op&0xff00)==0x8f00)
        l18_pending=(L18Pending){L18_DO_COND,1,0,pc};
    l18_lastpc=pc;
}
static void l18_charge(unsigned token,uint32_t pc,uint64_t fixed_cycles) {
    if(!l18_enabled) return;
    if(token>=l18_count) l18_die("stale charge token");
    l18_nodes[token].self+=fixed_cycles;
    l18_flat[l18_function(pc)]+=fixed_cycles;
    l18_charged+=fixed_cycles;
}
static void l18_begin(const char *trace) {
    if(!l18_enabled) return;
    l18_count=0; l18_depth=1; l18_irqdepth=0; l18_lastpc=0;
    l18_pending=(L18Pending){0}; l18_trace=trace; l18_charged=0;
    memset(l18_flat,0,l18_nsymbols*sizeof(*l18_flat));
    l18_stack[0]=l18_new(0,0,L18_CUT,0);
    l18_current=l18_charge_token=l18_floor_token=l18_branch_token=0;
}
static void l18_end(void) {
    if(!l18_enabled) return;
    uint64_t total=0,flat=0;
    for(unsigned i=0;i<l18_count;i++) { total+=l18_nodes[i].self; l18_nodes[i].inclusive=l18_nodes[i].self; }
    for(unsigned i=l18_count;i-->1;) {
        L18Node *n=&l18_nodes[i];
        if(n->parent<i) l18_nodes[n->parent].inclusive+=n->inclusive;
    }
    for(unsigned i=0;i<l18_count;i++) {
        L18Node *n=&l18_nodes[i];
        fprintf(l18_node_out,"%u\t%u\t%u\t%u\t%u\t%u\t%u\t%u\t%llu\t%llu\n",l18_sample,i,n->parent,n->symbol,n->kind,n->owner,n->complete,n->invalid,(unsigned long long)n->self,(unsigned long long)n->inclusive);
    }
    for(unsigned i=0;i<l18_nsymbols;i++) if(l18_flat[i]) {
        flat+=l18_flat[i]; fprintf(l18_flat_out,"%u\t%u\t%llu\n",l18_sample,i,(unsigned long long)l18_flat[i]);
    }
    if(total!=flat || total!=l18_charged) l18_die("self-cost conservation failed");
    fprintf(l18_audit_out,"%u\t%s\t%u\t%llu\t%llu\t%llu\n",l18_sample++,l18_trace,l18_count,(unsigned long long)total,(unsigned long long)flat,(unsigned long long)l18_charged);
    fflush(l18_node_out); fflush(l18_flat_out); fflush(l18_audit_out);
}
static void l18_init(const char *symbols,const char *out) {
    if(!symbols) return;
    FILE *f=fopen(symbols,"r"); if(!f) l18_die("cannot open symbol table");
    unsigned cap=16384; l18_symbols=calloc(cap,sizeof(*l18_symbols)); l18_nsymbols=1;
    char line[1024];
    while(fgets(line,sizeof(line),f)) {
        L18Symbol s={0};
        if(sscanf(line,"vbr %x",&l18_vbr)==1) continue;
        if(sscanf(line,"%x\t%x\t%d\t%d\t%511[^\n]",&s.start,&s.end,&s.owner,&s.barrier,s.name)!=5) continue;
        if(l18_nsymbols>=cap) l18_die("symbol capacity exceeded");
        if(l18_nsymbols>1 && s.start<=l18_symbols[l18_nsymbols-1].start) l18_die("symbols not unique and sorted");
        l18_symbols[l18_nsymbols++]=s;
    }
    fclose(f); l18_flat=calloc(l18_nsymbols,sizeof(*l18_flat));
    if(!l18_symbols || !l18_flat) l18_die("symbol allocation failed");
    char path[4096];
    snprintf(path,sizeof(path),"%s.contexts.tsv",out); l18_node_out=fopen(path,"w");
    snprintf(path,sizeof(path),"%s.function_frames.tsv",out); l18_flat_out=fopen(path,"w");
    snprintf(path,sizeof(path),"%s.context_audit.tsv",out); l18_audit_out=fopen(path,"w");
    if(!l18_node_out || !l18_flat_out || !l18_audit_out) l18_die("cannot open outputs");
    fputs("sample\tnode\tparent\tsymbol\tkind\towner\tcomplete\tinvalid\tself16\tinclusive16\n",l18_node_out);
    fputs("sample\tsymbol\tcycles16\n",l18_flat_out);
    fputs("sample\ttrace\tnodes\tnode_self16\tflat_self16\tcharged16\n",l18_audit_out);
    l18_enabled=1;
}
#endif
