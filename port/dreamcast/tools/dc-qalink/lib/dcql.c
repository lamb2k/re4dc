/* dcql.c: dc-qalink transport (modem dial, KOS libppp, one UDP socket, two bounded rings). MIT licence.
 *
 * Threads (both detached, static stacks, the caller's priority):
 *   dial thread (8 KiB): dials up to 3 times, negotiates PPP, opens the socket, leaves; also hangs up.
 *   PPP thread  (4 KiB): libppp's receive loop. dcql.mk compiles libppp from $(KOS_BASE)/addons/libppp with
 *     thd_create / thd_pass / modem_write_data / modem_read_data renamed to dcql_ppp_* below:
 *       - its stack comes from BSS instead of a 32 KiB KOS heap stack;
 *       - thd_pass sleeps 4 ms (libppp polls in a loop) and, once the link is up, moves datagrams: all received ones
 *         into the rx ring, then ONE queued datagram out, so libppp reads the line between sends (sending a whole
 *         backlog in one pass overflows the modem's 1 KiB rx buffer and loses incoming commands);
 *       - a modem write that makes no progress for 2 s, or any write while hanging up, discards instead of spinning.
 *   The modem driver's chain buffers and its timeout worker's stack also come from BSS (--wrap, see dcql.mk).
 * The KOS network stack runs without net_init(): fs_socket_init() + net_udp_init() only (no DHCP, no work-queue
 * thread). So no IPv4 fragment reassembly: every datagram stays <= DCQL_DATAGRAM_MAX both ways.
 * Hang-up order: stop the pump, drop the line (a blocked write then returns), enter PPP phase DEAD, wait for the PPP
 * thread to leave, then ppp_shutdown. If it does not leave, the state reports FAILED (-31) and the next start retries:
 * a thread that may hold libppp's mutex is never destroyed and its static stack is never reused under it.
 */
#undef DCQL_ENABLE
#define DCQL_ENABLE 1 /* this file is the implementation; dcql.mk only compiles it when DCQL_ENABLE=1 */
#include "dcql.h"

#include <kos.h>
#include <kos/thread.h>
#include <kos/worker_thread.h>
#include <kos/net.h>
#include <kos/fs_socket.h>
#include <arch/timer.h>
#include <arch/irq.h>
#include <dc/modem/modem.h>
#include <ppp/ppp.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <fcntl.h>
#include <unistd.h>
#include <string.h>
#include <stdio.h>
#include <stdarg.h>
#include <ctype.h>
#include <stdint.h>
#include <stdbool.h>

int _ppp_enter_phase(int phase); /* libppp ppp_internal.h */
int net_udp_init(void);          /* kernel/net/net_udp.c */

enum { kBulkCap = 2400 /* ~0.7 s of line at 33.6 kbps */, kWriteNoProgressMs = 2000, kRing = 4096 };

static volatile int g_state = DCQL_OFF, g_attempt, g_err, g_stop;
static volatile unsigned g_rate, g_tx_bytes, g_rx_bytes, g_tx_drops, g_bulk_skips, g_rx_drops, g_tx_stalls;
static unsigned char g_ip[4], g_peer[4];
static char g_number[24] = "1111111", g_user[24] = "dream", g_pass[24] = "dreamcast";
static unsigned g_host = 0xFFFFFFFFu, g_configured_host = 0xFFFFFFFFu; /* network order; all-ones = learn */
static unsigned short g_port = 52040, g_lport = 52040;
static int (*g_bulk_ok)(void);
static void (*g_logfn)(const char*);
static dcql_command_fn g_cmd;
static void* g_cmd_user;
static volatile int g_sock = -1;
static bool g_net_ready, g_ppp_init;
static volatile int g_dial_running, g_ppp_running;
static volatile bool g_retiring, g_tx_fault;
static bool g_write_waiting;
static uint64_t g_write_since;
static kthread_t* volatile g_ppp_thd;
static kthread_t* volatile g_dial_thd;
static volatile tid_t g_ppp_tid, g_dial_tid;
static unsigned char g_dial_stack[8192] __attribute__((aligned(32)));
static unsigned char g_ppp_stack[4096] __attribute__((aligned(32)));
static void* (*g_ppp_fn)(void*);
static unsigned g_tseq, g_lseq;

static void logf_(const char* fmt, ...) {
    if (!g_logfn) return;
    char b[128];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(b, sizeof(b), fmt, ap);
    va_end(ap);
    g_logfn(b);
}

static bool thread_busy(tid_t id) {
    if (!id) return false;
    /* Never dereference a detached thread after it may be reaped: look it up by id with IRQs masked. */
    const int irq = irq_disable();
    const kthread_t* t = thd_by_tid(id);
    const bool busy = t && t->state != STATE_ZOMBIE && t->state != STATE_FINISHED;
    irq_restore(irq);
    return busy;
}

/* ---- single-producer single-consumer datagram rings: [u16 length][bytes] */
typedef struct {
    unsigned char buf[kRing];
    volatile unsigned head, tail; /* byte counters: head by the producer, tail by the consumer */
} ring_t;
static ring_t g_tx, g_rx;
static unsigned char g_pkt[DCQL_DATAGRAM_MAX + 8]; /* the PPP thread's datagram buffer */

static unsigned ring_used(const ring_t* r) { return r->head - r->tail; }
static bool ring_put(ring_t* r, const void* p, unsigned n) {
    if (!p || !n || n > DCQL_DATAGRAM_MAX || ring_used(r) + n + 2 > kRing) return false;
    unsigned h = r->head;
    r->buf[h++ % kRing] = (unsigned char) n;
    r->buf[h++ % kRing] = (unsigned char) (n >> 8);
    for (unsigned i = 0; i < n; ++i) r->buf[h++ % kRing] = ((const unsigned char*) p)[i];
    __asm__ __volatile__("" ::: "memory");
    r->head = h;
    return true;
}
/* -1 empty; -2 retired whole because it did not fit (a truncated command could be a different valid command). */
static int ring_get(ring_t* r, void* p, unsigned max) {
    if (r->head == r->tail) return -1;
    unsigned t = r->tail;
    unsigned n = r->buf[t++ % kRing];
    n |= (unsigned) r->buf[t++ % kRing] << 8;
    if (n > max || !p) {
        __asm__ __volatile__("" ::: "memory");
        r->tail = t + n;
        return -2;
    }
    for (unsigned i = 0; i < n; ++i, ++t) ((unsigned char*) p)[i] = r->buf[t % kRing];
    __asm__ __volatile__("" ::: "memory");
    r->tail = t;
    return (int) n;
}
static void ring_clear(ring_t* r) { r->tail = r->head; }

/* ---- the PPP thread's pump: everything received in, then at most one datagram out */
static void pump(void) {
    if (!modem_is_connected()) {
        g_state = DCQL_DROPPED;
        logf_("dcql: line dropped");
        return;
    }
    int n;
    for (;;) {
        struct sockaddr_in from;
        socklen_t fl = sizeof(from);
        n = recvfrom(g_sock, g_pkt, sizeof(g_pkt), 0, (struct sockaddr*) &from, &fl);
        if (n == 0) { ++g_rx_drops; continue; }
        if (n < 0) break;
        g_rx_bytes += n;
        if (n > DCQL_DATAGRAM_MAX || fl < sizeof(from) || from.sin_family != AF_INET || from.sin_port != htons(g_port) ||
            (g_host != 0xFFFFFFFFu && g_host != 0 && from.sin_addr.s_addr != g_host)) {
            ++g_rx_drops;
            continue;
        }
        if (g_host == 0xFFFFFFFFu || g_host == 0) { /* learn the relay's address from its first datagram */
            g_host = from.sin_addr.s_addr;
            memcpy(g_peer, &g_host, 4);
            logf_("dcql: peer %u.%u.%u.%u", g_peer[0], g_peer[1], g_peer[2], g_peer[3]);
        }
        if (!ring_put(&g_rx, g_pkt, (unsigned) n)) ++g_rx_drops;
    }
    if ((n = ring_get(&g_tx, g_pkt, sizeof(g_pkt))) >= 0) {
        struct sockaddr_in to;
        memset(&to, 0, sizeof(to));
        to.sin_family = AF_INET;
        to.sin_port = htons(g_port);
        to.sin_addr.s_addr = g_host;
        const int sent = sendto(g_sock, g_pkt, n, 0, (struct sockaddr*) &to, sizeof(to));
        if (sent == n && !g_tx_fault && !g_retiring && !g_stop) g_tx_bytes += n;
        else ++g_tx_drops;
    }
}

static void* ppp_trampoline(void* arg) {
    g_ppp_thd = thd_get_current();
    g_ppp_tid = thd_get_id(g_ppp_thd);
    void* r = g_ppp_fn(arg);
    g_ppp_thd = NULL;
    g_ppp_running = 0;
    return r;
}

/* ---- libppp redirections (dcql.mk compiles libppp with -Dthd_create=dcql_ppp_thd_create etc.) */
kthread_t* dcql_ppp_thd_create(bool detach, void* (*routine)(void*), void* param) {
    (void) detach; /* libppp never joins it */
    if (thread_busy(g_ppp_tid) || g_ppp_running) return NULL; /* one PPP thread: one static stack */
    kthread_attr_t a;
    memset(&a, 0, sizeof(a));
    a.create_detached = true;
    a.stack_size = sizeof(g_ppp_stack);
    a.stack_ptr = g_ppp_stack;
    a.prio = thd_get_prio(thd_get_current());
    a.label = "dcql-ppp";
    a.disable_tls = true;
    g_ppp_fn = routine;
    g_ppp_running = 1;
    kthread_t* t = thd_create_ex(&a, ppp_trampoline, param);
    if (!t) g_ppp_running = 0;
    return t;
}
static bool on_ppp_thread_retiring(void) {
    return g_ppp_thd && thd_get_current() == g_ppp_thd && (g_stop || g_retiring || g_tx_fault);
}
void dcql_ppp_thd_pass(void) {
    /* libppp calls this with its mutex released. Entering DEAD also wakes ppp_connect. */
    if (on_ppp_thread_retiring()) {
        if (g_tx_fault && !g_stop && !g_retiring) g_state = DCQL_DROPPED;
        _ppp_enter_phase(PPP_PHASE_DEAD);
        thd_sleep(4);
        return;
    }
    if (g_state == DCQL_UP && g_sock >= 0 && g_ppp_thd && thd_get_current() == g_ppp_thd) pump();
    if (on_ppp_thread_retiring()) {
        if (g_tx_fault && !g_stop && !g_retiring) g_state = DCQL_DROPPED;
        _ppp_enter_phase(PPP_PHASE_DEAD);
    }
    thd_sleep(4);
}
int dcql_ppp_modem_write(unsigned char* data, int size) {
    /* modem_shutdown does not clear CONNECTED on every KOS; never write once hang-up has started. */
    if (g_stop || g_retiring || g_tx_fault) return size;
    if (!modem_is_connected()) return size; /* dropped line: discard (libppp would spin forever) */
    const int n = modem_write_data(data, size);
    if (n <= 0) {
        const uint64_t now = timer_ms_gettime64();
        if (!g_write_waiting) { g_write_waiting = true; g_write_since = now; }
        else if (now - g_write_since >= kWriteNoProgressMs) {
            g_tx_fault = true;
            ++g_tx_stalls;
            g_err = -14;
            return size; /* discard; thd_pass enters DEAD */
        }
        thd_sleep(2);
        return 0;
    }
    g_write_waiting = false;
    return n;
}
int dcql_ppp_modem_read(unsigned char* data, int size) { return modem_read_data(data, size); }

/* ---- the modem driver's chain buffers from BSS (-Wl,--wrap=createChainBuffer,--wrap=destroyChainBuffer) */
typedef struct { int length; int start, end; unsigned char flags; unsigned char* data; } dcql_chain_buffer;
static dcql_chain_buffer g_cb[2];
static unsigned char g_cb_data[2][1025] __attribute__((aligned(4)));
static bool g_cb_used[2];
dcql_chain_buffer* __real_createChainBuffer(int length);
void __real_destroyChainBuffer(dcql_chain_buffer* b);
dcql_chain_buffer* __wrap_createChainBuffer(int length) {
    for (int i = 0; i < 2; ++i)
        if (!g_cb_used[i] && length + 1 <= (int) sizeof(g_cb_data[i])) {
            g_cb_used[i] = true;
            memset(&g_cb[i], 0, sizeof(g_cb[i]));
            g_cb[i].length = length + 1; /* chainbuf.c keeps one spare byte */
            g_cb[i].data = g_cb_data[i];
            return &g_cb[i];
        }
    return __real_createChainBuffer(length);
}
void __wrap_destroyChainBuffer(dcql_chain_buffer* b) {
    for (int i = 0; i < 2; ++i)
        if (b == &g_cb[i]) { g_cb_used[i] = false; g_cb[i].data = NULL; return; }
    __real_destroyChainBuffer(b);
}

/* ---- the modem's timeout worker on a BSS stack (-Wl,--wrap=thd_worker_create_ex); other callers unchanged */
static unsigned char g_timer_stack[4096] __attribute__((aligned(32)));
static kthread_t* volatile g_timer_thd;
kthread_worker_t* __real_thd_worker_create_ex(const kthread_attr_t* attr, void (*routine)(void*), void* data);
kthread_worker_t* __wrap_thd_worker_create_ex(const kthread_attr_t* attr, void (*routine)(void*), void* data) {
    if (attr || !g_dial_thd || thd_get_current() != g_dial_thd || g_timer_thd)
        return __real_thd_worker_create_ex(attr, routine, data);
    kthread_attr_t a;
    memset(&a, 0, sizeof(a));
    a.stack_size = sizeof(g_timer_stack);
    a.stack_ptr = g_timer_stack;
    a.prio = PRIO_DEFAULT;
    a.label = "dcql-timer";
    a.disable_tls = true;
    kthread_worker_t* w = __real_thd_worker_create_ex(&a, routine, data);
    if (w) g_timer_thd = thd_worker_get_thread(w);
    return w;
}
void modemIntShutdown(void); /* kernel/arch/dreamcast/hardware/modem/mintr.c */
static void timer_down(void) {
    /* modem_shutdown leaves the IRQ handler and the oneshot timer; every redial would leak a worker thread. */
    if (!g_timer_thd) return;
    modemIntShutdown();
    g_timer_thd = NULL;
}

/* ---- dial / hang up (dial thread only) */
static bool hang_up(void) {
    g_retiring = true;
    const int s = g_sock;
    g_sock = -1;          /* the pump stops */
    ring_clear(&g_tx);
    modem_shutdown();     /* the line drops: a blocked modem write returns */
    if (s >= 0) close(s);
    if (g_ppp_init) _ppp_enter_phase(PPP_PHASE_DEAD);
    for (int i = 0; i < 400 && (g_ppp_running || thread_busy(g_ppp_tid)); ++i) thd_sleep(8);
    if (g_ppp_running || thread_busy(g_ppp_tid)) { g_err = -31; return false; } /* retried by the next start */
    if (g_ppp_init) {
        ppp_set_login(NULL, NULL); /* ppp_shutdown leaves these allocated */
        ppp_shutdown();
        g_ppp_init = false;
    }
    timer_down();
    ring_clear(&g_rx);
    return true;
}

static bool dial_once(void) {
    g_retiring = false;
    g_tx_fault = false;
    g_write_waiting = false;
    g_host = g_configured_host; /* a new call learns the peer anew */
    memcpy(g_peer, &g_host, 4);
    g_state = DCQL_DIALLING;
    if (!g_ppp_init) {
        if (ppp_init() < 0) { g_err = -20; return false; }
        g_ppp_init = true;
    }
    int rate = 0;
    const int r = ppp_modem_init(g_number, 1, &rate); /* blind dial: a DreamPi line has no dial tone */
    if (r < 0) { g_err = r; logf_("dcql: dial failed %d", r); return false; }
    if (g_stop) return false;
    g_rate = (unsigned) rate;
    g_state = DCQL_PPP;
    logf_("dcql: modem %u bps, PPP", g_rate);
    if (ppp_set_login(g_user, g_pass) < 0) { g_err = -15; return false; }
    if (ppp_connect() < 0) { g_err = -10; logf_("dcql: PPP failed"); return false; }
    if (!g_net_ready) {
        fs_socket_init();
        net_udp_init();
        g_net_ready = true;
    }
    if (net_default_dev) memcpy(g_ip, net_default_dev->ip_addr, 4);
    const int s = socket(AF_INET, SOCK_DGRAM, 0);
    if (s < 0) { g_err = -11; return false; }
    struct sockaddr_in me;
    memset(&me, 0, sizeof(me));
    me.sin_family = AF_INET;
    me.sin_port = htons(g_lport);
    me.sin_addr.s_addr = INADDR_ANY;
    if (bind(s, (struct sockaddr*) &me, sizeof(me)) < 0) { close(s); g_err = -12; return false; }
    if (fcntl(s, F_SETFL, O_NONBLOCK) < 0) { close(s); g_err = -13; return false; }
    ring_clear(&g_rx); /* no command from an earlier call may run */
    ring_clear(&g_tx);
    g_sock = s;
    logf_("dcql: up ip=%u.%u.%u.%u", g_ip[0], g_ip[1], g_ip[2], g_ip[3]);
    return true;
}

/* arg 0 = dial (3 tries), 1 = hang up, 2 = hang up then dial */
static void* dial_main(void* arg) {
    g_dial_thd = thd_get_current();
    g_dial_tid = thd_get_id(g_dial_thd);
    const intptr_t mode = (intptr_t) arg;
    if (mode) {
        if (!hang_up()) { g_state = DCQL_FAILED; goto out; }
        g_state = DCQL_OFF;
        logf_("dcql: hung up");
    }
    if (mode != 1 && !g_stop) {
        bool up = false;
        for (int a = 1; a <= 3 && !g_stop && !up; ++a) {
            g_attempt = a;
            up = dial_once();
            if (!up) {
                if (!hang_up()) { g_state = DCQL_FAILED; goto out; }
                for (int i = 0; i < 40 && !g_stop && a < 3; ++i) thd_sleep(100); /* 4 s between tries */
            }
        }
        if (up && g_stop) {
            if (!hang_up()) { g_state = DCQL_FAILED; goto out; }
            up = false;
        }
        g_state = up ? DCQL_UP : g_stop ? DCQL_OFF : DCQL_FAILED;
    }
out:
    g_dial_thd = NULL;
    g_dial_running = 0;
    return NULL;
}

static bool spawn_dial(int mode) {
    if (thread_busy(g_dial_tid) || g_dial_running) return false;
    kthread_attr_t a;
    memset(&a, 0, sizeof(a));
    a.create_detached = true;
    a.stack_size = sizeof(g_dial_stack);
    a.stack_ptr = g_dial_stack;
    a.prio = thd_get_prio(thd_get_current());
    a.label = "dcql-dial";
    a.disable_tls = true;
    g_dial_running = 1;
    if (!thd_create_ex(&a, dial_main, (void*) (intptr_t) mode)) { g_dial_running = 0; return false; }
    return true;
}

static unsigned parse_ip(const char* s) {
    unsigned a[4];
    if (sscanf(s, "%u.%u.%u.%u", &a[0], &a[1], &a[2], &a[3]) != 4) return 0xFFFFFFFFu;
    unsigned char b[4] = {(unsigned char) a[0], (unsigned char) a[1], (unsigned char) a[2], (unsigned char) a[3]};
    unsigned v;
    memcpy(&v, b, 4);
    return v;
}
static void copy_str(char* d, size_t n, const char* s) {
    if (s && s[0]) { strncpy(d, s, n - 1); d[n - 1] = 0; }
}

/* ---- public API */
void dcql_config(const dcql_config_t* c) {
    if (!c) return;
    copy_str(g_number, sizeof(g_number), c->number);
    copy_str(g_user, sizeof(g_user), c->user);
    copy_str(g_pass, sizeof(g_pass), c->pass);
    g_configured_host = (!c->host || !c->host[0] || !strcmp(c->host, "peer")) ? 0xFFFFFFFFu : parse_ip(c->host);
    g_host = g_configured_host;
    memcpy(g_peer, &g_host, 4);
    if (c->port) g_port = c->port;
    if (c->lport) g_lport = c->lport;
    g_bulk_ok = c->bulk_ok;
    g_logfn = c->log;
}
void dcql_set_command(dcql_command_fn fn, void* user) { g_cmd = fn; g_cmd_user = user; }

int dcql_start(void) {
    if (thread_busy(g_dial_tid) || g_dial_running || g_state == DCQL_UP) return 0;
    const int mode = (g_state == DCQL_DROPPED || g_state == DCQL_FAILED || g_ppp_running || thread_busy(g_ppp_tid) ||
                      g_sock >= 0) ? 2 : 0;
    g_stop = 0; g_err = 0; g_attempt = 0;
    g_state = mode ? DCQL_STOPPING : DCQL_DIALLING;
    ring_clear(&g_rx);
    if (!spawn_dial(mode)) { g_state = DCQL_FAILED; g_err = -30; return -1; }
    logf_("dcql: start number=%s port=%u lport=%u", g_number, (unsigned) g_port, (unsigned) g_lport);
    return 0;
}
void dcql_stop(void) {
    g_stop = 1; /* a dial in progress stops after its current step */
    if (g_dial_running) { g_state = DCQL_STOPPING; return; }
    if (g_state == DCQL_UP || g_state == DCQL_DROPPED || g_ppp_running || g_sock >= 0) {
        g_state = DCQL_STOPPING;
        if (!spawn_dial(1)) { g_state = DCQL_FAILED; g_err = -30; }
        return;
    }
    g_state = DCQL_OFF;
}
dcql_state_t dcql_state(void) { return (dcql_state_t) g_state; }
void dcql_state_text(char* out, size_t n) {
    switch (g_state) {
    case DCQL_OFF: snprintf(out, n, "OFF"); break;
    case DCQL_DIALLING: snprintf(out, n, "DIALLING %d/3", g_attempt); break;
    case DCQL_PPP: snprintf(out, n, "PPP %u BPS %d/3", g_rate, g_attempt); break;
    case DCQL_UP:
        snprintf(out, n, "UP %u.%u.%u.%u TO %u.%u.%u.%u", g_ip[0], g_ip[1], g_ip[2], g_ip[3], g_peer[0], g_peer[1],
                 g_peer[2], g_peer[3]);
        break;
    case DCQL_FAILED: snprintf(out, n, "FAILED (%d)", g_err); break;
    case DCQL_DROPPED: snprintf(out, n, "LINE DROPPED"); break;
    default: snprintf(out, n, "HANGING UP"); break;
    }
}
void dcql_counters(dcql_counters_t* c) {
    c->tx_bytes = g_tx_bytes; c->rx_bytes = g_rx_bytes; c->tx_drops = g_tx_drops; c->bulk_skips = g_bulk_skips;
    c->rx_drops = g_rx_drops; c->tx_stalls = g_tx_stalls; c->queued = ring_used(&g_tx); c->rate = g_rate;
    c->attempt = g_attempt; c->err = g_err;
}

int dcql_send_raw(const void* p, size_t n) {
    if (g_state != DCQL_UP) return 0;
    if (n > DCQL_DATAGRAM_MAX || !ring_put(&g_tx, p, (unsigned) n)) { ++g_tx_drops; return 0; }
    return 1;
}
/* Bulk rows (T / L) are admitted only while the backlog is short and bulk_ok() agrees, so a slow line never grows
 * the backlog without bound; answers and marks keep the rest of the ring. */
static bool bulk_admit(unsigned n) {
    if (g_state != DCQL_UP) return false;
    if (ring_used(&g_tx) + n + 2 * 8 > kBulkCap || (g_bulk_ok && !g_bulk_ok())) { ++g_bulk_skips; return false; }
    return true;
}
/* kind 'T': "T seq ms p/n\n", kind 'L': "L seq p/n\n"; parts end at a newline where one exists. */
static int send_parts(char kind, const char* text) {
    const size_t len = strlen(text);
    size_t cuts[16];
    int parts = 0;
    for (size_t off = 0; parts < 16;) {
        size_t n = len - off;
        if (n > DCQL_PART_MAX) {
            n = DCQL_PART_MAX;
            for (size_t k = DCQL_PART_MAX; k > DCQL_PART_MAX / 2; --k)
                if (text[off + k - 1] == '\n') { n = k; break; }
        }
        off += n;
        cuts[parts++] = off;
        if (off >= len) break;
    }
    if (!bulk_admit((unsigned) (len + parts * 32))) return 0;
    const unsigned seq = kind == 'T' ? ++g_tseq : ++g_lseq;
    const unsigned ms = (unsigned) (timer_ms_gettime64() & 0xFFFFFFFFu);
    char b[DCQL_PART_MAX + 48];
    size_t from = 0;
    for (int p = 0; p < parts; ++p) {
        const int h = kind == 'T' ? snprintf(b, sizeof(b), "T %u %u %d/%d\n", seq, ms, p + 1, parts)
                                  : snprintf(b, sizeof(b), "L %u %d/%d\n", seq, p + 1, parts);
        const size_t n = cuts[p] - from;
        memcpy(b + h, text + from, n);
        from = cuts[p];
        if (!dcql_send_raw(b, h + n)) return 0;
    }
    return 1;
}
int dcql_telemetry(const char* body) { return body ? send_parts('T', body) : 0; }
int dcql_log(const char* text) { return text ? send_parts('L', text) : 0; }
int dcql_answer(const char* id, int ok, const char* fmt, ...) {
    char b[DCQL_DATAGRAM_MAX + 1];
    int k = snprintf(b, sizeof(b), "A %s %s ", id ? id : "-", ok ? "OK" : "ERR");
    va_list ap;
    va_start(ap, fmt);
    const int m = vsnprintf(b + k, sizeof(b) - k, fmt, ap);
    va_end(ap);
    k += m;
    if (k > DCQL_DATAGRAM_MAX) k = DCQL_DATAGRAM_MAX;
    return dcql_send_raw(b, (size_t) k);
}
int dcql_mark(const char* label) {
    char b[160];
    const int k = snprintf(b, sizeof(b), "M %u %s", (unsigned) (timer_ms_gettime64() & 0xFFFFFFFFu), label);
    const int ok = dcql_send_raw(b, (size_t) (k < (int) sizeof(b) ? k : (int) sizeof(b) - 1));
    char l[160];
    snprintf(l, sizeof(l), "dcql-mark: %s\n", label);
    logf_("dcql-mark: %s", label);
    /* The L echo goes through the ring directly: marks must not be skipped by the bulk cap. */
    char e[200];
    const int h = snprintf(e, sizeof(e), "L %u 1/1\n%s", ++g_lseq, l);
    dcql_send_raw(e, (size_t) (h < (int) sizeof(e) ? h : (int) sizeof(e) - 1));
    return ok;
}

void dcql_poll(void) {
    char b[DCQL_DATAGRAM_MAX + 1];
    for (int guard = 0; guard < 8; ++guard) {
        const int n = ring_get(&g_rx, b, sizeof(b) - 1);
        if (n == -1) break;
        if (n < 0) { ++g_rx_drops; continue; }
        b[n] = 0;
        /* "<id> <VERB> [args]" */
        char* id = b;
        char* verb = strchr(b, ' ');
        if (!verb) continue;
        *verb++ = 0;
        char* args = strchr(verb, ' ');
        if (args) *args++ = 0; else args = verb + strlen(verb);
        for (char* p = verb; *p; ++p) *p = (char) toupper((unsigned char) *p);
        if (!strcmp(verb, "HELLO")) continue; /* the relay's greeting: it teaches us its address */
        if (!strcmp(verb, "PING")) { dcql_answer(id, 1, "PONG %s", args); continue; }
        if (!strcmp(verb, "MARK")) { dcql_mark(args); dcql_answer(id, 1, "MARK %s", args); continue; }
        if (!strcmp(verb, "STATUS")) {
            dcql_counters_t c;
            dcql_counters(&c);
            dcql_answer(id, 1, "tx=%u rx=%u drops=%u skips=%u rxdrop=%u stall=%u queued=%u rate=%u", c.tx_bytes,
                        c.rx_bytes, c.tx_drops, c.bulk_skips, c.rx_drops, c.tx_stalls, c.queued, c.rate);
            continue;
        }
        if (!g_cmd || !g_cmd(id, verb, args, g_cmd_user)) dcql_answer(id, 0, "unknown %s", verb);
    }
}
