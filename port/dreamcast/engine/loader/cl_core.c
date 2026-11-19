/* cl_core.c: the console side of the console-loop protocol (lane eng-loop, 2026-11-19).
   docs/engine/CONSOLE_LOOP.md sections 3 and 4. No hardware here: cl_platform_t supplies the link, the clock, the
   memory and the hand-off area. The one rule that matters: exec_pending is set only for the session whose image
   passed the stream CRC, the bounded inflate to exactly raw_len bytes and the SHA-256 in LOAD. */
#include "cl_core.h"
#include <stdio.h>
#include <string.h>

#define ACK_EVERY 4
#define ACK_DELAY_MS 150
#define HELLO_IDLE_MS 1000
#define HELLO_BUSY_MS 3000
#define ERR_GAP_MS 500
#define REPQ_MAX 8
/* the image must end below the loader's main stack (64 KiB under the hand-off area), where arch_exec_at keeps its
   trampoline while it copies */
#define CL_IMAGE_END (CL_HANDOFF_ADDR - 0x11000u)

const char *cl_err_name(int code) {
    switch (code) {
    case CL_OK: return "ok";
    case CL_E_COMP_CRC: return "stream crc";
    case CL_E_INFLATE: return "inflate";
    case CL_E_RAW_LEN: return "raw length";
    case CL_E_SHA: return "sha256";
    case CL_E_SIZE: return "size";
    case CL_E_ADDR: return "load address";
    case CL_E_NOMEM: return "no memory";
    case CL_E_NOT_VERIFIED: return "not verified";
    case CL_E_SESSION: return "unknown session";
    case CL_E_BAD_LOAD: return "bad load";
    case CL_E_CODEC: return "codec";
    case CL_E_NO_REPORT: return "no report";
    case CL_E_BUSY: return "busy";
    default: return "?";
    }
}

static void logf_(cl_core_t *c, const char *fmt, ...) __attribute__((format(printf, 2, 3)));
#include <stdarg.h>
static void logf_(cl_core_t *c, const char *fmt, ...) {
    if (!c->p.log) return;
    char b[160];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(b, sizeof(b), fmt, ap);
    va_end(ap);
    c->p.log(c->p.ctx, b);
}

static void out(cl_core_t *c, uint8_t type, uint32_t session, uint32_t a, uint16_t b, const void *pl, uint16_t len) {
    uint8_t d[CL_DGRAM_MAX];
    size_t n = cl_frame(d, type, session, a, b, pl, len);
    if (n && c->p.send(c->p.ctx, d, n)) c->tx_pkts++;
}

static void err(cl_core_t *c, uint32_t session, int code, int always) {
    uint32_t now = c->p.now_ms(c->p.ctx);
    if (!always && now - c->last_err_ms < ERR_GAP_MS) return;
    c->last_err_ms = now;
    const char *t = cl_err_name(code);
    out(c, CL_ERR, session, (uint32_t)code, 0, t, (uint16_t)strlen(t));
}

static void drop_image(cl_core_t *c) {
    if (c->raw && c->raw != c->comp) c->p.free(c->raw);
    if (c->comp) c->p.free(c->comp);
    if (c->bitmap) c->p.free(c->bitmap);
    c->comp = c->raw = c->bitmap = NULL;
    c->have = c->next_needed = c->nchunks = 0;
    c->verified = 0;
    c->verdict = -1;
    c->state = CL_ST_IDLE;
}

void cl_core_hello(cl_core_t *c) {
    const cl_handoff_hdr_t *h = &c->p.handoff->h;
    uint8_t pl[CL_HELLO_LEN];
    memset(pl, 0, sizeof(pl));
    uint32_t v[16] = {c->boot_count, c->p.now_ms(c->p.ctx) - c->boot_ms, (uint32_t)c->state, c->session,
                      c->have, c->nchunks, c->rx_bytes, c->rx_bad,
                      h->run_id, h->state, h->report_len, h->report_crc,
                      (uint32_t)h->exit_code, c->p.console_ip, c->p.max_raw, (uint32_t)c->verdict};
    for (int i = 0; i < 16; ++i) cl_wr32(pl + 4 * i, v[i]);
    if (c->p.build) strncpy((char *)pl + 64, c->p.build, 31);
    out(c, CL_HELLO, c->session, c->rx_pkts, 0, pl, sizeof(pl));
    c->last_hello_ms = c->p.now_ms(c->p.ctx);
}

static void send_ack(cl_core_t *c) {
    uint8_t pl[16 + CL_ACK_BITS / 8];
    uint32_t left = c->nchunks - c->next_needed;
    uint32_t nb = (left + 7) / 8;
    if (nb > CL_ACK_BITS / 8) nb = CL_ACK_BITS / 8;
    cl_wr32(pl, c->have);
    cl_wr32(pl + 4, c->rx_bad);
    cl_wr32(pl + 8, c->rx_dup);
    cl_wr32(pl + 12, c->nchunks);
    memset(pl + 16, 0, nb);
    for (uint32_t i = 0; i < nb * 8 && c->next_needed + i < c->nchunks; ++i) {
        uint32_t k = c->next_needed + i;
        if (c->bitmap[k >> 3] & (1u << (k & 7))) pl[16 + (i >> 3)] |= (uint8_t)(1u << (i & 7));
    }
    out(c, CL_ACK, c->session, c->next_needed, (uint16_t)nb, pl, (uint16_t)(16 + nb));
    c->new_since_ack = 0;
    c->ack_due = 0;
}

static void send_verdict(cl_core_t *c) {
    char t[64];
    snprintf(t, sizeof(t), "%s raw=%u", cl_err_name(c->verdict), (unsigned)c->raw_len);
    out(c, CL_VERDICT, c->session, (uint32_t)c->verdict, 0, t, (uint16_t)strlen(t));
}

/* the whole-image check: stream CRC, bounded inflate to exactly raw_len, SHA-256 */
static int verify(cl_core_t *c) {
    if (cl_crc32(0, c->comp, c->comp_len) != c->comp_crc) return CL_E_COMP_CRC;
    if (c->codec == CL_CODEC_DEFLATE) {
        if (!c->raw) c->raw = (uint8_t *)c->p.alloc(c->raw_len + 4);   /* + 4: the jump copies whole words */
        if (!c->raw) return CL_E_NOMEM;
        memset(c->raw + c->raw_len, 0, 4);
        size_t got = 0;
        int r = cl_inflate(c->comp, c->comp_len, c->raw, c->raw_len, &got);
        if (r == -2) return CL_E_RAW_LEN;   /* the stream holds more than raw_len */
        if (r) return CL_E_INFLATE;
        if (got != c->raw_len) return CL_E_RAW_LEN;
    } else {
        c->raw = c->comp;
    }
    uint8_t sha[32];
    cl_sha256_t s;
    cl_sha256_init(&s);
    cl_sha256_update(&s, c->raw, c->raw_len);
    cl_sha256_final(&s, sha);
    if (memcmp(sha, c->sha, 32)) return CL_E_SHA;
    return CL_OK;
}

static void finish(cl_core_t *c) {
    uint32_t t0 = c->p.now_ms(c->p.ctx);
    int r = verify(c);
    c->verdict = r;
    logf_(c, "verify %s (%u ms)", cl_err_name(r), (unsigned)(c->p.now_ms(c->p.ctx) - t0));
    if (r == CL_OK) {
        c->verified = 1;
        c->state = CL_ST_VERIFIED;
        if (c->codec == CL_CODEC_DEFLATE && c->comp) { c->p.free(c->comp); c->comp = NULL; }
    } else {
        /* a refused image is dropped whole: nothing of it can run, and a resend starts clean */
        if (c->raw && c->raw != c->comp) c->p.free(c->raw);
        c->raw = NULL;
        c->verified = 0;
        c->state = CL_ST_FAILED;
        if (c->comp) { c->p.free(c->comp); c->comp = NULL; }
        if (c->bitmap) { c->p.free(c->bitmap); c->bitmap = NULL; }
        c->have = c->next_needed = 0;
    }
    send_verdict(c);
}

static void on_load(cl_core_t *c, uint32_t session, const uint8_t *pl, unsigned len) {
    if (len < CL_LOAD_FIXED) { err(c, session, CL_E_BAD_LOAD, 1); return; }
    uint32_t comp_len = cl_rd32(pl), raw_len = cl_rd32(pl + 4), chunk = cl_rd32(pl + 8), nchunks = cl_rd32(pl + 12);
    uint8_t codec = pl[16], flags = pl[17];
    uint16_t deadline = cl_rd16(pl + 18);
    uint32_t addr = cl_rd32(pl + 20);
    const uint8_t *sha = pl + 24;
    uint32_t comp_crc = cl_rd32(pl + 56);
    unsigned args_len = cl_rd16(pl + 60);
    if (args_len > CL_ARGS_MAX || CL_LOAD_FIXED + args_len > len) { err(c, session, CL_E_BAD_LOAD, 1); return; }
    int e = CL_OK;
    if (chunk != CL_CHUNK || !comp_len || !raw_len || nchunks != (comp_len + CL_CHUNK - 1) / CL_CHUNK) e = CL_E_BAD_LOAD;
    else if (codec != CL_CODEC_NONE && codec != CL_CODEC_DEFLATE) e = CL_E_CODEC;
    else if (codec == CL_CODEC_NONE && comp_len != raw_len) e = CL_E_BAD_LOAD;
    else if (addr != CL_LOAD_ADDR) e = CL_E_ADDR;
    else if (raw_len > c->p.max_raw || (uint64_t)addr + raw_len + 4 > CL_IMAGE_END) e = CL_E_SIZE;
    else if (comp_len > raw_len + raw_len / 8 + 1024) e = CL_E_SIZE;   /* beyond deflate's worst case */
    if (e) { err(c, session, e, 1); return; }
    int same = (c->comp || c->verified) && c->comp_len == comp_len && c->raw_len == raw_len && c->codec == codec &&
               c->comp_crc == comp_crc && !memcmp(c->sha, sha, 32);
    if (!same) {
        drop_image(c);
        c->comp = (uint8_t *)c->p.alloc(comp_len + 4);
        if (c->comp) memset(c->comp + comp_len, 0, 4);
        c->bitmap = (uint8_t *)c->p.alloc(nchunks / 8 + 1);
        if (!c->comp || !c->bitmap) { drop_image(c); err(c, session, CL_E_NOMEM, 1); return; }
        memset(c->bitmap, 0, nchunks / 8 + 1);
        c->comp_len = comp_len; c->raw_len = raw_len; c->nchunks = nchunks; c->codec = codec;
        c->comp_crc = comp_crc; c->load_addr = addr;
        memcpy(c->sha, sha, 32);
        c->have = c->next_needed = 0;
        c->state = CL_ST_RECEIVING;
        logf_(c, "load %08x comp %u raw %u chunks %u", (unsigned)session, (unsigned)comp_len, (unsigned)raw_len,
              (unsigned)nchunks);
    } else {
        logf_(c, "load %08x resumes at %u/%u", (unsigned)session, (unsigned)c->have, (unsigned)c->nchunks);
    }
    c->session = session;
    c->flags = flags;
    c->deadline_s = deadline;
    memcpy(c->args, pl + CL_LOAD_FIXED, args_len);
    c->args[args_len] = 0;
    if (c->verified) {
        c->have = c->next_needed = c->nchunks;
        send_ack(c);
        send_verdict(c);
    } else {
        send_ack(c);
    }
}

static void on_data(cl_core_t *c, uint32_t session, uint32_t idx, const uint8_t *pl, unsigned len) {
    if (session != c->session || c->state != CL_ST_RECEIVING || !c->comp) {
        if (session == c->session && c->verified) { c->ack_due = 1; return; }   /* late duplicate */
        err(c, session, CL_E_SESSION, 0);
        return;
    }
    if (idx >= c->nchunks) { c->rx_bad++; return; }
    unsigned want = idx == c->nchunks - 1 ? c->comp_len - idx * CL_CHUNK : CL_CHUNK;
    if (len != want) { c->rx_bad++; return; }
    if (c->bitmap[idx >> 3] & (1u << (idx & 7))) {
        c->rx_dup++;
        c->ack_due = 1;   /* the PC missed an ack */
        return;
    }
    memcpy(c->comp + (size_t)idx * CL_CHUNK, pl, len);
    c->bitmap[idx >> 3] |= (uint8_t)(1u << (idx & 7));
    c->have++;
    while (c->next_needed < c->nchunks && (c->bitmap[c->next_needed >> 3] & (1u << (c->next_needed & 7))))
        c->next_needed++;
    c->new_since_ack++;
    c->last_data_ms = c->p.now_ms(c->p.ctx);
    if (c->have == c->nchunks) {
        send_ack(c);
        finish(c);
    } else if (c->new_since_ack >= ACK_EVERY) {
        send_ack(c);
    } else {
        c->ack_due = 1;
    }
}

static void on_run(cl_core_t *c, uint32_t session) {
    if (session != c->session || !c->verified || !c->raw || c->verdict != CL_OK) {
        err(c, session, CL_E_NOT_VERIFIED, 1);
        logf_(c, "run %08x refused (not verified)", (unsigned)session);
        return;
    }
    if (c->exec_pending) return;
    cl_handoff_t *a = c->p.handoff;
    cl_handoff_hdr_t *h = &a->h;
    h->run_id = session;
    h->state = CL_RUN_RUNNING;
    h->exit_code = 0;
    h->deadline_s = c->deadline_s;
    h->flags = c->flags;
    h->link_host = c->p.link_host; h->link_port = c->p.link_port; h->link_lport = c->p.link_lport;
    h->console_ip = c->p.console_ip;
    memset(h->number, 0, sizeof(h->number));
    if (c->p.number) strncpy(h->number, c->p.number, sizeof(h->number) - 1);
    memset(h->args, 0, sizeof(h->args));
    memcpy(h->args, c->args, strlen(c->args) < sizeof(h->args) ? strlen(c->args) : sizeof(h->args) - 1);
    h->crash_evt = h->crash_pc = h->crash_pr = h->crash_sp = 0;
    h->report_len = 0;
    h->report_crc = 0;
    cl_handoff_seal(a);
    out(c, CL_EXEC, session, c->raw_len, 0, NULL, 0);
    c->exec_pending = 1;
    c->state = CL_ST_EXEC;
    logf_(c, "run %08x: exec %u bytes", (unsigned)session, (unsigned)c->raw_len);
}

static void on_repq(cl_core_t *c, uint32_t run, uint32_t off, unsigned count) {
    const cl_handoff_t *a = c->p.handoff;
    const cl_handoff_hdr_t *h = &a->h;
    if (run != h->run_id || h->state == CL_RUN_NONE || h->state == CL_RUN_RUNNING || off % CL_CHUNK) {
        err(c, run, CL_E_NO_REPORT, 1);
        return;
    }
    if (count > REPQ_MAX) count = REPQ_MAX;
    if (!count) count = 1;
    for (unsigned k = 0; k < count; ++k) {
        uint32_t o = off + k * CL_CHUNK;
        if (o >= h->report_len && !(o == 0 && h->report_len == 0)) break;
        uint32_t n = h->report_len - o < CL_CHUNK ? h->report_len - o : CL_CHUNK;
        out(c, CL_REPORT, run, o, (uint16_t)(o + n >= h->report_len), a->report + o, (uint16_t)n);
    }
}

void cl_core_input(cl_core_t *c, const uint8_t *d, size_t n) {
    c->rx_pkts++;
    c->rx_bytes += (uint32_t)n;
    int len = cl_unframe(d, n);
    if (len < 0) { c->rx_bad++; return; }
    uint8_t type = d[3];
    uint32_t session = cl_rd32(d + 4), a = cl_rd32(d + 8);
    uint16_t b = cl_rd16(d + 14);
    const uint8_t *pl = d + CL_HDR;
    if (c->exec_pending) return;   /* jumping: nothing else may change the image */
    switch (type) {
    case CL_LOAD: on_load(c, session, pl, (unsigned)len); break;
    case CL_DATA: on_data(c, session, a, pl, (unsigned)len); break;
    case CL_RUN: on_run(c, session); break;
    case CL_REPQ: on_repq(c, session, a, b); break;
    case CL_REPDONE:
        if (session == c->p.handoff->h.run_id && c->p.handoff->h.state != CL_RUN_RUNNING) {
            c->p.handoff->h.state = CL_RUN_NONE;
            c->p.handoff->h.report_len = 0;
            c->p.handoff->h.report_crc = 0;
            cl_handoff_seal(c->p.handoff);
        }
        cl_core_hello(c);
        break;
    case CL_PING: cl_core_hello(c); break;
    case CL_ABORT:
        if (session == c->session) { drop_image(c); c->session = 0; }
        cl_core_hello(c);
        break;
    case CL_VERIFY:
        if (session == c->session && c->verdict >= 0) send_verdict(c);
        else if (session == c->session && c->comp) send_ack(c);
        else err(c, session, CL_E_SESSION, 1);
        break;
    default: c->rx_bad++; break;
    }
}

void cl_core_tick(cl_core_t *c) {
    uint32_t now = c->p.now_ms(c->p.ctx);
    if (c->exec_pending) return;
    if (c->ack_due && c->comp && (now - c->last_data_ms >= ACK_DELAY_MS || c->new_since_ack == 0)) send_ack(c);
    else if (c->ack_due && c->verified) { c->ack_due = 0; send_ack(c); }
    int busy = c->state == CL_ST_RECEIVING && now - c->last_data_ms < 3000;
    if (now - c->last_hello_ms >= (uint32_t)(busy ? HELLO_BUSY_MS : HELLO_IDLE_MS)) cl_core_hello(c);
}

void cl_core_init(cl_core_t *c, const cl_platform_t *p) {
    memset(c, 0, sizeof(*c));
    c->p = *p;
    c->verdict = -1;
    c->boot_ms = c->p.now_ms(c->p.ctx);
    c->last_hello_ms = c->boot_ms - HELLO_IDLE_MS;
    cl_handoff_t *a = c->p.handoff;
    if (!cl_handoff_valid(a)) {
        memset(&a->h, 0, sizeof(a->h));
        a->h.boot_count = 1;
        logf_(c, "hand-off: fresh (power-on or overwritten)");
    } else {
        a->h.boot_count++;
        if (a->h.state == CL_RUN_RUNNING) {
            a->h.state = CL_RUN_LOST;   /* came back without the client's hand-in (no client, reboot, power) */
            a->h.report_len = 0;
            a->h.report_crc = 0;
        } else if (a->h.state != CL_RUN_NONE && !cl_handoff_report_ok(a)) {
            a->h.report_len = 0;        /* the run's state stands; its report did not survive */
            a->h.report_crc = 0;
        }
        logf_(c, "hand-off: boot %u, run %08x state %u report %u bytes", (unsigned)a->h.boot_count,
              (unsigned)a->h.run_id, (unsigned)a->h.state, (unsigned)a->h.report_len);
    }
    cl_handoff_seal(a);
    c->boot_count = a->h.boot_count;
}
