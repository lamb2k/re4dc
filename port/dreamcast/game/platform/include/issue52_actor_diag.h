#pragma once

// Default-off issue52 diagnostic. Source hooks pass integers only; the collector
// and crash renderer never dereference a candidate actor or its vtable.
extern "C" unsigned long re4dc_issue52_stage_base();
extern "C" void re4dc_issue52_actor_note(unsigned phase, unsigned frame,
                                         unsigned room, unsigned long actor);

// Only the real r10c list2 caller starts an attempt. Tokens are diagnostic call
// serials, NOT pool/module generations. Nested hooks must also match source TASK.
enum Issue52Admission {
    I52_ID_FILTER = 1, I52_STAGE, I52_ROOM, I52_ALREADY_SET, I52_ZERO_ID,
    I52_DEAD, I52_LIST_FILTER, I52_CAP, I52_CREATE_FAILED, I52_CREATED
};
enum Issue52Detail {
    I52_CONSTRUCT_BEGIN = 1, I52_CONSTRUCT_NO_ARC, I52_CONSTRUCT_INIT,
    I52_READ_CACHED, I52_READ_MISS, I52_READ_ABSENT, I52_READ_SUBMIT,
    I52_READ_NEGATIVE, I52_READ_COMPLETE
};
enum { I52_PENDING = 1, I52_COMPLETED = 2, I52_ABANDONED = 3 };

// Pure bounded collector, shared verbatim by the target wrappers and host checks.
// No pointers are followed, no source owner is retained, no dynamic allocation.
struct Issue52Attempt {
    unsigned serial, state, abandoned, frame, end_frame, room, entry, id;
    unsigned reason, construct, constructs, read_path, read_reason, negatives;
    unsigned long task, base, end_base, actor;
    int request, poll, first_negative, last_negative;

    unsigned begin(unsigned long owner, unsigned at, unsigned where,
                   unsigned no, unsigned enemy, unsigned long module)
    {
        if (!owner || where != 0x10c || no != 2) return 0;
        const unsigned next = serial + 1 ? serial + 1 : 1;
        const unsigned lost = abandoned + (state == I52_PENDING ? 1 : 0);
        *this = Issue52Attempt{};
        serial = next; abandoned = lost; state = I52_PENDING;
        task = owner; frame = at; room = where; entry = no; id = enemy;
        base = module;
        return serial;
    }
    bool matches(unsigned token, unsigned long owner) const
    {
        return token && serial == token && task == owner && state == I52_PENDING;
    }
    unsigned current(unsigned long owner, unsigned enemy) const
    {
        return state == I52_PENDING && task == owner && id == enemy &&
               construct <= 2 ? serial : 0;
    }
    void detail(unsigned token, unsigned long owner, unsigned kind, int a, int b)
    {
        if (!matches(token, owner)) return;
        if (kind == I52_CONSTRUCT_BEGIN) {
            // A reentrant construction in the same source task is ambiguous.
            // Invalidate attribution instead of merging two producer histories.
            if (construct == 1) { state = I52_ABANDONED; ++abandoned; }
            else {
                // A prior no-archive return may be retried by existing EM_MUST.
                construct = 1; ++constructs;
                read_path = read_reason = 0; request = poll = 0;
            }
            return;
        }
        if (construct != 1) return; // ignore nested work after initial construction
        switch (kind) {
        case I52_CONSTRUCT_NO_ARC: construct = 2; break;
        case I52_CONSTRUCT_INIT: construct = 3; break;
        case I52_READ_CACHED: read_path = 1; break;
        case I52_READ_MISS: read_path = 2; break;
        case I52_READ_ABSENT: read_reason = 1; break;
        case I52_READ_SUBMIT: request = a; break;
        case I52_READ_NEGATIVE:
            request = a; poll = b;
            if (!negatives) first_negative = b;
            last_negative = b; ++negatives; read_reason = 2;
            break;
        case I52_READ_COMPLETE: request = a; poll = b; read_reason = 3; break;
        }
    }
    void finish(unsigned token, unsigned long owner, unsigned why,
                unsigned long result, unsigned at, unsigned long module)
    {
        if (!matches(token, owner)) return;
        reason = why; actor = result; end_frame = at; end_base = module;
        state = I52_COMPLETED;
    }
};

static_assert(sizeof(Issue52Attempt) <= 128, "issue52 diagnostic record exceeds bound");

extern "C" unsigned re4dc_issue52_begin(unsigned long task, unsigned frame,
    unsigned room, unsigned entry, unsigned id);
extern "C" unsigned re4dc_issue52_current(unsigned long task, unsigned id);
extern "C" void re4dc_issue52_detail(unsigned token, unsigned long task,
    unsigned kind, int a, int b);
extern "C" void re4dc_issue52_finish(unsigned token, unsigned long task,
    unsigned reason, unsigned long actor, unsigned frame);
extern "C" unsigned long re4dc_issue52_source_task();
