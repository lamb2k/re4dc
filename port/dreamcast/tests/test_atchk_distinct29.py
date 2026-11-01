#!/usr/bin/env python3
"""Compile the production at_mod candidate path with distinct body notes."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
PRELUDE = r'''
#include <cassert>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <new>
#include <vector>
#include <algorithm>
using u32 = uintptr_t;
using u16 = uint16_t;
using u8 = uint8_t;
using f32 = float;
extern "C" void re4dc_log(const char*, ...) {}
static unsigned builds, collections;
'''
LAYOUT = r'''
struct cAtariInfo {
    u8 prefix[0x10];
    AtRadius m_radius2;
    u8 middle[6];
    AtFlag16 m_flag;
};
static_assert(offsetof(cAtariInfo,m_radius2)==0x10,"radius wrapper owner");
static_assert(offsetof(cAtariInfo,m_flag)==0x1a,"flag wrapper owner");
struct cEm { cEm* pNext; cAtariInfo atari; };
'''
CASES = r'''
static cEm pool[704]{};
static std::vector<cEm*> expected(cEm* head) {
    std::vector<cEm*> out;
    for (; head; head=head->pNext)
        if ((head->atari.m_flag&0x200) && head->atari.m_radius2!=0.0f)
            out.push_back(head);
    return out;
}
static void link(std::vector<cEm*>& nodes) {
    for (unsigned i=0;i<nodes.size();i++)
        nodes[i]->pNext=i+1<nodes.size()?nodes[i+1]:nullptr;
}
static int query(AtList& list, AtCand& cand, std::vector<cEm*>& nodes, u32 gen) {
    static int queries;
    ++queries;
    cEm* out[ATCHK_MAX];
    cEm* head=nodes.empty()?nullptr:nodes[0];
    int n=atchkCandidates(&cand,&list,head,gen,out);
    auto want=expected(head);
    if (want.size()>ATCHK_MAX) assert(n==-1);
    else { if(n!=int(want.size())) fprintf(stderr,"query %d reader %d n=%d want=%zu dirty=%u invalid=%u\n",queries,cand.consumer,n,want.size(),atcDirtyN,atcDirtyInvalid);
           assert(n==int(want.size())); assert(std::equal(want.begin(),want.end(),out)); }
    return n;
}
static void reset_body(cEm* p, bool eligible) {
    p->atari.m_flag=eligible?0x200:0;
    p->atari.m_radius2=1.0f;
}
int main() {
    std::vector<cEm*> em, obj;
    for (int i=0;i<90;i++) { em.push_back(&pool[i]); reset_body(&pool[i],i%3==0); }
    for (int i=100;i<190;i++) { obj.push_back(&pool[i]); reset_body(&pool[i],i%4==0); }
    link(em); link(obj);
    AtList le={0,0,-1}, lo={0,0,-1};
    AtCand ce={0,0,0,-1,ATC_EM}, co={0,0,0,-1,ATC_OBJ};
    u32 eg=11,og=29;
    query(le,ce,em,eg); query(lo,co,obj,og);
    assert(atcDirtyN==0 && atcDirtyInvalid==0);

    // Hundreds of historical writes to one body occupy one pending entry.
    for (int i=0;i<257;i++) pool[1].atari.m_flag^=0x200;
    assert(atcDirtyN==1 && atcDirtyInvalid==0);
    assert(atcDirtyPending[0]==(ATC_EM|ATC_OBJ));
    unsigned before=collections;
    query(le,ce,em,eg);
#if RE4DC_ATCHK_CACHE == 1
    assert(collections==before);
#endif
    assert(atcDirtyN==1 && atcDirtyPending[0]==ATC_OBJ);
    // An intermediate query must see the eligible state before a return.
    pool[1].atari.m_flag^=0x200;
    query(lo,co,obj,og); query(le,ce,em,eg);
    assert(atcDirtyN==0 && atcDirtyInvalid==0);
    pool[3].atari.m_radius2=0;
    pool[3].atari.m_radius2=1;
    query(le,ce,em,eg); query(lo,co,obj,og);
    // Mixed insertions and removals are applied in source list order.
    for (int i=10;i<50;i++) pool[i].atari.m_flag^=0x200;
    before=collections; query(le,ce,em,eg);
#if RE4DC_ATCHK_CACHE == 1
    assert(collections==before);
#endif
    query(lo,co,obj,og);

    // A stale object reader must not force an active enemy reader to fall back.
    for (int i=0;i<65;i++) {
        pool[i].atari.m_flag^=0x200;
        query(le,ce,em,eg);
    }
    assert(atcDirtyInvalid==ATC_OBJ);
    assert(atcDirtyN==0);
    before=collections; query(le,ce,em,eg);
#if RE4DC_ATCHK_CACHE == 1
    assert(collections==before);
#endif
    query(lo,co,obj,og);
    assert(atcDirtyInvalid==0 && atcDirtyN==0);

    // More than 64 distinct changes without either reader: both must recollect.
    for (int i=0;i<65;i++) pool[i].atari.m_flag^=0x200;
    assert(atcDirtyInvalid==(ATC_EM|ATC_OBJ));
    query(le,ce,em,eg);
    assert(atcDirtyInvalid==ATC_OBJ);
    pool[1].atari.m_flag^=0x200;
    query(le,ce,em,eg); // a new change after the enemy rebuild is visible
    query(lo,co,obj,og);
    assert(atcDirtyInvalid==0 && atcDirtyN==0);

    // A dead but still listed body can change eligibility; a noted address
    // absent between list members is skipped safely, never dereferenced.
    pool[7].atari.m_flag=0; query(le,ce,em,eg);
    em.erase(em.begin()+8); link(em); query(le,ce,em,++eg);
    pool[8].atari.m_flag^=0x200;
#if RE4DC_ATCHK_CACHE == 1
    before=collections;
#endif
    query(le,ce,em,eg);
#if RE4DC_ATCHK_CACHE == 1
    assert(collections==before); // generation-bound list proves nonmembership
#endif
    query(lo,co,obj,og);
    em.insert(em.begin()+8,&pool[8]); link(em); query(le,ce,em,++eg);
    std::swap(em[2],em[41]); link(em); query(le,ce,em,++eg);
    // Retire and reconstruct in the same address, with manager generation bump.
    cEm* reused=em[2];
    em.erase(em.begin()+2); link(em); query(le,ce,em,++eg);
    reused->~cEm(); new (reused) cEm{}; reset_body(reused,true);
    em.insert(em.begin()+2,reused); link(em); query(le,ce,em,++eg);
    query(lo,co,obj,og);

    // Candidate capacity refusal keeps notes until a successful collection.
    for (int i=0;i<97;i++) { pool[i].atari.m_flag=0x200; pool[i].atari.m_radius2=1; }
    em.clear(); for (int i=0;i<97;i++) em.push_back(&pool[i]); link(em);
    query(le,ce,em,++eg); // 97 eligible: source refusal
    assert(ce.n==-1);
    pool[96].atari.m_flag=0;
    query(le,ce,em,eg); // 96 eligible: successful retention
    query(lo,co,obj,og);
    assert(ce.n==96);

    // An oversized alive list is not a successful cache refresh. Its notes
    // remain pending until the list shrinks and a source collection succeeds.
    em.clear(); for (int i=350;i<671;i++) { reset_body(&pool[i],i%8==0); em.push_back(&pool[i]); }
    link(em); query(le,ce,em,++eg);
    pool[364].atari.m_flag^=0x200;
    assert(atcDirtyN!=0 || (atcDirtyInvalid&ATC_EM));
    query(le,ce,em,eg);
    assert(atcDirtyN!=0 || (atcDirtyInvalid&ATC_EM));
    em.resize(90); link(em); query(le,ce,em,++eg);
    query(lo,co,obj,og);
    assert(atcDirtyN==0 && atcDirtyInvalid==0);

#if RE4DC_ATCHK_CACHE == 2
    assert(atcMis==0);
    // Negative control: an unnoted field write is found by the production
    // source-order comparison and never accepted as a cache hit.
    unsigned mismatch=atcMis;
    em[2]->atari.m_flag.v^=0x200;
    query(le,ce,em,eg);
    assert(atcMis==mismatch+1);
#endif
    puts("PASS distinct29: production candidates, wrappers, two cursors, boundaries, overflow, lifetime, order");
}
'''


class DistinctDirtyTest(unittest.TestCase):
    def test_zero_matches_absent_source(self):
        source = (ROOT / "src/game/at_mod.cpp").read_text()
        header = (ROOT / "include/atariInfo.h").read_text()
        wrappers = header[header.index('extern "C" u32 re4dc_atari_seq;'):
                          header.index('#define RE4DC_AT_FLAG16')]
        collect = source[source.index('#define ATCHK_MAX'):
                         source.index('#if defined(RE4DC_ATCHK_LIST)')]
        begin = source.index('#if defined(RE4DC_ATLIST_512)')
        helpers = source[begin:source.index('static int atchkCollectEm(', begin)] + '\n#endif\n'
        with tempfile.TemporaryDirectory() as tmp:
            cpp = Path(tmp) / "off.cpp"
            cpp.write_text(PRELUDE + wrappers + LAYOUT + collect + helpers)
            cmd = ["g++", "-std=c++11", "-E", "-P", "-DRE4DC_ATCHK_LIST=1",
                   "-DRE4DC_ATCHK_CACHE=2", str(cpp)]
            absent = subprocess.check_output(cmd)
            zero = subprocess.check_output(cmd + ["-DRE4DC_ATCHK_DISTINCT29=0"])
            self.assertEqual(absent, zero)

    def test_production_cache(self):
        source = (ROOT / "src/game/at_mod.cpp").read_text()
        header = (ROOT / "include/atariInfo.h").read_text()
        wrappers = header[header.index('extern "C" u32 re4dc_atari_seq;'):
                          header.index('#define RE4DC_AT_FLAG16')]
        collect = source[source.index('#define ATCHK_MAX'):
                         source.index('#if defined(RE4DC_ATCHK_LIST)')]
        begin = source.index('#if defined(RE4DC_ATLIST_512)')
        helpers = source[begin:source.index('static int atchkCollectEm(', begin)] + '\n#endif\n'
        for name in ('atListBuild(AtList* L, cEm* head, u32 gen)',
                     'atchkCollect(cEm* head, cEm** out)',
                     'atchkCollectList(const AtList* L, int N, cEm** out)'):
            marker = ('static int ' if not name.startswith('atListBuild') else 'static int ') + name + '\n{'
            target = collect if name.startswith('atchkCollect(') else helpers
            self.assertIn(marker, target)
            target = target.replace(marker, marker + '\n    ++' +
                                    ('builds' if name.startswith('atListBuild') else 'collections') + ';', 1)
            if name.startswith('atchkCollect('): collect = target
            else: helpers = target
        sanitizer = os.environ.get("ATCHK_SANITIZE") == "1"
        with tempfile.TemporaryDirectory() as tmp:
            cpp = Path(tmp) / "fixture.cpp"
            cpp.write_text(PRELUDE + wrappers + LAYOUT + collect + helpers + CASES)
            for mode in (1, 2):
                exe = Path(tmp) / f"distinct-{mode}"
                cmd = ["g++", "-std=c++11", "-O1" if sanitizer else "-O2", "-g",
                       "-Wall", "-Wextra", "-Wno-missing-field-initializers",
                       "-Wno-unused-variable", "-Wno-unused-but-set-variable", "-DRE4DC_ATCHK_DISTINCT29=1",
                       "-DRE4DC_ATCHK_LIST=1", f"-DRE4DC_ATCHK_CACHE={mode}",
                       str(cpp), "-o", str(exe)]
                if sanitizer:
                    cmd += ["-fsanitize=address,undefined", "-fno-omit-frame-pointer"]
                subprocess.run(cmd, check=True)
                subprocess.run([str(exe)], check=True)


if __name__ == "__main__":
    unittest.main()
