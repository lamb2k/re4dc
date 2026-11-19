/* cl_proto.h: the console loop's wire format (lane eng-loop, 2026-11-19). Shared by the loader (console), its host
   build and, by value, tools/consoleloop/clproto.py. Design: docs/engine/CONSOLE_LOOP.md section 3.

   Datagram: 16-byte header, payload, CRC-32 (IEEE, zlib's) of header + payload. Little-endian. At most CL_DGRAM_MAX
   bytes: the console reassembles no IP fragments. */
#ifndef CL_PROTO_H
#define CL_PROTO_H
#include <stdint.h>
#include <stddef.h>

#define CL_MAGIC0 'C'
#define CL_MAGIC1 'L'
#define CL_VERSION 1
#define CL_HDR 16
#define CL_DGRAM_MAX 1200
#define CL_PAYLOAD_MAX (CL_DGRAM_MAX - CL_HDR - 4)
#define CL_CHUNK 1024
#define CL_PORT 52060
#define CL_LOAD_ADDR 0x8c010000u
#define CL_ARGS_MAX 512
#define CL_ACK_BITS 2048 /* chunks covered by an ACK's bitmap after the cumulative point */

enum {
    /* console -> PC */
    CL_HELLO = 0x01, CL_ACK = 0x02, CL_VERDICT = 0x03, CL_REPORT = 0x04, CL_EXEC = 0x05, CL_ERR = 0x06,
    /* PC -> console */
    CL_LOAD = 0x10, CL_DATA = 0x11, CL_RUN = 0x12, CL_REPQ = 0x13, CL_REPDONE = 0x14, CL_PING = 0x15,
    CL_ABORT = 0x16, CL_VERIFY = 0x17
};

/* VERDICT / ERR codes */
enum {
    CL_OK = 0, CL_E_COMP_CRC = 1, CL_E_INFLATE = 2, CL_E_RAW_LEN = 3, CL_E_SHA = 4, CL_E_SIZE = 5, CL_E_ADDR = 6,
    CL_E_NOMEM = 7, CL_E_NOT_VERIFIED = 8, CL_E_SESSION = 9, CL_E_BAD_LOAD = 10, CL_E_CODEC = 11, CL_E_NO_REPORT = 12,
    CL_E_BUSY = 13
};

/* loader states (HELLO) */
enum { CL_ST_IDLE = 0, CL_ST_RECEIVING = 1, CL_ST_VERIFIED = 2, CL_ST_FAILED = 3, CL_ST_EXEC = 4 };

/* codecs */
enum { CL_CODEC_NONE = 0, CL_CODEC_DEFLATE = 1 };

/* LOAD payload */
typedef struct {
    uint32_t comp_len, raw_len, chunk_size, nchunks;
    uint8_t codec, flags;
    uint16_t deadline_s;
    uint32_t load_addr;
    uint8_t sha256[32];
    uint32_t comp_crc;
    uint16_t args_len;
    uint16_t reserved;
    /* args follow (args_len bytes, no terminator) */
} cl_load_t;
#define CL_LOAD_FIXED 64

/* HELLO payload (fixed) */
typedef struct {
    uint32_t boot_count, uptime_ms, state, session;
    uint32_t have, nchunks, rx_bytes, rx_bad;
    uint32_t report_run, report_state, report_len, report_crc;
    int32_t report_exit;
    uint32_t console_ip, max_raw, verdict;
    char build[32];
} cl_hello_t;
#define CL_HELLO_LEN 96

/* little-endian helpers (the SH-4 and x86 are both little-endian; these keep the code honest elsewhere) */
static inline uint32_t cl_rd32(const uint8_t *p) {
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}
static inline uint16_t cl_rd16(const uint8_t *p) { return (uint16_t)(p[0] | (p[1] << 8)); }
static inline void cl_wr32(uint8_t *p, uint32_t v) {
    p[0] = (uint8_t)v; p[1] = (uint8_t)(v >> 8); p[2] = (uint8_t)(v >> 16); p[3] = (uint8_t)(v >> 24);
}
static inline void cl_wr16(uint8_t *p, uint16_t v) { p[0] = (uint8_t)v; p[1] = (uint8_t)(v >> 8); }

/* cl_util.c */
uint32_t cl_crc32(uint32_t crc, const void *buf, size_t n);  /* zlib-compatible: start with 0 */
typedef struct { uint32_t h[8]; uint64_t len; uint8_t buf[64]; uint32_t n; } cl_sha256_t;
void cl_sha256_init(cl_sha256_t *s);
void cl_sha256_update(cl_sha256_t *s, const void *p, size_t n);
void cl_sha256_final(cl_sha256_t *s, uint8_t out[32]);
/* raw deflate (RFC 1951, no zlib header). 0 = ok and *out_len set; <0 = malformed input or the output would not fit.
   Never reads past src + src_len or writes past dst + dst_cap. */
int cl_inflate(const uint8_t *src, size_t src_len, uint8_t *dst, size_t dst_cap, size_t *out_len);

/* datagram framing: returns the total length, or 0 if it would not fit */
size_t cl_frame(uint8_t *out, uint8_t type, uint32_t session, uint32_t a, uint16_t b, const void *payload, uint16_t len);
/* checks magic, version, length and CRC; returns the payload length or -1 */
int cl_unframe(const uint8_t *in, size_t n);

#endif
