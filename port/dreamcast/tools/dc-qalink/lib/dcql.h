/* dcql.h: dc-qalink, a QA/telemetry link for KallistiOS programs over the Dreamcast modem.
 *
 * The console dials a PPP peer (a DreamPi or any Linux box with a modem and pppd), then one UDP socket carries short
 * text rows both ways. Network work runs on two background threads with static stacks; the functions below that the
 * program calls every frame only copy bytes into or out of two bounded rings. MIT licence (see LICENSE).
 *
 * Rows the console sends (first letter = kind):
 *   T <seq> <ms> <part>/<parts>\n<body>   telemetry; body is usually "name k=v k=v" lines
 *   L <seq> <part>/<parts>\n<text>        log text
 *   A <id> OK|ERR <text>                  answer to command <id>
 *   M <ms> <label>                        mark (also echoed as an A answer and an L line "dcql-mark: <label>")
 * Rows the console receives: "<id> <VERB> [args]" (PING, MARK and STATUS are built in).
 */
#ifndef DCQL_H
#define DCQL_H

#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

#define DCQL_DATAGRAM_MAX 1200 /* every datagram, both ways: below the PPP MTU, never IP-fragmented */
#define DCQL_PART_MAX 1100     /* payload of one T / L part (header added on top) */

typedef enum {
    DCQL_OFF = 0,
    DCQL_DIALLING, /* modem dial in progress (attempt 1..3) */
    DCQL_PPP,      /* carrier up, PPP negotiating */
    DCQL_UP,       /* socket open: rows move */
    DCQL_FAILED,   /* three attempts failed; dcql_start() retries */
    DCQL_DROPPED,  /* line dropped; dcql_start() hangs up and redials */
    DCQL_STOPPING  /* hanging up */
} dcql_state_t;

typedef struct {
    const char* number;      /* dial string, default "1111111" (DreamPi answers any number) */
    const char* host;        /* relay IPv4 "a.b.c.d", or NULL / "peer" to learn it from its first datagram */
    unsigned short port;     /* relay UDP port, default 52040 */
    unsigned short lport;    /* console UDP port, default 52040 (use another one under Flycast's modem emulation) */
    const char* user;        /* PAP login if the peer asks, default "dream" / "dreamcast" */
    const char* pass;
    /* Optional: return 0 to refuse bulk rows (T / L) right now, e.g. when the KOS heap is low. NULL = always allow. */
    int (*bulk_ok)(void);
    /* Optional: the library's own diagnostics ("dcql: up ip=..."). Called from any thread; keep it cheap. */
    void (*log)(const char* line);
} dcql_config_t;

/* A command handler. Return 1 if handled (answer it with dcql_answer, now or later), 0 for "unknown". Runs on the
 * thread that calls dcql_poll(). verb is upper-cased; args may be "". */
typedef int (*dcql_command_fn)(const char* id, const char* verb, const char* args, void* user);

typedef struct {
    unsigned tx_bytes, rx_bytes; /* UDP payload bytes moved */
    unsigned tx_drops;           /* rows refused (ring full / send failed) */
    unsigned bulk_skips;         /* T / L rows skipped by the backlog cap or bulk_ok() */
    unsigned rx_drops;           /* received datagrams rejected (oversize, empty, wrong peer, ring full) */
    unsigned tx_stalls;          /* modem writes that made no progress for 2 s (the link then drops) */
    unsigned queued;             /* bytes waiting in the tx ring */
    unsigned rate;               /* modem connect rate, bps */
    int attempt, err;            /* last dial attempt (1..3) and error code (0 = none) */
} dcql_counters_t;

#if defined(DCQL_ENABLE) && DCQL_ENABLE
void dcql_config(const dcql_config_t* cfg);    /* call before dcql_start(); copies the strings */
void dcql_set_command(dcql_command_fn fn, void* user);
int dcql_start(void);                          /* dial (or hang up + redial); returns at once; 0 = started/already */
void dcql_stop(void);                          /* hang up in the background; returns at once */
dcql_state_t dcql_state(void);
void dcql_state_text(char* out, size_t n);     /* "DIALLING 1/3", "UP 10.0.0.2 TO 10.0.0.1", ... */
void dcql_counters(dcql_counters_t* c);

/* Per frame (or any cadence), on one thread: dispatches received commands to the handler / built-ins. */
void dcql_poll(void);

/* Sending; all return 1 if queued, 0 if refused (link not up, ring full, or bulk cap). Never block. */
int dcql_telemetry(const char* body);          /* T row; split into parts at line ends */
int dcql_log(const char* text);                /* L row */
int dcql_answer(const char* id, int ok, const char* fmt, ...) __attribute__((format(printf, 3, 4)));
int dcql_mark(const char* label);              /* M row + L echo */
int dcql_send_raw(const void* p, size_t n);    /* one datagram as-is (<= DCQL_DATAGRAM_MAX) */
#else
/* DCQL_ENABLE off (the default; dcql.mk sets it with `make DCQL_ENABLE=1`): every call compiles to nothing, so a
 * retail build carries no modem, PPP or socket code. */
static inline void dcql_config(const dcql_config_t* c) { (void) c; }
static inline void dcql_set_command(dcql_command_fn f, void* u) { (void) f; (void) u; }
static inline int dcql_start(void) { return -1; }
static inline void dcql_stop(void) {}
static inline dcql_state_t dcql_state(void) { return DCQL_OFF; }
static inline void dcql_state_text(char* o, size_t n) { if (n) o[0] = 0; }
static inline void dcql_counters(dcql_counters_t* c) { *c = (dcql_counters_t){0}; }
static inline void dcql_poll(void) {}
static inline int dcql_telemetry(const char* b) { (void) b; return 0; }
static inline int dcql_log(const char* t) { (void) t; return 0; }
static inline int dcql_answer(const char* id, int ok, const char* fmt, ...) { (void) id; (void) ok; (void) fmt; return 0; }
static inline int dcql_mark(const char* l) { (void) l; return 0; }
static inline int dcql_send_raw(const void* p, size_t n) { (void) p; (void) n; return 0; }
#endif

#ifdef __cplusplus
}
#endif
#endif
