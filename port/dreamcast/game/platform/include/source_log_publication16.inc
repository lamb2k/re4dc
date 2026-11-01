// Included only by mem.cpp, inside its existing C linkage block.
re4dc::log_publication16::State re4dc_log_publication16_state;

static int logEntrySr16()
{
    // Use the existing KOS IRQ API, including exact original SR restoration.
    // This constant-work probe is separate from every bounded copy window.
    const int entry = irq_disable();
    irq_restore(entry);
    return entry;
}

static re4dc::log_publication16::Result logCopyOwned16(const char* data, unsigned long len, bool stopping)
{
    using namespace re4dc::log_publication16;
    auto& state = re4dc_log_publication16_state;
    do {
        const int irq = irq_disable();
#if defined(RE4DC_LOG_RING_HDR) && RE4DC_LOG_RING_HDR
        if (!re4dc_logring.magic) {
            re4dc_logring.size = RE4DC_LOG_SIZE;
            re4dc_logring.nmagic = ~0x5A53474CUL;
            __asm__ __volatile__("" ::: "memory");
            re4dc_logring.magic = 0x5A53474CUL;
        }
#endif
        const unsigned long part = len < window ? len : window;
        for (unsigned long i = 0; i < part; ++i) {
            if (!stopping && state.stopped.load(std::memory_order_acquire)) {
                irq_restore(irq);
                return abandoned;
            }
            // Preserve the old bytewise forward semantics even when data aliases
            // the ring or the live head bytes. Do not snapshot either operand.
            re4dc_logbuf[re4dc_log_head % RE4DC_LOG_SIZE] = *data++;
            __asm__ __volatile__("" ::: "memory");
            re4dc_log_head++;
            __asm__ __volatile__("" ::: "memory");
        }
        len -= part;
        irq_restore(irq);
    } while (len);
    return !stopping && state.stopped.load(std::memory_order_acquire) ? abandoned : accepted;
}

int re4dc_log_write16(const char* data, unsigned long len)
{
    using namespace re4dc::log_publication16;
    auto& state = re4dc_log_publication16_state;
    if (!data && len) return state.report(invalid);
    const int sr = logEntrySr16();
    if (len > window && ((sr & 0xf0) || irq_inside_int())) return state.report(context);
    Result result = state.claim();
    if (result != accepted) return state.report(result);
    result = logCopyOwned16(data, len, false);
    state.release();
    state.report(result);
#if defined(RE4DC_LOG_CRASH_TEST) && RE4DC_LOG_CRASH_TEST
    if (result == accepted) logCrashAppend16();
#endif
    return result;
}

int re4dc_log_terminal16(const re4dc::log_publication16::Evidence* evidence)
{
    using namespace re4dc::log_publication16;
    auto& state = re4dc_log_publication16_state;
    // Stop before copying: a nested terminal invocation cannot let a suspended
    // normal publisher resume and claim whole-call completion.
    state.stopped.store(true, std::memory_order_release);
    state.capture(*evidence); // lost/unfinished are explicit; published slots never change
    if (state.writer.test_and_set(std::memory_order_acquire)) return state.report(busy);
    Line line;
    line.text(evidence->kind == 1 ? "FAULT code=" : "HALT stop: line="); line.hex(evidence->code);
    line.text(" pc="); line.hex(evidence->pc);
    line.text(" pr="); line.hex(evidence->pr);
    line.text(" sp="); line.hex(evidence->sp);
    line.text(" sr="); line.hex(evidence->sr);
    line.text(" expevt="); line.hex(evidence->expevt);
    line.text(" tea="); line.hex(evidence->tea);
    line.text(" inside="); line.hex(evidence->inside);
    line.text(" tid="); line.hex(evidence->tid);
    line.text(" frame="); line.hex(evidence->frame);
    line.text("\n");
    Result result = logCopyOwned16(line.bytes, line.size, true);
    state.release();
    return state.report(result);
}
