#!/usr/bin/env python3
"""Actual-source R4PV size/quantization controls; no table/data emitted."""
import argparse
import hashlib
import json
import re
import resource
import subprocess
import tempfile
from pathlib import Path


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--source-tree',required=True,type=Path);ap.add_argument('--out',required=True,type=Path);a=ap.parse_args()
    if a.out.exists():raise ValueError('Preserve existing receipt')
    resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,256*1024*1024))
    native=a.source_tree/'port/dreamcast/game/platform/native_static.cpp';fmt=native.parent/'include/pvs23_format.hpp'
    text=native.read_text();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    if sha(native)!='e23dda292ae37aff409bd66228c0a2edf80c27536ba477b9b9a51c1cc19113eb':raise ValueError('Unreviewed current native source')
    head=re.search(r'struct Head \{.*?\};',text[text.index('namespace pvs {\nstruct Head'):],re.S)[0]
    expression='size>=sizeof(Head) && size<=262144U && !(size&31U)'
    if text.count(expression)!=1:raise ValueError('Loader size expression changed')
    body=r'''
#include <cassert>
#include <cstdio>
#include <cstring>
#include <limits>
#include "pvs23_format.hpp"
HEAD
bool allocation(unsigned size){return EXPRESSION;}
unsigned checks=0;
#define CHECK(x) do{++checks;assert(x);}while(0)
int main(){
 static_assert(sizeof(Head)==64);
 auto test=[&](unsigned nx,unsigned nz,float cell,bool expected,unsigned expected_bytes){
  Head h{};h.nx=nx;h.nz=nz;h.cell=cell;h.x0=-10000;h.z0=-36000;h.ninst=318;h.nsets=1;h.ncells=1;h.set_bytes=40;
  const unsigned bytes=(64+8*nx*nz+40+31)&~31U;CHECK(bytes==expected_bytes);
  CHECK(re4dc::pvs23::layout(h,bytes));CHECK(allocation(bytes)==expected);
  std::printf("%u %u %.0f %u %u\n",nx,nz,cell,bytes,unsigned(allocation(bytes)));
  return h;
 };
 auto h=test(22,25,2000,true,4512);
 test(88,100,500,true,70528);
 test(176,200,250,false,281728); // format valid, actual allocation bound refuses
 test(128,128,250,true,131200); // local32m window; outside remains unsupported
 test(1,1,500,true,128);test(1,1,250,true,128);
 h.cell=0;CHECK(!re4dc::pvs23::layout(h,4512));h.cell=-1;CHECK(!re4dc::pvs23::layout(h,4512));
 h.cell=std::numeric_limits<float>::infinity();CHECK(!re4dc::pvs23::layout(h,4512));
 h.cell=std::numeric_limits<float>::quiet_NaN();CHECK(!re4dc::pvs23::layout(h,4512));
 h.cell=500;h.nx=65536;h.nz=2;CHECK(!re4dc::pvs23::layout(h,1048704));
 CHECK(!allocation(262176));CHECK(allocation(262144));CHECK(!allocation(4513));
 std::printf("checks=%u\n",checks);
}
'''.replace('HEAD',head).replace('EXPRESSION',expression)
    with tempfile.TemporaryDirectory(prefix='iv23-cell-layout-',dir='/dev/shm') as work:
        work=Path(work);src=work/'layout.cpp';exe=work/'layout';src.write_text(body)
        subprocess.run(['g++','-std=c++17','-O1','-fsanitize=undefined','-fno-sanitize-recover=all','-I'+str(fmt.parent),str(src),'-o',str(exe)],check=True,capture_output=True,text=True)
        run=subprocess.run([str(exe)],check=True,capture_output=True,text=True)
    out=dict(kind='Existing R4PV1 finer-grid representability and loader extent controls only',tool_sha256=sha(Path(__file__)),source={str(p.relative_to(a.source_tree)):sha(p) for p in (native,fmt)},actual_loader_expression=expression,stdout=run.stdout,source_profile='fb254 core with owned reviewed PVS guards',heap_extra_bytes=1056,single_set_extent_only=True,certificate_admission=False,geometry_proof=False,actual_renderer_admission=False,data_emitted=False,peak_child_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open('x') as f:json.dump(out,f,indent=1);f.write('\n')
    print(json.dumps(out))

if __name__=='__main__':main()
