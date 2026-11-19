/* link.c: the console loop loader's modem link (lane eng-loop, 2026-11-19).

   A copy of the QA link's console transport (port/dreamcast/game/qa_link.cpp, lanes qalink27 / link28 / qalink26 /
   build28; console-proven with the DreamPi), in C, with its review28 and fix26 paths always on and the game's KOS heap
   squeeze dropped. The pieces, as there:
    - KOS's libppp sources compiled into the loader (Makefile) with four names redirected here: thd_create (the PPP
      thread on a static stack), thd_pass (a 4 ms sleep that also moves the datagrams on the PPP thread), modem write
      (cannot spin on a dropped line; a stall of 2 s is a fault) and modem read (counted); sem_wait_timed bounds
      ppp_connect's wait (45 s, or a lost line).
    - the modem driver's chain buffers and its timeout worker's stack from BSS (--wrap), so every redial is clean.
    - the KOS network stack without net_init(): fs_socket_init() + net_udp_init(). No IP fragment reassembly: the PC
      side never sends a datagram larger than 1200 bytes.
    - the main thread only copies into and out of two rings; the PPP thread is the only network thread.
   Differences: rings of 64 KiB in and 16 KiB out (data flows down now), port 52060, and a redial that keeps the
   loader's state (the caller owns the retry policy). */
#include <kos.h>
#include <kos/thread.h>
#include <kos/worker_thread.h>
#include <kos/net.h>
#include <kos/fs_socket.h>
#include <kos/sem.h>
#include <kos/irq.h>
#include <arch/timer.h>
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
#include "link.h"

int _ppp_enter_phase(int phase);   /* libppp ppp_internal.h (compiled in) */
int net_udp_init(void);            /* kernel/net/net_udp.c */
void loader_log(const char *fmt, ...);

#define PPP_WAIT_MS 45000
#define DGRAM 1200
#define WRITE_NO_PROGRESS_MS 2000

static volatile int g_state = LINK_OFF, g_attempt, g_err, g_stop;
static volatile unsigned g_rate, g_tx_bytes, g_rx_bytes, g_tx_drops, g_rx_drops, g_modem_tx, g_modem_rx, g_tx_stalls;
static unsigned char g_ip[4], g_peer[4];
static char g_number[24] = "1111111";
static unsigned g_host = 0xFFFFFFFFu, g_configured_host = 0xFFFFFFFFu;   /* network order; all-ones = learn it */
static unsigned short g_port = 52060, g_lport = 52060;
static volatile int g_sock = -1;
static int g_net_ready, g_ppp_init;
static volatile int g_dial_running, g_ppp_running;
static kthread_t *volatile g_ppp_thd;
static volatile tid_t g_ppp_tid, g_dial_tid;
static volatile int g_retiring, g_tx_fault, g_abort;
static volatile int g_why;
static int g_write_waiting;
static uint64_t g_write_since;
static unsigned char g_dial_stack[8192] __attribute__((aligned(32)));
static unsigned char g_ppp_stack[8192] __attribute__((aligned(32)));
static void *(*g_ppp_fn)(void *);

static int stack_busy(tid_t id) {
    if (!id) return 0;
    const irq_mask_t irq = irq_disable();
    const kthread_t *t = thd_by_tid(id);
    const int busy = t && t->state != STATE_ZOMBIE && t->state != STATE_FINISHED;
    irq_restore(irq);
    return busy;
}

/* single-producer single-consumer rings of datagrams: [u16 length][bytes] */
typedef struct { unsigned char *buf; unsigned size; volatile unsigned head, tail; } ring_t;
static unsigned char g_rx_mem[65536], g_tx_mem[16384];
static ring_t g_rx = {g_rx_mem, sizeof(g_rx_mem), 0, 0}, g_tx = {g_tx_mem, sizeof(g_tx_mem), 0, 0};
static unsigned ring_used(const ring_t *r) { return r->head - r->tail; }
static int ring_put(ring_t *r, const void *p, unsigned n) {
    if (!p || !n || n > DGRAM || ring_used(r) + n + 2 > r->size) return 0;
    unsigned h = r->head;
    r->buf[h++ % r->size] = (unsigned char)n;
    r->buf[h++ % r->size] = (unsigned char)(n >> 8);
    for (unsigned i = 0; i < n; ++i) r->buf[h++ % r->size] = ((const unsigned char *)p)[i];
    __asm__ __volatile__("" ::: "memory");
    r->head = h;
    return 1;
}
static int ring_get(ring_t *r, void *p, unsigned max) {
    if (r->head == r->tail) return -1;
    unsigned t = r->tail;
    unsigned n = r->buf[t++ % r->size];
    n |= (unsigned)r->buf[t++ % r->size] << 8;
    if (n > max || !p) { __asm__ __volatile__("" ::: "memory"); r->tail = t + n; return -2; }
    for (unsigned i = 0; i < n; ++i, ++t) ((unsigned char *)p)[i] = r->buf[t % r->size];
    __asm__ __volatile__("" ::: "memory");
    r->tail = t;
    return (int)n;
}
static void ring_clear(ring_t *r) { r->tail = r->head; }
static unsigned char g_pkt[1408];

/* the PPP thread, link up: every received datagram in, then at most ONE queued datagram out (link28: a modem write
   waits while the 1 KiB tx buffer drains; libppp must get back to reading the line between datagrams) */
static void pump(void) {
    if (!modem_is_connected()) { g_state = LINK_DROPPED; return; }
    int n;
    for (;;) {
        struct sockaddr_in from;
        socklen_t fl = sizeof(from);
        n = recvfrom(g_sock, g_pkt, sizeof(g_pkt) - 1, 0, (struct sockaddr *)&from, &fl);
        if (n == 0) { ++g_rx_drops; continue; }
        if (n < 0) break;
        g_rx_bytes += n;
        if (n > DGRAM || fl < sizeof(from) || from.sin_family != AF_INET || from.sin_port != htons(g_port) ||
            (g_host != 0xFFFFFFFFu && g_host != 0 && from.sin_addr.s_addr != g_host)) {
            ++g_rx_drops;
            continue;
        }
        if (g_host == 0xFFFFFFFFu || g_host == 0) {   /* learn the Pi's address from its first datagram */
            g_host = from.sin_addr.s_addr;
            memcpy(g_peer, &from.sin_addr.s_addr, 4);
        }
        if (!ring_put(&g_rx, g_pkt, (unsigned)n)) ++g_rx_drops;
    }
    if ((n = ring_get(&g_tx, g_pkt, sizeof(g_pkt))) > 0) {
        struct sockaddr_in to;
        memset(&to, 0, sizeof(to));
        to.sin_family = AF_INET;
        to.sin_port = htons(g_port);
        to.sin_addr.s_addr = g_host;
        const int sent = sendto(g_sock, g_pkt, n, 0, (struct sockaddr *)&to, sizeof(to));
        if (sent == n && !g_tx_fault && !g_retiring && !g_stop) g_tx_bytes += n;
        else ++g_tx_drops;
    }
}

static void *ppp_trampoline(void *arg) {
    g_ppp_thd = thd_get_current();
    g_ppp_tid = thd_get_id(g_ppp_thd);
    void *r = g_ppp_fn(arg);
    g_ppp_thd = NULL;
    g_ppp_running = 0;
    return r;
}

/* ---------------------------------------------------------------- libppp redirections (Makefile -D names) */
kthread_t *loader_link_thd_create(bool detach, void *(*routine)(void *), void *param) {
    (void)detach;
    if (stack_busy(g_ppp_tid) || g_ppp_running) return NULL;
    kthread_attr_t a;
    memset(&a, 0, sizeof(a));
    a.create_detached = true;
    a.stack_size = sizeof(g_ppp_stack);
    a.stack_ptr = g_ppp_stack;
    a.prio = thd_get_prio(thd_get_current());
    a.label = "loader-ppp";
    a.disable_tls = true;
    g_ppp_fn = routine;
    g_ppp_running = 1;
    kthread_t *t = thd_create_ex(&a, ppp_trampoline, param);
    if (!t) g_ppp_running = 0;
    return t;
}
void loader_link_thd_pass(void) {
    const int on_ppp = g_ppp_thd && thd_get_current() == g_ppp_thd;
    if (on_ppp && (g_stop || g_retiring || g_tx_fault)) {
        if (g_tx_fault && !g_stop && !g_retiring) g_state = LINK_DROPPED;
        _ppp_enter_phase(PPP_PHASE_DEAD);
        thd_sleep(4);
        return;
    }
    if (g_state == LINK_UP && g_sock >= 0 && on_ppp) pump();
    thd_sleep(4);
}
int loader_link_sem_wait_timed(semaphore_t *s, unsigned int timeout) {
    if (timeout) return sem_wait_timed(s, timeout);
    const uint64_t t0 = timer_ms_gettime64();
    for (;;) {
        if (sem_wait_timed(s, 250) == 0) return 0;
        const unsigned ms = (unsigned)(timer_ms_gettime64() - t0);
        const int lost = !modem_is_connected();
        if (g_stop || lost || ms >= PPP_WAIT_MS) {
            g_why = g_stop ? 0 : lost ? -16 : -17;
            loader_log("link: PPP %s after %u ms (modem tx %u rx %u)", g_stop ? "stopped" : lost ? "line lost" : "timed out",
                       ms, (unsigned)g_modem_tx, (unsigned)g_modem_rx);
            g_abort = 1;
            _ppp_enter_phase(PPP_PHASE_DEAD);
            return sem_wait_timed(s, 0);
        }
    }
}
int loader_link_modem_write(unsigned char *data, int size) {
    if (g_stop || g_retiring || g_tx_fault || g_abort) return size;
    if (!modem_is_connected()) return size;   /* dropped line: discard (libppp would spin for ever) */
    const int n = modem_write_data(data, size);
    if (n <= 0) {
        const uint64_t now = timer_ms_gettime64();
        if (!g_write_waiting) { g_write_waiting = 1; g_write_since = now; }
        else if (now - g_write_since >= WRITE_NO_PROGRESS_MS) {
            g_tx_fault = 1;
            ++g_tx_stalls;
            g_err = -14;
            return size;
        }
        thd_sleep(2);
        return 0;
    }
    g_write_waiting = 0;
    g_modem_tx += (unsigned)n;
    return n;
}
int loader_link_modem_read(unsigned char *data, int size) {
    const int n = modem_read_data(data, size);
    if (n > 0) g_modem_rx += (unsigned)n;
    return n;
}

/* ---------------------------------------------------------------- modem chain buffers from BSS (--wrap) */
typedef struct { int length; int start, end; unsigned char flags; unsigned char *data; } chain_buffer_t;
static chain_buffer_t g_cb[2];
static unsigned char g_cb_data[2][1025] __attribute__((aligned(4)));
static int g_cb_used[2];
chain_buffer_t *__real_createChainBuffer(int length);
void __real_destroyChainBuffer(chain_buffer_t *b);
chain_buffer_t *__wrap_createChainBuffer(int length) {
    for (int i = 0; i < 2; ++i)
        if (!g_cb_used[i] && length + 1 <= (int)sizeof(g_cb_data[i])) {
            g_cb_used[i] = 1;
            memset(&g_cb[i], 0, sizeof(g_cb[i]));
            g_cb[i].length = length + 1;
            g_cb[i].data = g_cb_data[i];
            return &g_cb[i];
        }
    return __real_createChainBuffer(length);
}
void __wrap_destroyChainBuffer(chain_buffer_t *b) {
    for (int i = 0; i < 2; ++i)
        if (b == &g_cb[i]) { g_cb_used[i] = 0; g_cb[i].data = NULL; return; }
    __real_destroyChainBuffer(b);
}
/* the modem's timeout worker: created by the dial thread on a static stack, torn down after each hang-up */
static unsigned char g_timer_stack[4096] __attribute__((aligned(32)));
static kthread_t *volatile g_dial_thd;
static kthread_t *volatile g_timer_thd;
kthread_worker_t *__real_thd_worker_create_ex(const kthread_attr_t *attr, void (*routine)(void *), void *data);
kthread_worker_t *__wrap_thd_worker_create_ex(const kthread_attr_t *attr, void (*routine)(void *), void *data) {
    if (attr || !g_dial_thd || thd_get_current() != g_dial_thd || g_timer_thd)
        return __real_thd_worker_create_ex(attr, routine, data);
    kthread_attr_t a;
    memset(&a, 0, sizeof(a));
    a.stack_size = sizeof(g_timer_stack);
    a.stack_ptr = g_timer_stack;
    a.prio = PRIO_DEFAULT;
    a.label = "loader-modem-timer";
    a.disable_tls = true;
    kthread_worker_t *w = __real_thd_worker_create_ex(&a, routine, data);
    if (w) g_timer_thd = thd_worker_get_thread(w);
    return w;
}
void modemIntShutdown(void);   /* kernel/arch/dreamcast/hardware/modem/mintr.c */
static void timer_down(void) {
    if (!g_timer_thd) return;
    modemIntShutdown();
    g_timer_thd = NULL;
}

/* ---------------------------------------------------------------- dial / hang up (the dial thread) */
static int hang_up(void) {
    g_retiring = 1;
    const int s = g_sock;
    g_sock = -1;
    ring_clear(&g_tx);
    modem_shutdown();
    if (s >= 0) close(s);
    if (g_ppp_init) _ppp_enter_phase(PPP_PHASE_DEAD);
    for (int i = 0; i < 400 && (g_ppp_running || stack_busy(g_ppp_tid)); ++i) thd_sleep(8);
    if (g_ppp_running || stack_busy(g_ppp_tid)) { g_err = -31; return 0; }
    if (g_ppp_init) { ppp_set_login(NULL, NULL); ppp_shutdown(); g_ppp_init = 0; }
    timer_down();
    ring_clear(&g_rx);
    return 1;
}

static int dial_once(void) {
    g_retiring = 0; g_tx_fault = 0; g_write_waiting = 0; g_abort = 0; g_why = 0;
    g_host = g_configured_host;
    memcpy(g_peer, &g_host, 4);
    g_modem_tx = g_modem_rx = 0;
    g_state = LINK_DIAL;
    if (!g_ppp_init) {
        if (ppp_init() < 0) { g_err = -20; return 0; }
        g_ppp_init = 1;
    }
    int rate = 0;
    const int r = ppp_modem_init(g_number, 1, &rate);   /* blind dial: a DreamPi line has no dial tone */
    if (r < 0) { g_err = r; loader_log("link: dial failed %d", r); return 0; }
    if (g_stop) return 0;
    g_rate = (unsigned)rate;
    g_state = LINK_PPP;
    loader_log("link: modem connected %u bps, PPP", g_rate);
    if (ppp_set_login("dream", "dreamcast") < 0) { g_err = -15; return 0; }   /* DreamPi's pppd asks for PAP */
    if (ppp_connect() < 0 || g_abort) {
        g_err = g_why ? g_why : -10;
        loader_log("link: PPP failed %d (modem tx %u rx %u)", g_err, (unsigned)g_modem_tx, (unsigned)g_modem_rx);
        return 0;
    }
    if (!g_net_ready) { fs_socket_init(); net_udp_init(); g_net_ready = 1; }
    if (net_default_dev) memcpy(g_ip, net_default_dev->ip_addr, 4);
    const int s = socket(AF_INET, SOCK_DGRAM, 0);
    if (s < 0) { g_err = -11; return 0; }
    struct sockaddr_in me;
    memset(&me, 0, sizeof(me));
    me.sin_family = AF_INET;
    me.sin_port = htons(g_lport);
    me.sin_addr.s_addr = INADDR_ANY;
    if (bind(s, (struct sockaddr *)&me, sizeof(me)) < 0) { close(s); g_err = -12; return 0; }
    if (fcntl(s, F_SETFL, O_NONBLOCK) < 0) { close(s); g_err = -13; return 0; }
    ring_clear(&g_rx);
    ring_clear(&g_tx);
    g_sock = s;
    loader_log("link: up %u.%u.%u.%u", g_ip[0], g_ip[1], g_ip[2], g_ip[3]);
    return 1;
}

/* arg 0 = dial (3 tries), 1 = hang up, 2 = hang up then dial */
static void *dial_main(void *arg) {
    g_dial_thd = thd_get_current();
    g_dial_tid = thd_get_id(g_dial_thd);
    const intptr_t mode = (intptr_t)arg;
    if (mode) {
        if (!hang_up()) { g_state = LINK_DROPPED; g_dial_thd = NULL; g_dial_running = 0; return NULL; }
        g_state = LINK_OFF;
    }
    if (mode != 1 && !g_stop) {
        int up = 0;
        for (int a = 1; a <= 3 && !g_stop && !up; ++a) {
            g_attempt = a;
            up = dial_once();
            if (!up) {
                if (!hang_up()) { g_state = LINK_DROPPED; g_dial_thd = NULL; g_dial_running = 0; return NULL; }
                for (int i = 0; i < 40 && !g_stop; ++i) thd_sleep(100);
            }
        }
        if (up && g_stop) {
            if (!hang_up()) { g_state = LINK_DROPPED; g_dial_thd = NULL; g_dial_running = 0; return NULL; }
            up = 0;
        }
        g_state = up ? LINK_UP : g_stop ? LINK_OFF : LINK_FAILED;
    }
    g_dial_thd = NULL;
    g_dial_running = 0;
    return NULL;
}

static int spawn_dial(int mode) {
    if (stack_busy(g_dial_tid) || g_dial_running) return 0;
    kthread_attr_t a;
    memset(&a, 0, sizeof(a));
    a.create_detached = true;
    a.stack_size = sizeof(g_dial_stack);
    a.stack_ptr = g_dial_stack;
    a.prio = thd_get_prio(thd_get_current());
    a.label = "loader-dial";
    a.disable_tls = true;
    g_dial_running = 1;
    if (!thd_create_ex(&a, dial_main, (void *)(intptr_t)mode)) { g_dial_running = 0; return 0; }
    return 1;
}

static unsigned parse_ip(const char *s) {
    unsigned a[4] = {0, 0, 0, 0};
    if (sscanf(s, "%u.%u.%u.%u", &a[0], &a[1], &a[2], &a[3]) != 4) return 0xFFFFFFFFu;
    unsigned char b[4] = {(unsigned char)a[0], (unsigned char)a[1], (unsigned char)a[2], (unsigned char)a[3]};
    unsigned v;
    memcpy(&v, b, 4);
    return v;
}

/* ---------------------------------------------------------------- API (link.h) */
void link_config(const char *number, const char *host, unsigned port, unsigned lport) {
    if (number && number[0]) { strncpy(g_number, number, sizeof(g_number) - 1); g_number[sizeof(g_number) - 1] = 0; }
    if (host && host[0]) g_configured_host = g_host = strcmp(host, "peer") ? parse_ip(host) : 0xFFFFFFFFu;
    if (port && port < 65536) g_port = (unsigned short)port;
    if (lport && lport < 65536) g_lport = (unsigned short)lport;
    memcpy(g_peer, &g_host, 4);
}
int link_start(void) {
    if (stack_busy(g_dial_tid) || g_dial_running || g_state == LINK_UP) return 0;
    const int mode = (g_state == LINK_DROPPED || g_ppp_running || stack_busy(g_ppp_tid) || g_sock >= 0) ? 2 : 0;
    g_stop = 0; g_err = 0; g_attempt = 0;
    g_state = mode ? LINK_STOPPING : LINK_DIAL;
    if (!spawn_dial(mode)) { g_state = LINK_FAILED; g_err = -30; return -1; }
    return 0;
}
void link_stop(void) {
    g_stop = 1;
    if (g_dial_running) { g_state = LINK_STOPPING; return; }
    if (g_state == LINK_UP || g_state == LINK_DROPPED || g_ppp_running || g_sock >= 0) {
        g_state = LINK_STOPPING;
        if (!spawn_dial(1)) { g_state = LINK_FAILED; g_err = -30; }
        return;
    }
    g_state = LINK_OFF;
}
int link_state(void) { return g_state; }
int link_busy(void) { return g_dial_running || g_ppp_running; }
int link_send(const void *p, unsigned n) {
    if (g_state != LINK_UP) return 0;
    if (!ring_put(&g_tx, p, n)) { ++g_tx_drops; return 0; }
    return 1;
}
int link_recv(void *p, unsigned max) {
    const int n = ring_get(&g_rx, p, max);
    if (n == -2) ++g_rx_drops;
    return n;
}
unsigned link_tx_queued(void) { return ring_used(&g_tx); }
unsigned link_console_ip(void) { unsigned v; memcpy(&v, g_ip, 4); return v; }
unsigned link_host(void) { return g_host; }
unsigned link_port(void) { return g_port; }
unsigned link_lport(void) { return g_lport; }
const char *link_number(void) { return g_number; }
void link_text(char *out, unsigned n) {
    switch (g_state) {
    case LINK_OFF: snprintf(out, n, "OFF"); break;
    case LINK_DIAL: snprintf(out, n, "DIALLING %d/3 (%s)", g_attempt, g_number); break;
    case LINK_PPP: snprintf(out, n, "PPP %u BPS %d/3 T%u R%u", g_rate, g_attempt, (unsigned)g_modem_tx, (unsigned)g_modem_rx); break;
    case LINK_UP:
        snprintf(out, n, "UP %u.%u.%u.%u TO %u.%u.%u.%u %u BPS", g_ip[0], g_ip[1], g_ip[2], g_ip[3], g_peer[0], g_peer[1],
                 g_peer[2], g_peer[3], g_rate);
        break;
    case LINK_FAILED: snprintf(out, n, "FAILED %d T%u R%u", g_err, (unsigned)g_modem_tx, (unsigned)g_modem_rx); break;
    case LINK_DROPPED: snprintf(out, n, "LINE DROPPED"); break;
    default: snprintf(out, n, "HANGING UP"); break;
    }
}
void link_counters(unsigned *tx, unsigned *rx, unsigned *txd, unsigned *rxd) {
    *tx = g_tx_bytes; *rx = g_rx_bytes; *txd = g_tx_drops; *rxd = g_rx_drops;
}
