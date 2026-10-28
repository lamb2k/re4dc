#include <sh4zam/shz_strip.h>
extern "C" void shz_strip_walk_sq(shz_strip_walk_t *c) {
    const uint8_t *s=c->cursor;
    while(s<c->end) {
        const unsigned n=*s;
        const uint8_t *const indices=s+1;
        const uint8_t *ip=indices;
        unsigned left=n,all=255,any=0,t;
        // Source count streams have positive counts. Reject malformed zero
        // without touching its indices, leaving its count byte for the caller.
        if(!n) break;
        __asm__ __volatile__(
            "mov.b @%[ip]+,r0\n\t"
            "dt %[left]\n\t"
            "bt/s 2f\n\t"
            "extu.b r0,r0\n"
            "1:\n\t"
            "mov.b @(r0,%[oc]),%[t]\n\t"
            "mov.b @%[ip]+,r0\n\t"
            "dt %[left]\n\t"
            "and %[t],%[all]\n\t"
            "extu.b r0,r0\n\t"
            "bf/s 1b\n\t"
            "or %[t],%[any]\n"
            "2:\n\t"
            "mov.b @(r0,%[oc]),%[t]\n\t"
            "and %[t],%[all]\n\t"
            "or %[t],%[any]\n"
            : [ip]"+r"(ip),[left]"+r"(left),[all]"+r"(all),[any]"+r"(any),[t]"=&r"(t)
            : [oc]"r"(c->outcodes):"r0","t","memory");
        if(all&3u) ++c->culled;
        else if((any&3u)||n>c->limit) break;
        else if(all&60u) ++c->culled;
        else {
            shz_strip_sq_t strip{c->cache,indices,n,255,c->cull,c->q,0,0};
            shz_strip_sq(&strip);
            c->q=strip.q;
            ++c->emitted;
            c->accepted_triangles+=n>=2?n-2:0;
        }
        s=ip;
    }
    c->cursor=s;
}
