/* Count executed entry PCs in retained D367 traces, independent of call-stack reconstruction.
 * Each trace record is two little-endian u32 words. A type-1 record (word1 >> 28)
 * executes word1 & 0x0fffffff consecutive SH-4 instructions beginning at word0.
 * Other record types describe memory events and are not instruction executions.
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int cmp_u32(const void *a, const void *b) {
    uint32_t x = *(const uint32_t *)a, y = *(const uint32_t *)b;
    return x < y ? -1 : x != y;
}
static uint32_t le32(const unsigned char *p) {
    return (uint32_t)p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
}
int main(int argc, char **argv) {
    if (argc < 3) { fprintf(stderr, "usage: trace_entries entries.txt trace...\n"); return 2; }
    uint32_t entries[1024]; unsigned n = 0, e;
    FILE *f = fopen(argv[1], "r");
    if (!f) { perror(argv[1]); return 1; }
    while (fscanf(f, "%x", &e) == 1) {
        if (n == 1024) { fprintf(stderr, "too many entries\n"); fclose(f); return 1; }
        entries[n++] = e;
    }
    fclose(f); qsort(entries, n, sizeof(*entries), cmp_u32);
    unsigned unique = 0;
    for (unsigned i = 0; i < n; ++i) if (!i || entries[i] != entries[i - 1]) entries[unique++] = entries[i];
    n = unique;
    unsigned char *buf = malloc(8 * 65536);
    if (!buf) return 1;
    puts("sample_index\ttrace\tentry\texecuted_entry_pc_count");
    for (int a = 2; a < argc; ++a) {
        uint64_t count[1024] = {0};
        f = fopen(argv[a], "rb"); if (!f) { perror(argv[a]); free(buf); return 1; }
        size_t bytes;
        while ((bytes = fread(buf, 1, 8 * 65536, f))) {
            if (bytes % 8) { fprintf(stderr, "truncated record: %s\n", argv[a]); fclose(f); free(buf); return 1; }
            for (size_t j = 0; j < bytes; j += 8) {
                uint32_t pc = le32(buf + j), word = le32(buf + j + 4);
                if (word >> 28 != 1) continue;
                uint64_t end = (uint64_t)pc + 2 * (uint64_t)(word & 0x0fffffff);
                unsigned lo = 0, hi = n;
                while (lo < hi) { unsigned mid = lo + (hi - lo) / 2; if (entries[mid] < pc) lo = mid + 1; else hi = mid; }
                while (lo < n && entries[lo] < end) {
                    if (!((entries[lo] - pc) & 1)) count[lo]++;
                    lo++;
                }
            }
        }
        if (ferror(f)) { perror(argv[a]); fclose(f); free(buf); return 1; }
        fclose(f);
        for (unsigned i = 0; i < n; ++i)
            printf("%d\t%s\t%08x\t%llu\n", a - 2, argv[a], entries[i], (unsigned long long)count[i]);
    }
    free(buf); return 0;
}
