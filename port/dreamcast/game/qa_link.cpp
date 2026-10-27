// qa_link.cpp: the QA remote link's transport (QA_LINK=1 in qalink.mk; QA discs only, never a release image). Lane
// qalink27, 2026-10-27.
//
// The Dreamcast's built-in 56k modem dials a DreamPi (a Raspberry Pi with a USB modem that answers and runs pppd), PPP
// gives the console an IP address, and one UDP socket carries text lines both ways (qa_menu.cpp writes the protocol;
// tools/qalink/qalink_pi.py is the Pi side).
//
// Pieces:
//  - KOS's libppp sources (addons/libppp, the pinned toolchain), compiled into the game by qalink.mk with these names
//    redirected to this file instead of linking libppp.a:
//      thd_create       -> re4dc_qalink_thd_create: the PPP thread runs detached on a static 4 KiB stack (high water 2 KiB measured) (BSS), not a
//                          32 KiB KOS heap stack;
//      thd_pass         -> re4dc_qalink_thd_pass: sleeps 4 ms (libppp's receive loop and the modem connect wait call
//                          thd_pass() in a loop, which would keep a thread always runnable at the game's priority). On
//                          the PPP thread, with the link up, it also moves the datagrams (pump()): the PPP thread is
//                          the only network thread once the link is up;
//      modem_write_data -> re4dc_qalink_modem_write: libppp's modem tx spins until every byte is buffered and never
//                          returns once the line drops; here a dropped line discards the bytes and a full buffer sleeps;
//      modem_read_data  -> re4dc_qalink_modem_read (byte counts; QA_LINK_DEBUG=1 also logs the first bytes in hex).
//  - the modem driver's two 1 KiB chain buffers come from BSS (link --wrap=createChainBuffer / destroyChainBuffer):
//    the KOS heap runs with ~6-10 KiB of headroom under the 48 KiB squeeze gate, and a failed allocation there is an
//    assert in the driver.
//  - the KOS network stack without net_init(): fs_socket_init() + net_udp_init() only. net_init() would start the
//    network work-queue thread (another 32 KiB heap stack) and DHCP, which PPP does not need. Consequence: no IPv4
//    fragment reassembly (the Pi side never sends a datagram larger than 1200 bytes).
//  - a dial thread (detached, static 8 KiB stack): dials (3 tries), negotiates PPP, opens the socket and leaves; on
//    "off" another one hangs up. The game thread only copies into and out of two rings (no network call and no modem
//    wait on the frame path).
#include <kos.h>
#include <kos/thread.h>
#include <kos/worker_thread.h>
#include <kos/net.h>
#include <kos/fs_socket.h>
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

extern "C" {
void re4dc_log(const char* fmt, ...);
int net_udp_init(void);   // kernel/net/net_udp.c (KOS internal; registers UDP with fs_socket)
}

namespace {
enum { S_OFF, S_DIAL, S_PPP, S_UP, S_FAILED, S_DROPPED, S_STOPPING };
volatile int g_state = S_OFF, g_attempt, g_err, g_stop;
volatile unsigned g_rate, g_tx_bytes, g_rx_bytes, g_tx_drops, g_modem_tx, g_modem_rx;
unsigned char g_ip[4], g_peer[4];
char g_number[24] = "1111111";
unsigned g_host = 0xFFFFFFFFu;   // network order; 255.255.255.255 = whoever is at the other end of the PPP link
unsigned short g_port = 52040, g_lport = 52040;   // the Pi's port / this console's port
volatile int g_sock = -1;
bool g_net_ready, g_ppp_init;
volatile int g_dial_running, g_ppp_running;
kthread_t* volatile g_ppp_thd;
unsigned char g_dial_stack[8192] __attribute__((aligned(32)));
unsigned char g_ppp_stack[4096] __attribute__((aligned(32)));
void* (*g_ppp_fn)(void*);

// Single-producer single-consumer rings of datagrams: [u16 length][bytes]. tx: game -> PPP thread; rx: PPP thread -> game.
struct Ring {
    unsigned char buf[4096];
    volatile unsigned head, tail;   // head written by the producer, tail by the consumer (byte counters)
    unsigned used() const { return head - tail; }
    bool put(const void* p, unsigned n) {
        if (n > 1400 || used() + n + 2 > sizeof(buf)) return false;
        unsigned h = head;
        buf[h++ % sizeof(buf)] = (unsigned char) n;
        buf[h++ % sizeof(buf)] = (unsigned char) (n >> 8);
        for (unsigned i = 0; i < n; ++i) buf[h++ % sizeof(buf)] = ((const unsigned char*) p)[i];
        __asm__ __volatile__("" ::: "memory");
        head = h;
        return true;
    }
    int get(void* p, unsigned max) {
        if (head == tail) return -1;
        unsigned t = tail;
        unsigned n = buf[t++ % sizeof(buf)];
        n |= (unsigned) buf[t++ % sizeof(buf)] << 8;
        for (unsigned i = 0; i < n; ++i, ++t)
            if (i < max) ((unsigned char*) p)[i] = buf[t % sizeof(buf)];
        __asm__ __volatile__("" ::: "memory");
        tail = t;
        return (int) (n < max ? n : max);
    }
    void clear() { tail = head; }
};
Ring g_tx, g_rx;
unsigned char g_pkt[1408];   // the PPP thread's datagram buffer

// The PPP thread, link up: queued datagrams out, received ones in. Called between libppp's receive passes, with
// libppp's mutex released (sendto takes it).
void pump() {
    if (!modem_is_connected()) {
        g_state = S_DROPPED;
        re4dc_log("qalink: line dropped\n");
        return;
    }
    int n;
    while ((n = g_tx.get(g_pkt, sizeof(g_pkt))) >= 0) {
        sockaddr_in to;
        memset(&to, 0, sizeof(to));
        to.sin_family = AF_INET;
        to.sin_port = htons(g_port);
        to.sin_addr.s_addr = g_host;
        if (sendto(g_sock, g_pkt, n, 0, (sockaddr*) &to, sizeof(to)) == n) g_tx_bytes = g_tx_bytes + n;
        else g_tx_drops = g_tx_drops + 1;
        if (!modem_is_connected()) return;
    }
    for (;;) {
        sockaddr_in from;
        socklen_t fl = sizeof(from);
        n = recvfrom(g_sock, g_pkt, sizeof(g_pkt) - 1, 0, (sockaddr*) &from, &fl);
        if (n <= 0) break;
        g_rx_bytes = g_rx_bytes + n;
        if (g_host == 0xFFFFFFFFu || g_host == 0) {   // learn the Pi's address from its first datagram
            g_host = from.sin_addr.s_addr;
            memcpy(g_peer, &from.sin_addr.s_addr, 4);
            re4dc_log("qalink: peer %u.%u.%u.%u\n", g_peer[0], g_peer[1], g_peer[2], g_peer[3]);
        }
        g_rx.put(g_pkt, (unsigned) n);
    }
}

void* ppp_trampoline(void* arg) {
    void* r = g_ppp_fn(arg);
    g_ppp_thd = nullptr;
    g_ppp_running = 0;
    return r;
}
}  // namespace

extern "C" {
// ---------------------------------------------------------------- libppp redirections (qalink.mk -D names)
kthread_t* re4dc_qalink_thd_create(bool detach, void* (*routine)(void*), void* param) {
    (void) detach;                         // libppp never joins its thread: detached, so KOS frees it at exit
    if (g_ppp_running) return nullptr;     // one PPP thread at a time (the static stack)
    kthread_attr_t a;
    memset(&a, 0, sizeof(a));
    a.create_detached = true;
    a.stack_size = sizeof(g_ppp_stack);
    a.stack_ptr = g_ppp_stack;
    a.prio = thd_get_prio(thd_get_current());
    a.label = "qalink-ppp";
    a.disable_tls = true;
    g_ppp_fn = routine;
    g_ppp_running = 1;
    kthread_t* t = thd_create_ex(&a, ppp_trampoline, param);
    if (!t) g_ppp_running = 0;
    g_ppp_thd = t;
    return t;
}
void re4dc_qalink_thd_pass(void) {
    if (g_state == S_UP && g_sock >= 0 && g_ppp_thd && thd_get_current() == g_ppp_thd) pump();
    thd_sleep(4);
}
// QA_LINK_DEBUG=1 (qalink.mk): libppp's dbglog lines into the RAM log
void re4dc_qalink_dbglog(int level, const char* fmt, ...) {
    (void) level;
    char b[160];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(b, sizeof(b), fmt, ap);
    va_end(ap);
    re4dc_log("ppp: %s", b);
}
int re4dc_qalink_modem_write(unsigned char* data, int size) {
    if (!modem_is_connected()) return size;   // dropped line: discard (libppp would spin forever)
    const int n = modem_write_data(data, size);
    if (!n) thd_sleep(2);                      // tx buffer full: let the modem drain it
    g_modem_tx = g_modem_tx + (unsigned) n;
#if defined(RE4DC_QA_LINK_DEBUG) && RE4DC_QA_LINK_DEBUG
    for (int i = 0; i < n && g_modem_tx <= 512; i += 24) {
        char h[80];
        int k = 0;
        for (int j = i; j < n && j < i + 24; ++j) k += snprintf(h + k, sizeof(h) - k, "%02x", data[j]);
        re4dc_log("qalink tx: %s\n", h);
    }
#endif
    return n;
}
int re4dc_qalink_modem_read(unsigned char* data, int size) {
    const int n = modem_read_data(data, size);
    if (n > 0) g_modem_rx = g_modem_rx + (unsigned) n;
#if defined(RE4DC_QA_LINK_DEBUG) && RE4DC_QA_LINK_DEBUG
    for (int i = 0; i < n && g_modem_rx <= 512; i += 24) {   // the first bytes of the line, in hex
        char h[80];
        int k = 0;
        for (int j = i; j < n && j < i + 24; ++j) k += snprintf(h + k, sizeof(h) - k, "%02x", data[j]);
        re4dc_log("qalink rx: %s\n", h);
    }
#endif
    return n;
}

// ---------------------------------------------------------------- modem chain buffers from BSS (--wrap, qalink.mk)
// Same layout as kernel/arch/dreamcast/hardware/modem/chainbuf.h (CHAIN_BUFFER).
struct qalink_chain_buffer { int length; int start, end; unsigned char flags; unsigned char* data; };
static qalink_chain_buffer g_cb[2];
static unsigned char g_cb_data[2][1025] __attribute__((aligned(4)));
static bool g_cb_used[2];
qalink_chain_buffer* __real_createChainBuffer(int length);
void __real_destroyChainBuffer(qalink_chain_buffer* b);
qalink_chain_buffer* __wrap_createChainBuffer(int length) {
    for (int i = 0; i < 2; ++i)
        if (!g_cb_used[i] && length + 1 <= (int) sizeof(g_cb_data[i])) {
            g_cb_used[i] = true;
            memset(&g_cb[i], 0, sizeof(g_cb[i]));
            g_cb[i].length = length + 1;   // chainbuf.c keeps one spare byte
            g_cb[i].data = g_cb_data[i];
            return &g_cb[i];
        }
    return __real_createChainBuffer(length);
}
void __wrap_destroyChainBuffer(qalink_chain_buffer* b) {
    for (int i = 0; i < 2; ++i)
        if (b == &g_cb[i]) { g_cb_used[i] = false; g_cb[i].data = nullptr; return; }
    __real_destroyChainBuffer(b);
}

// ---------------------------------------------------------------- the modem's timeout worker on a BSS stack (--wrap)
// modem_init (mintr.c) creates a oneshot timer, whose worker thread KOS would give a 32 KiB stack from the KOS heap
// (measured: a 32 KiB sbrk request during the dial, an "Out of memory" line under the 48 KiB squeeze gate). A worker
// created by the dial thread gets a 4 KiB static stack instead; any other caller is unchanged.
static unsigned char g_timer_stack[4096] __attribute__((aligned(32)));
static kthread_t* volatile g_dial_thd;
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
    a.label = "qalink-timer";
    a.disable_tls = true;
    kthread_worker_t* w = __real_thd_worker_create_ex(&a, routine, data);
    if (w) g_timer_thd = thd_worker_get_thread(w);
    return w;
}
void modemIntShutdown(void);   // kernel/arch/dreamcast/hardware/modem/mintr.c (mintern.h)
// After modem_shutdown(): KOS's modem_shutdown leaves the interrupt handler and the oneshot timer (its worker thread)
// in place and the next modem_init creates another timer, so every redial would leak a thread. Tear them down here.
void re4dc_qalink_timer_down(void) {
    if (!g_timer_thd) return;
    modemIntShutdown();
    g_timer_thd = nullptr;
}
}  // extern "C"

namespace {
void hang_up() {
    if (g_sock >= 0) { const int s = g_sock; g_sock = -1; close(s); }
    if (g_ppp_init) { ppp_shutdown(); g_ppp_init = false; }
    modem_shutdown();
    re4dc_qalink_timer_down();
    for (int i = 0; i < 250 && g_ppp_running; ++i) thd_sleep(8);   // the PPP thread leaves when its phase is dead
}

bool dial_once() {
    g_state = S_DIAL;
    if (!g_ppp_init) {
        if (ppp_init() < 0) { g_err = -20; return false; }
        g_ppp_init = true;
    }
    int rate = 0;
    const int r = ppp_modem_init(g_number, 1, &rate);   // blind dial: a DreamPi line has no exchange dial tone
    if (r < 0) { g_err = r; re4dc_log("qalink: dial failed %d\n", r); return false; }
    g_rate = (unsigned) rate;
    g_state = S_PPP;
    re4dc_log("qalink: modem connected %u bps, PPP\n", g_rate);
    ppp_set_login("dream", "dreamcast");   // DreamPi's pppd runs noauth; PAP is used only if the peer asks for it
    if (ppp_connect() < 0) {
        g_err = -10;
        re4dc_log("qalink: PPP failed (modem tx %u rx %u bytes)\n", (unsigned) g_modem_tx, (unsigned) g_modem_rx);
        return false;
    }
    if (!g_net_ready) {
        fs_socket_init();
        net_udp_init();
        g_net_ready = true;
    }
    if (net_default_dev) memcpy(g_ip, net_default_dev->ip_addr, 4);
    const int s = socket(AF_INET, SOCK_DGRAM, 0);
    if (s < 0) { g_err = -11; return false; }
    sockaddr_in me;
    memset(&me, 0, sizeof(me));
    me.sin_family = AF_INET;
    me.sin_port = htons(g_lport);
    me.sin_addr.s_addr = INADDR_ANY;
    if (bind(s, (sockaddr*) &me, sizeof(me)) < 0) { close(s); g_err = -12; return false; }
    fcntl(s, F_SETFL, O_NONBLOCK);
    g_tx.clear();
    g_sock = s;
    re4dc_log("qalink: up ip=%u.%u.%u.%u\n", g_ip[0], g_ip[1], g_ip[2], g_ip[3]);
    return true;
}

// The dial thread: arg 0 = dial (3 tries), 1 = hang up. Detached; it leaves once the link is up or down.
void* dial_main(void* arg) {
    g_dial_thd = thd_get_current();
    if (arg) {
        hang_up();
        g_state = S_OFF;
        re4dc_log("qalink: hung up\n");
    } else {
        bool up = false;
        for (int a = 1; a <= 3 && !g_stop && !up; ++a) {
            g_attempt = a;
            up = dial_once();
            if (!up) {
                hang_up();
                for (int i = 0; i < 40 && !g_stop; ++i) thd_sleep(100);   // 4 s before the next try
            }
        }
        if (up && g_stop) { hang_up(); up = false; }
        g_state = up ? S_UP : g_stop ? S_OFF : S_FAILED;
    }
    g_dial_thd = nullptr;
    g_dial_running = 0;
    return nullptr;
}

bool spawn_dial(int mode) {
    if (g_dial_running) return false;
    kthread_attr_t a;
    memset(&a, 0, sizeof(a));
    a.create_detached = true;
    a.stack_size = sizeof(g_dial_stack);
    a.stack_ptr = g_dial_stack;
    a.prio = thd_get_prio(thd_get_current());
    a.label = "qalink-dial";
    a.disable_tls = true;
    g_dial_running = 1;
    if (!thd_create_ex(&a, dial_main, (void*) (intptr_t) mode)) { g_dial_running = 0; return false; }
    return true;
}

unsigned parse_ip(const char* s) {
    unsigned a[4] = {0, 0, 0, 0};
    if (sscanf(s, "%u.%u.%u.%u", &a[0], &a[1], &a[2], &a[3]) != 4) return 0xFFFFFFFFu;
    unsigned char b[4] = {(unsigned char) a[0], (unsigned char) a[1], (unsigned char) a[2], (unsigned char) a[3]};
    unsigned v;
    memcpy(&v, b, 4);
    return v;
}
}  // namespace

extern "C" {

// Settings (qa_menu.cpp reads /cd/dc/qa/link.txt): dial number, Pi address ("peer" = learn it), the Pi's UDP port,
// this console's UDP port (Flycast's modem emulation opens the same port on the PC, so a PC test needs it different).
void re4dc_qalink_config(const char* number, const char* host, unsigned port, unsigned lport) {
    if (number && number[0]) { strncpy(g_number, number, sizeof(g_number) - 1); g_number[sizeof(g_number) - 1] = 0; }
    if (host && host[0]) g_host = strcmp(host, "peer") ? parse_ip(host) : 0xFFFFFFFFu;
    if (port && port < 65536) g_port = (unsigned short) port;
    if (lport && lport < 65536) g_lport = (unsigned short) lport;
    memcpy(g_peer, &g_host, 4);
}

// Start (dial thread) / stop (a thread hangs up). Both return at once.
void re4dc_qalink_stop(void);
int re4dc_qalink_start(void) {
    if (g_state == S_DROPPED) { re4dc_qalink_stop(); return 0; }   // a dropped line hangs up first
    if (g_dial_running || g_state == S_UP || g_ppp_running) return 0;   // dialling, up, or still hanging up
    g_stop = 0; g_err = 0; g_attempt = 0; g_state = S_DIAL;
    g_rx.clear();
    if (!spawn_dial(0)) { g_state = S_FAILED; g_err = -30; return -1; }
    re4dc_log("qalink: start number=%s port=%u lport=%u\n", g_number, (unsigned) g_port, (unsigned) g_lport);
    return 0;
}
void re4dc_qalink_stop(void) {
    g_stop = 1;   // a dial in progress stops after its current step
    if (g_dial_running) { g_state = S_STOPPING; return; }
    if (g_state == S_UP || g_state == S_DROPPED || g_ppp_running) { g_state = S_STOPPING; spawn_dial(1); return; }
    g_state = S_OFF;
}

// 1 = the link is up (datagrams move).
int re4dc_qalink_up(void) { return g_state == S_UP; }
// 1 = dialling or up (the menu row's ON).
int re4dc_qalink_wanted(void) { return g_state == S_DIAL || g_state == S_PPP || g_state == S_UP; }

// The state for the QA menu row and the telemetry.
void re4dc_qalink_state_text(char* out, unsigned n) {
    switch (g_state) {
    case S_OFF: snprintf(out, n, "OFF"); break;
    case S_DIAL: snprintf(out, n, "DIALLING %d/3", g_attempt); break;
    case S_PPP: snprintf(out, n, "PPP %u BPS %d/3", g_rate, g_attempt); break;
    case S_UP: snprintf(out, n, "UP %u.%u.%u.%u TO %u.%u.%u.%u", g_ip[0], g_ip[1], g_ip[2], g_ip[3], g_peer[0], g_peer[1],
                        g_peer[2], g_peer[3]); break;
    case S_FAILED: snprintf(out, n, "FAILED (%d) - A: RETRY", g_err); break;
    case S_DROPPED: snprintf(out, n, "LINE DROPPED - A: HANG UP"); break;
    default: snprintf(out, n, "HANGING UP"); break;
    }
}
void re4dc_qalink_counters(unsigned* tx, unsigned* rx, unsigned* drops, unsigned* queued) {
    *tx = g_tx_bytes; *rx = g_rx_bytes; *drops = g_tx_drops; *queued = g_tx.used();
}

// Game thread: queue one datagram (<= 1400 bytes; 0 = ring full, dropped) / take one received datagram.
int re4dc_qalink_send(const void* p, unsigned n) {
    if (g_state != S_UP) return 0;
    if (!g_tx.put(p, n)) { g_tx_drops = g_tx_drops + 1; return 0; }
    return 1;
}
int re4dc_qalink_recv(char* p, unsigned max) {
    const int n = g_rx.get(p, max - 1);
    if (n >= 0) p[n] = 0;
    return n;
}

}  // extern "C"
