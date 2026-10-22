#!/usr/bin/env python3
"""Compare actual candidate lookup against the frozen linear implementation."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

DRIVER = r'''
#include <cassert>
#include <cstdio>
#include "old/world_rect_bind.h"
#include "new/world_rect_bind.h"
unsigned cases=0,max_iterations=0;
void check(const unsigned* a,bool enabled) {
    re4dc::rect21::Descriptor n{a[4],a[5],a[6],a[7],a[8],a[9],a[10]};
    re4dc::linear21::Descriptor o{a[4],a[5],a[6],a[7],a[8],a[9],a[10]};
    float nu=-13.25f,nv=29.5f,ou=nu,ov=nv;
    bool nr=re4dc::rect21::adapt(a[0],a[1],a[2],a[3],n,nu,nv,enabled);
    bool old=re4dc::linear21::adapt(a[0],a[1],a[2],a[3],o,ou,ov,enabled);
    assert(nr==old && nu==ou && nv==ov);
    if(!nr)assert(nu==-13.25f && nv==29.5f);
    ++cases;
    unsigned lo=0,hi=re4dc::rect21::qualified_count,iterations=0;
    while(lo<hi) {
        ++iterations;unsigned mid=lo+(hi-lo)/2;
        const auto& r=re4dc::rect21::qualified[mid];
        if(r.crc<a[0] || (r.crc==a[0] && r.fnv<a[1]))lo=mid+1;else hi=mid;
    }
    if(iterations>max_iterations)max_iterations=iterations;
    assert(iterations<=10);
}
int main() {
    for(const auto& r:re4dc::rect21::qualified) {
        const auto& s=r.stored;
        unsigned a[]={r.crc,r.fnv,r.logical_width,r.logical_height,s.width,s.height,s.format,s.flags,s.payload,s.bytes,s.checksum};
        check(a,true);check(a,false);
        for(unsigned i=0;i<11;++i) {
            unsigned saved=a[i];a[i]^=1U;check(a,true);check(a,false);a[i]=saved;
        }
        for(unsigned crc:{0U,0x7fffffffU,0x80000000U,0xffffffffU}) {
            unsigned saved=a[0];a[0]=crc;check(a,true);a[0]=saved;
        }
        for(unsigned fnv:{0U,0x7fffffffU,0x80000000U,0xffffffffU}) {
            unsigned saved=a[1];a[1]=fnv;check(a,true);a[1]=saved;
        }
    }
    std::printf("{\"semantic_comparisons\":%u,\"max_binary_iterations\":%u}\n",cases,max_iterations);
}
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--output', type=Path, required=True)
    a = ap.parse_args()
    a.output.mkdir(exist_ok=False)
    here = Path(__file__).resolve().parent
    rel = 'port/dreamcast/tools/d367/texture_rect21/world_rect_bind.h'
    old = subprocess.check_output(['git', 'show', '0425534d848973c1dae3ab960d0006ac9afcf363:' + rel], text=True)
    for name, header in [('old', old.replace('re4dc::rect21', 're4dc::linear21')), ('new', (here / 'world_rect_bind.h').read_text())]:
        target = a.output / name
        target.mkdir()
        (target / 'world_rect_bind.h').write_text(header)
        (target / 'scoped_representations.inc').write_bytes((here / 'scoped_representations.inc').read_bytes())
    (a.output / 'probe.cpp').write_text('#include <initializer_list>\n' + DRIVER)
    cmd = ['g++', '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror', '-fsanitize=undefined,address', str(a.output / 'probe.cpp'), '-o', str(a.output / 'probe')]
    subprocess.run(cmd, check=True)
    result = json.loads(subprocess.check_output([str(a.output / 'probe')], text=True))
    result.update(status='HOST_SEMANTIC_EQUIVALENCE_ONLY_NO_TARGET_TIMING', compiler=subprocess.check_output(['g++', '--version'], text=True).splitlines()[0], command=cmd,
                  sources={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in [here / 'world_rect_bind.h', here / 'scoped_representations.inc', here / 'world_rect_provenance.h', here / 'provenance_certificates.inc', here / 'compose650.py', here / 'qualify650.py']})
    (a.output / 'receipt.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
