#ifndef RE4DC_FALLBACK_ACTOR_AUDIT29_HPP
#define RE4DC_FALLBACK_ACTOR_AUDIT29_HPP

// Diagnostic only. Single writer: the game/render thread. QA formats between
// submissions on that same thread. Addresses are transient lookup keys, never
// retained backing, asset identities or dereferenced after the draw.
#include <stdint.h>
#include <stdio.h>
#include <string.h>

namespace re4dc { namespace fa29actor {
static_assert(sizeof(unsigned)==4, "diagnostic word size");
enum { Capacity = 32 };
struct Key { uintptr_t model, info, part; unsigned serial; };
struct Identity {
    unsigned tag, info_index, part_offset, positions, normals, stream_bytes;
    unsigned source_key, material_flags;
};
struct Context {
    unsigned material, ambient, tev_bits, controls, light_mask;
};
struct Row {
    Identity id;
    Context context;
    unsigned setups, exact_setups, exact_vertices, context_changes, path;
};
struct State {
    // Dense owner/serial keys: sixteen 32-byte lines on the SH-4, rather
    // than walking all the cold identity/lighting fields on every hit.
    // The source model serial prevents merging recycled addresses in a room.
    Key keys[Capacity];
    Row rows[Capacity];
    unsigned used, spill, overflow;
};
inline void add(State& state, unsigned& counter, unsigned amount) {
    if (amount > UINT32_MAX-counter) { counter=UINT32_MAX; state.overflow=1; }
    else counter+=amount;
}
inline unsigned find(const State& state, const Key& key) {
    for (unsigned i=0;i<state.used;++i)
        if (state.keys[i].model==key.model && state.keys[i].info==key.info &&
            state.keys[i].part==key.part && state.keys[i].serial==key.serial)
            return i;
    return Capacity;
}
inline unsigned observe(State& state, const Key& key, const Context& context,
                        unsigned path, bool* fresh) {
    *fresh=false;
    unsigned index=find(state,key);
    if (index==Capacity) {
        if (state.used==Capacity) { add(state,state.spill,1); return Capacity; }
        index=state.used++;
        state.keys[index]=key;
        state.rows[index]=Row{};
        state.rows[index].context=context;
        *fresh=true;
    }
    Row& row=state.rows[index];
    if (memcmp(&row.context,&context,sizeof(context))!=0) {
        add(state,row.context_changes,1);
        row.context=context;
    }
    row.path=path;
    add(state,row.setups,1);
    if (path==2) add(state,row.exact_setups,1);
    return index;
}
inline void vertices(State& state, const Key& key, unsigned count) {
    const unsigned index=find(state,key);
    if (index<Capacity) add(state,state.rows[index].exact_vertices,count);
}
inline unsigned line_count(const State& state) { return 1+2*state.used; }
inline int format_line(const State& state, unsigned line, char* out, unsigned capacity) {
    if (!out || !capacity) return 0;
    out[0]=0;
    int n;
    if (!line) {
        n=snprintf(out,capacity,"F29A rows=%u cap=%u spill=%u sat=%u scope=room context=latest units=setups,exact_vertices",
                   state.used,unsigned(Capacity),state.spill,state.overflow);
    } else {
        const unsigned index=(line-1)/2;
        if (index>=state.used) return 0;
        const Row& row=state.rows[index];
        if (line&1) {
            const Identity& id=row.id;
            n=snprintf(out,capacity,
                "F29P n=%u tag=%08x mi=%u off=%08x key=%08x pos=%u nrm=%u bytes=%u mf=%x calls=%u exact=%u verts=%u",
                index,id.tag,id.info_index,id.part_offset,id.source_key,id.positions,id.normals,id.stream_bytes,
                id.material_flags,row.setups,row.exact_setups,row.exact_vertices);
        } else {
            const Context& c=row.context;
            n=snprintf(out,capacity,"F29L n=%u mat=%08x amb=%08x tev=%08x ctl=%x mask=%x path=%u changes=%u",
                       index,c.material,c.ambient,c.tev_bits,c.controls,c.light_mask,row.path,row.context_changes);
        }
    }
    // Never present a clipped row as complete telemetry.
    if (n<0 || unsigned(n)>=capacity) { out[0]=0; return -1; }
    return n;
}
} }
#endif
