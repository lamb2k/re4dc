/* cl_util.c: CRC-32, SHA-256, raw inflate and datagram framing for the console loop (lane eng-loop, 2026-11-19).
   Portable C99: the loader (SH-4, KallistiOS) and its host build use the same file. The inflate follows RFC 1951
   in the canonical-code style of zlib's contrib/puff (no tables beyond the code counts), with every input read and
   output write bounds-checked: a malformed stream returns an error, never a fault. */
#include "cl_proto.h"
#include <string.h>

/* ---------------------------------------------------------------- CRC-32 (IEEE 802.3, reflected, as zlib) */
static uint32_t crc_table[256];
static int crc_ready;
static void crc_init(void) {
    for (uint32_t i = 0; i < 256; ++i) {
        uint32_t c = i;
        for (int k = 0; k < 8; ++k) c = (c & 1) ? 0xEDB88320u ^ (c >> 1) : c >> 1;
        crc_table[i] = c;
    }
    crc_ready = 1;
}
uint32_t cl_crc32(uint32_t crc, const void *buf, size_t n) {
    const uint8_t *p = (const uint8_t *)buf;
    if (!crc_ready) crc_init();
    crc = ~crc;
    while (n--) crc = crc_table[(crc ^ *p++) & 0xff] ^ (crc >> 8);
    return ~crc;
}

/* ---------------------------------------------------------------- SHA-256 (FIPS 180-4) */
static const uint32_t K256[64] = {
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5, 0xd807aa98,
    0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174, 0xe49b69c1, 0xefbe4786,
    0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da, 0x983e5152, 0xa831c66d, 0xb00327c8,
    0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967, 0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
    0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85, 0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819,
    0xd6990624, 0xf40e3585, 0x106aa070, 0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a,
    0x5b9cca4f, 0x682e6ff3, 0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7,
    0xc67178f2};
#define ROR(x, n) (((x) >> (n)) | ((x) << (32 - (n))))
static void sha_block(cl_sha256_t *s, const uint8_t *p) {
    uint32_t w[64], a, b, c, d, e, f, g, h;
    for (int i = 0; i < 16; ++i)
        w[i] = ((uint32_t)p[4 * i] << 24) | ((uint32_t)p[4 * i + 1] << 16) | ((uint32_t)p[4 * i + 2] << 8) | p[4 * i + 3];
    for (int i = 16; i < 64; ++i) {
        uint32_t s0 = ROR(w[i - 15], 7) ^ ROR(w[i - 15], 18) ^ (w[i - 15] >> 3);
        uint32_t s1 = ROR(w[i - 2], 17) ^ ROR(w[i - 2], 19) ^ (w[i - 2] >> 10);
        w[i] = w[i - 16] + s0 + w[i - 7] + s1;
    }
    a = s->h[0]; b = s->h[1]; c = s->h[2]; d = s->h[3]; e = s->h[4]; f = s->h[5]; g = s->h[6]; h = s->h[7];
    for (int i = 0; i < 64; ++i) {
        uint32_t t1 = h + (ROR(e, 6) ^ ROR(e, 11) ^ ROR(e, 25)) + ((e & f) ^ (~e & g)) + K256[i] + w[i];
        uint32_t t2 = (ROR(a, 2) ^ ROR(a, 13) ^ ROR(a, 22)) + ((a & b) ^ (a & c) ^ (b & c));
        h = g; g = f; f = e; e = d + t1; d = c; c = b; b = a; a = t1 + t2;
    }
    s->h[0] += a; s->h[1] += b; s->h[2] += c; s->h[3] += d; s->h[4] += e; s->h[5] += f; s->h[6] += g; s->h[7] += h;
}
void cl_sha256_init(cl_sha256_t *s) {
    static const uint32_t iv[8] = {0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
                                   0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19};
    memcpy(s->h, iv, sizeof(iv));
    s->len = 0;
    s->n = 0;
}
void cl_sha256_update(cl_sha256_t *s, const void *data, size_t n) {
    const uint8_t *p = (const uint8_t *)data;
    s->len += n;
    while (n) {
        if (s->n == 0 && n >= 64) { sha_block(s, p); p += 64; n -= 64; continue; }
        uint32_t k = 64 - s->n;
        if (k > n) k = (uint32_t)n;
        memcpy(s->buf + s->n, p, k);
        s->n += k; p += k; n -= k;
        if (s->n == 64) { sha_block(s, s->buf); s->n = 0; }
    }
}
void cl_sha256_final(cl_sha256_t *s, uint8_t out[32]) {
    uint64_t bits = s->len * 8;
    uint8_t pad = 0x80, z = 0, lb[8];
    cl_sha256_update(s, &pad, 1);
    while (s->n != 56) cl_sha256_update(s, &z, 1);
    for (int i = 0; i < 8; ++i) lb[i] = (uint8_t)(bits >> (56 - 8 * i));
    cl_sha256_update(s, lb, 8);
    for (int i = 0; i < 8; ++i) {
        out[4 * i] = (uint8_t)(s->h[i] >> 24); out[4 * i + 1] = (uint8_t)(s->h[i] >> 16);
        out[4 * i + 2] = (uint8_t)(s->h[i] >> 8); out[4 * i + 3] = (uint8_t)s->h[i];
    }
}

/* ---------------------------------------------------------------- raw inflate */
typedef struct {
    const uint8_t *in; size_t in_len, in_pos;
    uint8_t *out; size_t out_cap, out_pos;
    uint32_t bitbuf; int bitcnt;
    int err;
} inf_t;
typedef struct { short count[16]; short symbol[288]; } huff_t;

static int bits(inf_t *s, int need) {
    uint32_t v = s->bitbuf;
    while (s->bitcnt < need) {
        if (s->in_pos >= s->in_len) { s->err = -1; return 0; }   /* ran out of input */
        v |= (uint32_t)s->in[s->in_pos++] << s->bitcnt;
        s->bitcnt += 8;
    }
    s->bitbuf = v >> need;
    s->bitcnt -= need;
    return (int)(v & ((1u << need) - 1));
}
static int decode(inf_t *s, const huff_t *h) {
    int code = 0, first = 0, index = 0;
    for (int len = 1; len < 16; ++len) {
        code |= bits(s, 1);
        if (s->err) return -1;
        int count = h->count[len];
        if (code - count < first) return h->symbol[index + (code - first)];
        index += count; first += count; first <<= 1; code <<= 1;
    }
    s->err = -10;   /* ran out of codes */
    return -1;
}
/* returns 0 complete, >0 incomplete, <0 over-subscribed */
static int construct(huff_t *h, const short *length, int n) {
    short offs[16];
    for (int len = 0; len < 16; ++len) h->count[len] = 0;
    for (int sym = 0; sym < n; ++sym) h->count[length[sym]]++;
    if (h->count[0] == n) return 0;
    int left = 1;
    for (int len = 1; len < 16; ++len) {
        left <<= 1;
        left -= h->count[len];
        if (left < 0) return left;
    }
    offs[1] = 0;
    for (int len = 1; len < 15; ++len) offs[len + 1] = offs[len] + h->count[len];
    for (int sym = 0; sym < n; ++sym)
        if (length[sym] != 0) h->symbol[offs[length[sym]]++] = (short)sym;
    return left;
}
static const short LBASE[29] = {3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 15, 17, 19, 23, 27, 31,
                                35, 43, 51, 59, 67, 83, 99, 115, 131, 163, 195, 227, 258};
static const short LEXT[29] = {0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 4, 4, 4, 4, 5, 5, 5, 5, 0};
static const short DBASE[30] = {1, 2, 3, 4, 5, 7, 9, 13, 17, 25, 33, 49, 65, 97, 129, 193, 257, 385, 513, 769,
                                1025, 1537, 2049, 3073, 4097, 6145, 8193, 12289, 16385, 24577};
static const short DEXT[30] = {0, 0, 0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8, 9, 9, 10, 10, 11, 11, 12, 12, 13, 13};

static int codes(inf_t *s, const huff_t *lencode, const huff_t *distcode) {
    for (;;) {
        int sym = decode(s, lencode);
        if (sym < 0) return s->err ? s->err : -10;
        if (sym < 256) {
            if (s->out_pos >= s->out_cap) return -2;   /* output full */
            s->out[s->out_pos++] = (uint8_t)sym;
        } else if (sym == 256) {
            return 0;
        } else {
            sym -= 257;
            if (sym >= 29) return -11;
            int len = LBASE[sym] + bits(s, LEXT[sym]);
            if (s->err) return s->err;
            int dsym = decode(s, distcode);
            if (dsym < 0) return s->err ? s->err : -10;
            if (dsym >= 30) return -12;
            size_t dist = (size_t)DBASE[dsym] + (size_t)bits(s, DEXT[dsym]);
            if (s->err) return s->err;
            if (dist > s->out_pos) return -13;   /* distance before the start */
            if ((size_t)len > s->out_cap - s->out_pos) return -2;
            uint8_t *o = s->out + s->out_pos;
            const uint8_t *from = o - dist;
            for (int i = 0; i < len; ++i) o[i] = from[i];   /* byte by byte: overlapping copies repeat */
            s->out_pos += (size_t)len;
        }
    }
}
static int stored(inf_t *s) {
    s->bitbuf = 0; s->bitcnt = 0;   /* to the byte boundary */
    if (s->in_pos + 4 > s->in_len) return -1;
    unsigned len = s->in[s->in_pos] | (s->in[s->in_pos + 1] << 8);
    unsigned nlen = s->in[s->in_pos + 2] | (s->in[s->in_pos + 3] << 8);
    s->in_pos += 4;
    if (len != (~nlen & 0xffff)) return -3;
    if (s->in_pos + len > s->in_len) return -1;
    if (len > s->out_cap - s->out_pos) return -2;
    memcpy(s->out + s->out_pos, s->in + s->in_pos, len);
    s->out_pos += len; s->in_pos += len;
    return 0;
}
static int fixed(inf_t *s) {
    static huff_t lencode, distcode;
    static int ready;
    if (!ready) {
        short lengths[288];
        int sym = 0;
        for (; sym < 144; ++sym) lengths[sym] = 8;
        for (; sym < 256; ++sym) lengths[sym] = 9;
        for (; sym < 280; ++sym) lengths[sym] = 7;
        for (; sym < 288; ++sym) lengths[sym] = 8;
        construct(&lencode, lengths, 288);
        for (sym = 0; sym < 30; ++sym) lengths[sym] = 5;
        construct(&distcode, lengths, 30);
        ready = 1;
    }
    return codes(s, &lencode, &distcode);
}
static int dynamic(inf_t *s) {
    static const short order[19] = {16, 17, 18, 0, 8, 7, 9, 6, 10, 5, 11, 4, 12, 3, 13, 2, 14, 1, 15};
    short lengths[320];
    huff_t lencode, distcode;
    int nlen = bits(s, 5) + 257, ndist = bits(s, 5) + 1, ncode = bits(s, 4) + 4;
    if (s->err) return s->err;
    if (nlen > 286 || ndist > 30) return -3;
    int index;
    for (index = 0; index < ncode; ++index) lengths[order[index]] = (short)bits(s, 3);
    for (; index < 19; ++index) lengths[order[index]] = 0;
    if (s->err) return s->err;
    if (construct(&lencode, lengths, 19) != 0) return -4;   /* the code-length code must be complete */
    index = 0;
    while (index < nlen + ndist) {
        int sym = decode(s, &lencode);
        if (sym < 0) return s->err ? s->err : -10;
        if (sym < 16) {
            lengths[index++] = (short)sym;
        } else {
            int len = 0, rep;
            if (sym == 16) {
                if (index == 0) return -5;
                len = lengths[index - 1];
                rep = 3 + bits(s, 2);
            } else if (sym == 17) {
                rep = 3 + bits(s, 3);
            } else {
                rep = 11 + bits(s, 7);
            }
            if (s->err) return s->err;
            if (index + rep > nlen + ndist) return -6;
            while (rep--) lengths[index++] = (short)len;
        }
    }
    if (lengths[256] == 0) return -9;   /* no end-of-block code */
    int err = construct(&lencode, lengths, nlen);
    if (err && (err < 0 || nlen != lencode.count[0] + lencode.count[1])) return -7;
    err = construct(&distcode, lengths + nlen, ndist);
    if (err && (err < 0 || ndist != distcode.count[0] + distcode.count[1])) return -8;
    return codes(s, &lencode, &distcode);
}
int cl_inflate(const uint8_t *src, size_t src_len, uint8_t *dst, size_t dst_cap, size_t *out_len) {
    inf_t s;
    memset(&s, 0, sizeof(s));
    s.in = src; s.in_len = src_len; s.out = dst; s.out_cap = dst_cap;
    int last, err;
    do {
        last = bits(&s, 1);
        int type = bits(&s, 2);
        if (s.err) return s.err;
        err = type == 0 ? stored(&s) : type == 1 ? fixed(&s) : type == 2 ? dynamic(&s) : -14;
        if (err) return err;
    } while (!last);
    if (out_len) *out_len = s.out_pos;
    return 0;
}

/* ---------------------------------------------------------------- framing */
size_t cl_frame(uint8_t *out, uint8_t type, uint32_t session, uint32_t a, uint16_t b, const void *payload,
                uint16_t len) {
    if (len > CL_PAYLOAD_MAX) return 0;
    out[0] = CL_MAGIC0; out[1] = CL_MAGIC1; out[2] = CL_VERSION; out[3] = type;
    cl_wr32(out + 4, session);
    cl_wr32(out + 8, a);
    cl_wr16(out + 12, len);
    cl_wr16(out + 14, b);
    if (len) memcpy(out + CL_HDR, payload, len);
    cl_wr32(out + CL_HDR + len, cl_crc32(0, out, CL_HDR + len));
    return (size_t)CL_HDR + len + 4;
}
int cl_unframe(const uint8_t *in, size_t n) {
    if (n < CL_HDR + 4 || n > CL_DGRAM_MAX) return -1;
    if (in[0] != CL_MAGIC0 || in[1] != CL_MAGIC1 || in[2] != CL_VERSION) return -1;
    unsigned len = cl_rd16(in + 12);
    if ((size_t)CL_HDR + len + 4 != n) return -1;
    if (cl_crc32(0, in, CL_HDR + len) != cl_rd32(in + CL_HDR + len)) return -1;
    return (int)len;
}

/* ---------------------------------------------------------------- hand-off area */
#include "cl_core.h"
uint32_t cl_handoff_hdr_crc(const cl_handoff_hdr_t *h) {
    return cl_crc32(0, (const uint8_t *)h + CL_HANDOFF_HDR_CRC_FROM, CL_HANDOFF_HDR_CRC_TO - CL_HANDOFF_HDR_CRC_FROM);
}
int cl_handoff_valid(const cl_handoff_t *a) {
    return a->h.magic == CL_HANDOFF_MAGIC && a->h.version == CL_HANDOFF_VERSION &&
           a->h.header_crc == cl_handoff_hdr_crc(&a->h);
}
void cl_handoff_seal(cl_handoff_t *a) {
    a->h.magic = CL_HANDOFF_MAGIC;
    a->h.version = CL_HANDOFF_VERSION;
    a->h.header_crc = cl_handoff_hdr_crc(&a->h);
}
int cl_handoff_report_ok(const cl_handoff_t *a) {
    return a->h.report_len <= CL_REPORT_MAX && cl_crc32(0, a->report, a->h.report_len) == a->h.report_crc;
}
