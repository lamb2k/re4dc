/* host.c: the loader's protocol core on a PC, for the end-to-end host tests (lane eng-loop, 2026-11-19).
   The same cl_core.c / cl_util.c as the console; UDP on localhost stands in for the modem link and a static buffer
   for the hand-off area. "Running" a program writes the verified bytes to <dir>/exec-<session>.bin and then plays the
   program's part through the hand-off area as the client library would (args: report / crash / timeout / none /
   big:<n>), then "reboots" the loader (cl_core_init again on the same hand-off area).

     cl_host --lport 52061 --peer 127.0.0.1:52062 --dir <out> [--max-raw N] [--exit-after N]
     cl_host --inflate <in> <out>      raw inflate a file (unit test against zlib)
     cl_host --sha256 <file>           print the SHA-256 (unit test against hashlib) */
#include "cl_core.h"
#include <arpa/inet.h>
#include <netinet/in.h>
#include <poll.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <time.h>
#include <unistd.h>

static int g_sock = -1;
static struct sockaddr_in g_peer;
static cl_handoff_t g_handoff;
static const char *g_dir = ".";
static int g_execs, g_exit_after;
static uint32_t g_t0;

static uint32_t now_ms(void *ctx) {
    (void)ctx;
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint32_t)(ts.tv_sec * 1000u + ts.tv_nsec / 1000000u) - g_t0;
}
static int send_cb(void *ctx, const uint8_t *p, size_t n) {
    (void)ctx;
    return sendto(g_sock, p, n, 0, (struct sockaddr *)&g_peer, sizeof(g_peer)) == (ssize_t)n;
}
static void log_cb(void *ctx, const char *line) {
    (void)ctx;
    printf("%8u loader: %s\n", (unsigned)now_ms(NULL), line);
    fflush(stdout);
}
static void *alloc_cb(size_t n) { return malloc(n); }
static void free_cb(void *p) { free(p); }

static void report(const char *fmt, ...) __attribute__((format(printf, 1, 2)));
#include <stdarg.h>
static void report(const char *fmt, ...) {
    cl_handoff_hdr_t *h = &g_handoff.h;
    va_list ap;
    va_start(ap, fmt);
    int n = vsnprintf((char *)g_handoff.report + h->report_len, CL_REPORT_MAX - h->report_len, fmt, ap);
    va_end(ap);
    if (n > 0) h->report_len += (uint32_t)n < CL_REPORT_MAX - h->report_len ? (uint32_t)n : CL_REPORT_MAX - h->report_len - 1;
}

/* the program's part: what client.c does on the console */
static void play_program(const uint8_t *img, size_t len, uint32_t session) {
    cl_handoff_hdr_t *h = &g_handoff.h;
    if (!cl_handoff_valid(&g_handoff) || h->state != CL_RUN_RUNNING || h->run_id != session) {
        printf("program: no valid hand-off header\n");
        return;
    }
    uint8_t sha[32];
    cl_sha256_t s;
    cl_sha256_init(&s);
    cl_sha256_update(&s, img, len);
    cl_sha256_final(&s, sha);
    char hex[65];
    for (int i = 0; i < 32; ++i) sprintf(hex + 2 * i, "%02x", sha[i]);
    const char *args = h->args;
    h->report_len = 0;
    if (strstr(args, "none")) {
        /* a program without the client: the hand-off stays RUNNING */
        return;
    }
    report("program sha256=%s bytes=%u args=%s\n", hex, (unsigned)len, args);
    const char *big = strstr(args, "big:");
    if (big) {
        unsigned n = (unsigned)strtoul(big + 4, NULL, 10);
        for (unsigned i = 0; i < n && h->report_len < CL_REPORT_MAX - 1; ++i)
            g_handoff.report[h->report_len++] = (uint8_t)('a' + (i * 7 + i / 13) % 26);
    }
    if (strstr(args, "crash")) {
        h->state = CL_RUN_CRASHED; h->crash_evt = 0x180; h->crash_pc = 0x8c0123a4; h->crash_pr = 0x8c012000;
        h->exit_code = -1;
    } else if (strstr(args, "timeout")) {
        h->state = CL_RUN_TIMEOUT; h->exit_code = -2;
    } else {
        h->state = CL_RUN_DONE; h->exit_code = 0;
    }
    h->report_crc = cl_crc32(0, g_handoff.report, h->report_len);
    cl_handoff_seal(&g_handoff);
}

static int file_bytes(const char *path, uint8_t **out, size_t *n) {
    FILE *f = fopen(path, "rb");
    if (!f) return -1;
    fseek(f, 0, SEEK_END);
    long sz = ftell(f);
    fseek(f, 0, SEEK_SET);
    *out = malloc(sz ? (size_t)sz : 1);
    *n = fread(*out, 1, (size_t)sz, f);
    fclose(f);
    return 0;
}

int main(int argc, char **argv) {
    unsigned lport = 52061, max_raw = 15 * 1024 * 1024;
    const char *peer = "127.0.0.1:52062";
    if (argc == 4 && !strcmp(argv[1], "--inflate")) {
        uint8_t *in; size_t n;
        if (file_bytes(argv[2], &in, &n)) return 2;
        size_t cap = 64u << 20, got = 0;
        uint8_t *outb = malloc(cap);
        int r = cl_inflate(in, n, outb, cap, &got);
        if (r) { fprintf(stderr, "inflate error %d\n", r); free(outb); free(in); return 1; }
        FILE *f = fopen(argv[3], "wb");
        fwrite(outb, 1, got, f);
        fclose(f);
        free(outb);
        free(in);
        return 0;
    }
    if (argc == 3 && !strcmp(argv[1], "--sha256")) {
        uint8_t *in, sha[32]; size_t n;
        if (file_bytes(argv[2], &in, &n)) return 2;
        cl_sha256_t s;
        cl_sha256_init(&s);
        cl_sha256_update(&s, in, n);
        cl_sha256_final(&s, sha);
        for (int i = 0; i < 32; ++i) printf("%02x", sha[i]);
        printf("\n");
        free(in);
        return 0;
    }
    for (int i = 1; i + 1 < argc; i += 2) {
        if (!strcmp(argv[i], "--lport")) lport = (unsigned)atoi(argv[i + 1]);
        else if (!strcmp(argv[i], "--peer")) peer = argv[i + 1];
        else if (!strcmp(argv[i], "--dir")) g_dir = argv[i + 1];
        else if (!strcmp(argv[i], "--max-raw")) max_raw = (unsigned)strtoul(argv[i + 1], NULL, 0);
        else if (!strcmp(argv[i], "--exit-after")) g_exit_after = atoi(argv[i + 1]);
    }
    g_t0 = 0;
    g_t0 = now_ms(NULL);
    g_sock = socket(AF_INET, SOCK_DGRAM, 0);
    struct sockaddr_in me;
    memset(&me, 0, sizeof(me));
    me.sin_family = AF_INET;
    me.sin_port = htons((uint16_t)lport);
    me.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    if (bind(g_sock, (struct sockaddr *)&me, sizeof(me)) < 0) { perror("bind"); return 2; }
    char host[64];
    strncpy(host, peer, sizeof(host) - 1);
    host[sizeof(host) - 1] = 0;
    char *colon = strchr(host, ':');
    unsigned pport = colon ? (unsigned)atoi(colon + 1) : CL_PORT;
    if (colon) *colon = 0;
    memset(&g_peer, 0, sizeof(g_peer));
    g_peer.sin_family = AF_INET;
    g_peer.sin_port = htons((uint16_t)pport);
    inet_pton(AF_INET, host, &g_peer.sin_addr);

    memset(&g_handoff, 0xA5, sizeof(g_handoff));   /* power-on garbage */
    cl_platform_t p;
    memset(&p, 0, sizeof(p));
    p.send = send_cb; p.now_ms = now_ms; p.alloc = alloc_cb; p.free = free_cb; p.log = log_cb;
    p.handoff = &g_handoff; p.max_raw = max_raw; p.console_ip = htonl(0x7f000001);
    p.link_host = g_peer.sin_addr.s_addr; p.link_port = pport; p.link_lport = lport;
    p.number = "1111111"; p.build = "host cl_core";
    static cl_core_t c;
    cl_core_init(&c, &p);
    printf("%8u loader: up, lport %u peer %s:%u\n", (unsigned)now_ms(NULL), lport, host, pport);
    fflush(stdout);
    uint8_t buf[2048];
    for (;;) {
        struct pollfd pf = {g_sock, POLLIN, 0};
        if (poll(&pf, 1, 10) > 0) {
            for (;;) {
                ssize_t n = recv(g_sock, buf, sizeof(buf), MSG_DONTWAIT);
                if (n <= 0) break;
                cl_core_input(&c, buf, (size_t)n);
                if (c.exec_pending) break;
            }
        }
        cl_core_tick(&c);
        if (c.exec_pending) {
            /* the console flushes the EXEC datagram, hangs up and jumps; here: write the image, play the program */
            char path[512];
            snprintf(path, sizeof(path), "%s/exec-%08x.bin", g_dir, (unsigned)c.session);
            FILE *f = fopen(path, "wb");
            if (f) { fwrite(c.raw, 1, c.raw_len, f); fclose(f); }
            printf("%8u loader: EXEC session %08x bytes %u -> %s\n", (unsigned)now_ms(NULL), (unsigned)c.session,
                   (unsigned)c.raw_len, path);
            fflush(stdout);
            play_program(c.raw, c.raw_len, c.session);
            ++g_execs;
            if (g_exit_after && g_execs >= g_exit_after) return 0;
            /* the program ran; the console redials (a silent second here), the loader boots again */
            usleep(1000 * 1000);
            while (recv(g_sock, buf, sizeof(buf), MSG_DONTWAIT) > 0) {}   /* the line was down: nothing arrives */
            if (c.raw && c.raw != c.comp) free(c.raw);
            if (c.comp) free(c.comp);
            if (c.bitmap) free(c.bitmap);
            cl_core_init(&c, &p);
            printf("%8u loader: rebooted, boot %u\n", (unsigned)now_ms(NULL), (unsigned)c.boot_count);
            fflush(stdout);
        }
    }
}
