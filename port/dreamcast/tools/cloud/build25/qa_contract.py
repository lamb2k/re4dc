#!/usr/bin/env python3
"""Exercise production AL25 row formatting and QA_LINK part framing on the host."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
DC = HERE.parents[2]
ROOT = DC.parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    qa = DC / 'game/qa_menu.cpp'
    header = DC / 'game/platform/include/actor_light_fast_only.h'
    source = qa.read_text()
    addf = source[source.index('int addf(int at, const char* fmt, ...) __attribute__'):source.index('#if defined(RE4DC_WORLD_SCRATCH)', source.index('int addf(int at, const char* fmt, ...) __attribute__'))]
    start = source.index('#if defined(RE4DC_ACTOR_LIGHT_FAST_ONLY)', source.index('void snap_diag()'))
    rows = source[start:source.index('#endif', start) + len('#endif')]
    start = source.index('void link_send_parts(')
    parts = source[start:source.index('void link_telemetry()', start)]
    fixture = out / 'qa_contract.cpp'
    fixture.write_text(r'''#include <cassert>
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <climits>
#include <string>
#include <vector>
#include "actor_light_fast_only.h"
static char g_diag[4096];
static std::vector<std::string> sent;
static struct { unsigned seq; } g_link{UINT_MAX};
static unsigned long long timer_ms_gettime64() { return UINT_MAX; }
static void link_send_text(const char* p, int n) { assert(n>=0 && n<=1200); sent.emplace_back(p,n); }
// Framing contract with an accepting transport. link28's queue admission/drop
// policy is deliberately outside this Build 25 formatting fixture.
static void re4dc_qalink_send_bulk(const char* p, unsigned n) { link_send_text(p, int(n)); }
extern "C" void re4dc_actor_light25_snapshot(Re4dcActorLight25Stats* s) {
    std::memset(s, 0xff, sizeof(*s)); s->fallback_parts=0;
}
''' + addf + '\nstatic int light_rows() { int a=0;\n' + rows + '\nreturn a; }\n' + parts + r'''
int main() {
    const int n=light_rows();
    assert(n>0 && n<4096 && int(std::strlen(g_diag))==n);
    assert(std::strstr(g_diag,"fallback=0 MUST=0"));
    assert(std::strstr(g_diag,"vcolour=4294967295"));
    assert(std::strstr(g_diag,"diffuse_scale=4294967295"));
    assert(std::strstr(g_diag,"lights_over3=4294967295"));
    assert(std::strstr(g_diag,"probe_decline=4294967295"));
    assert(std::strstr(g_diag,"basis=4294967295"));
    assert(std::strstr(g_diag,"flat=4294967295 multiply=4294967295"));
    unsigned maximum=0, cases=0;
    for(char kind : {'T','D'}) for(unsigned len : {0U,1U,1099U,1100U,1101U,4095U,8191U}) {
        const std::string input(len,'x'); sent.clear();
        link_send_parts(kind,"123456789012345",input.data(),int(input.size()));
        std::string joined;
        for(const auto& d:sent) {
            if(d.size()>maximum)maximum=unsigned(d.size());
            const auto split=d.find('\n'); assert(split!=std::string::npos);
            joined+=d.substr(split+1);
        }
        assert(joined==input); ++cases;
    }
    std::printf("{\"status\":\"PASS\",\"row_bytes\":%d,\"framing_cases\":%u,\"max_datagram_bytes\":%u}\n",n,cases,maximum);
}
''')
    command = ['g++','-std=c++17','-O2','-Wall','-Wextra','-Werror',
               '-DRE4DC_ACTOR_LIGHT_FAST_ONLY=1','-I'+str(header.parent),str(fixture),'-o',str(out/'qa_contract')]
    subprocess.run(command,check=True,capture_output=True)
    result = json.loads(subprocess.check_output([str(out/'qa_contract')],text=True))
    result.update(scope=__doc__, source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (qa,header,Path(__file__))})
    (out/'qa-contract.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
