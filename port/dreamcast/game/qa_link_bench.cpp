// QA_LINK on a benchmark / arena disc (QA_LINK=1 with BENCHMARK=1 and QA_MENU=0; lane link28, user 2026-10-28: "make it
// link supported as well so that going forward all discs can work that way"). qalink.mk.
//
// A benchmark disc has no QA menu (QA_MENU and BENCHMARK both own the OSInit wrap and the banner), so this file is the
// link's whole game side there: it reads /cd/dc/link.txt (else /cd/dc/qa/link.txt) at the first game tick (same keys as the QA disc: number,
// host, port, lport, auto) and dials on its own when the file says `auto 1` (no menu row to press). Nothing else on the
// disc changes: the transport is qa_link.cpp, unchanged.
// Console -> Pi (the QA protocol's kinds, tools/qalink/README.md):
//   T <seq> <ms> 1/1   once a second: the link row and the benchmark scene number
//   L <seq> <dropped>  new RAM log lines, at most 640 bytes a second (as the QA disc)
//   B <seq> <dropped>  the benchmark's result rows, lossless: every complete RAM log line that starts with "bench: " or
//                      "PACE" (BENCHMARK result / result2 / phases / ta / tail / code rows, PACE windows), packed up to
//                      1000 bytes a datagram, sent as fast as the transmit ring drains; <dropped> counts only bytes the
//                      log ring overwrote before they were sent
//   A <id> OK|ERR      answers: PING / HELLO answer PONG; every QA-menu command answers ERR (no menu on this disc)
// re4dc_qa_link_bench_tick runs on the game thread: each game tick (dbgwarp_bridge.cpp re4dc_warp_poll) and each pass of
// the results screen's wait loop (bench.cpp), where the frame loop stops but the result rows have just been logged.
#include <kos.h>
#include <arch/timer.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <stdint.h>

extern "C" {
void re4dc_log(const char* fmt, ...);
int re4dc_fixture_read(const char* path, char* buffer, unsigned size);
int re4dc_bench_scene_no(void);   // bench.cpp
void re4dc_qalink_config(const char* number, const char* host, unsigned port, unsigned lport);
int re4dc_qalink_start(void);
int re4dc_qalink_up(void);
void re4dc_qalink_state_text(char* out, unsigned n);
void re4dc_qalink_counters(unsigned* tx, unsigned* rx, unsigned* drops, unsigned* queued);
int re4dc_qalink_send(const void* p, unsigned n);
int re4dc_qalink_send_bulk(const void* p, unsigned n);
unsigned re4dc_qalink_bulk_skips(void);
int re4dc_qalink_recv(char* p, unsigned max);
extern volatile unsigned long re4dc_log_head;   // platform/mem.cpp
}
#ifndef RE4DC_LOG_TRIM
#define RE4DC_LOG_TRIM 0
#endif
extern "C" char re4dc_logbuf[0x10000 - RE4DC_LOG_TRIM];

namespace {
struct BenchLink {
    bool cfg_read, auto_start;
    unsigned seq, log_seq, b_seq;
    unsigned long log_sent, b_sent, b_dropped;
    uint64_t next_ms, cost_us, cost_t0;
    unsigned cost_last;
} g_bl;

void read_cfg() {
    g_bl.cfg_read = true;
    char text[512];
    const char* file = "/cd/dc/link.txt";   // a benchmark disc's fixtures sit in /dc/ (mkgdi.sh); a QA tree's in /dc/qa/
    int len = re4dc_fixture_read(file, text, sizeof(text) - 1);
    if (len <= 0) { file = "/cd/dc/qa/link.txt"; len = re4dc_fixture_read(file, text, sizeof(text) - 1); }
    char number[24] = "", host[24] = "";
    unsigned port = 0, lport = 0;
    if (len > 0) {
        text[len] = 0;
        for (char* line = text; line && *line;) {
            char* next = strchr(line, '\n');
            if (next) *next++ = 0;
            char* cr = strchr(line, '\r');
            if (cr) *cr = 0;
            if (!strncmp(line, "number ", 7)) strncpy(number, line + 7, sizeof(number) - 1);
            else if (!strncmp(line, "host ", 5)) strncpy(host, line + 5, sizeof(host) - 1);
            else if (!strncmp(line, "port ", 5)) port = (unsigned) atoi(line + 5);
            else if (!strncmp(line, "lport ", 6)) lport = (unsigned) atoi(line + 6);
            else if (!strncmp(line, "auto ", 5)) g_bl.auto_start = atoi(line + 5) != 0;
            line = next;
        }
    }
    re4dc_qalink_config(number, host, port, lport);
    re4dc_log("qalink: bench config %s number=%s host=%s port=%u lport=%u auto=%d\n", len > 0 ? file : "none",
              number[0] ? number : "default", host[0] ? host : "peer", port, lport, (int) g_bl.auto_start);
    if (g_bl.auto_start) re4dc_qalink_start();
}

void reply(const char* id, bool ok, const char* fmt, ...) __attribute__((format(printf, 3, 4)));
void reply(const char* id, bool ok, const char* fmt, ...) {
    char b[300];
    int k = snprintf(b, sizeof(b), "A %s %s ", id, ok ? "OK" : "ERR");
    va_list ap;
    va_start(ap, fmt);
    const int m = vsnprintf(b + k, sizeof(b) - k, fmt, ap);
    va_end(ap);
    k = m < 0 ? k : (k + m >= (int) sizeof(b) ? (int) sizeof(b) - 1 : k + m);
    re4dc_qalink_send(b, (unsigned) k);
}

void command(char* line) {
    char* save = nullptr;
    char* id = strtok_r(line, " \r\n", &save);
    char* cmd = id ? strtok_r(nullptr, " \r\n", &save) : nullptr;
    char* rest = save ? save + strspn(save, " ") : nullptr;
    if (rest) { char* e = rest + strlen(rest); while (e > rest && (e[-1] == '\n' || e[-1] == '\r' || e[-1] == ' ')) *--e = 0; }
    if (!id || !cmd) return;
    if (strlen(id) > 15) id[15] = 0;
    re4dc_log("qalink: cmd %s %s %s\n", id, cmd, rest ? rest : "");
    if (!strcasecmp(cmd, "PING") || !strcasecmp(cmd, "HELLO"))
        reply(id, true, "PONG %s build=BENCHMARK menu=0 scene=%d", rest ? rest : "", re4dc_bench_scene_no());
    else
        reply(id, false, "%s: not on a benchmark disc (no QA menu); PING only", cmd);
}

const unsigned long kLog = sizeof(re4dc_logbuf);
char log_at(unsigned long i) { return re4dc_logbuf[i % kLog]; }

void send_log() {   // new RAM log bytes since the last call, at most 640 a second (the QA disc's L stream)
    const unsigned long head = re4dc_log_head;
    if (!g_bl.log_sent || head - g_bl.log_sent > kLog) g_bl.log_sent = head > kLog ? head - kLog : 0;
    unsigned long n = head - g_bl.log_sent, dropped = 0;
    if (!n) return;
    if (n > 640) { dropped = n - 640; g_bl.log_sent += dropped; n = 640; }
    char b[720];
    int h = snprintf(b, sizeof(b), "L %u %lu\n", ++g_bl.log_seq, dropped);
    for (unsigned long i = 0; i < n; ++i) {
        const char c = log_at(g_bl.log_sent + i);
        b[h++] = (c >= 32 && c < 127) || c == '\n' ? c : ' ';
    }
    g_bl.log_sent += n;
    re4dc_qalink_send_bulk(b, (unsigned) h);   // skipped when backlogged
}

bool wanted_line(unsigned long at) {
    static const char* const kPre[] = {"bench: ", "PACE"};
    for (const char* p : kPre) {
        unsigned long i = 0;
        for (; p[i] && log_at(at + i) == p[i]; ++i) {}
        if (!p[i]) return true;
    }
    return false;
}

// The result rows, lossless: complete lines only, while the transmit ring has room (at most 3 datagrams a pass).
void send_results() {
    const unsigned long head = re4dc_log_head;
    if (!g_bl.b_sent) g_bl.b_sent = head > kLog ? head - kLog : 0;   // from the oldest line still in the ring
    if (head - g_bl.b_sent > kLog) { g_bl.b_dropped += head - kLog - g_bl.b_sent; g_bl.b_sent = head - kLog; }
    for (int d = 0; d < 3; ++d) {
        unsigned tx, rx, dr, q;
        re4dc_qalink_counters(&tx, &rx, &dr, &q);
        if (q > 1024) return;   // let the PPP thread drain first (result rows wait; never skipped)
        char b[1100];
        int h = snprintf(b, sizeof(b), "B %u %lu\n", g_bl.b_seq + 1, g_bl.b_dropped);
        const int h0 = h;
        unsigned long at = g_bl.b_sent;
        while (at < head) {
            unsigned long e = at;
            while (e < head && log_at(e) != '\n') ++e;
            if (e >= head) break;   // the line is not complete yet
            const unsigned long len = e - at + 1;
            if (wanted_line(at)) {
                if (len > sizeof(b) - (unsigned) h0) { at = e + 1; continue; }   // longer than a datagram: skipped
                if (h + len > sizeof(b)) break;
                for (unsigned long i = 0; i < len; ++i) {
                    const char c = log_at(at + i);
                    b[h++] = (c >= 32 && c < 127) || c == '\n' ? c : ' ';
                }
            }
            at = e + 1;
        }
        if (h > h0) {
            if (!re4dc_qalink_send(b, (unsigned) h)) return;   // ring full: the same lines again next pass
            ++g_bl.b_seq;
            g_bl.b_dropped = 0;
        }
        g_bl.b_sent = at;
        if (h == h0 || at >= head) return;
    }
}
}  // namespace

extern "C" void re4dc_qa_link_bench_tick(void) {
    const uint64_t t0 = timer_us_gettime64();
    if (!g_bl.cfg_read) read_cfg();
    if (!re4dc_qalink_up()) return;
    char buf[1400];
    for (int k = 0; k < 4 && re4dc_qalink_recv(buf, sizeof(buf)) >= 0; ++k) command(buf);
    send_results();
    const uint64_t ms = t0 / 1000;
    if (ms >= g_bl.next_ms) {
        g_bl.next_ms = ms + 1000;
        unsigned tx, rx, dr, q;
        re4dc_qalink_counters(&tx, &rx, &dr, &q);
        char st[64], t[300];
        re4dc_qalink_state_text(st, sizeof(st));
        const int n = snprintf(t, sizeof(t), "T %u %u 1/1\nbench scene=%d\nlink %s tx=%u rx=%u drops=%u queued=%u skips=%u "
                               "cost_us_per_s=%u\n", ++g_bl.seq, (unsigned) (ms & 0xFFFFFFFFu), re4dc_bench_scene_no(),
                               st, tx, rx, dr, q, re4dc_qalink_bulk_skips(), g_bl.cost_last);
        re4dc_qalink_send_bulk(t, (unsigned) (n < (int) sizeof(t) ? n : (int) sizeof(t) - 1));
        send_log();
    }
    const uint64_t t1 = timer_us_gettime64();
    g_bl.cost_us += t1 - t0;
    if (t1 - g_bl.cost_t0 >= 1000000) { g_bl.cost_last = (unsigned) g_bl.cost_us; g_bl.cost_us = 0; g_bl.cost_t0 = t1; }
}
