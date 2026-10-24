#!/usr/bin/env python3
"""Actual unchanged production Panel receipts for a real two-triple transcript.

Synthetic package/cache/scene/material state only. Both triangles use the SAME
cache indices1/2 for the true diagonal. No actual frame/raster/asset admission.
"""
import argparse
import ast
import hashlib
import json
import resource
import subprocess
import tempfile
from pathlib import Path


def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--source-tree',required=True,type=Path);ap.add_argument('--out',required=True,type=Path);a=ap.parse_args()
 if a.out.exists():raise ValueError('Preserve old receipt')
 resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,256*1024*1024))
 here=Path(__file__).resolve().parent;donor=here/'duplicate_panel_checks.py';tree=ast.parse(donor.read_text())
 fixture=next(n.value.value for n in ast.walk(tree) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='fixture' for t in n.targets) and isinstance(n.value,ast.Constant))
 prefix=fixture[:fixture.index('unsigned checks=0;')]
 if prefix.count('unsigned vertex_count=3;')!=1:raise ValueError('Synthetic package anchor')
 prefix=prefix.replace('unsigned vertex_count=3;','unsigned vertex_count=4;')
 controls=r'''
unsigned checks=0;
#define CHECK(x) do{++checks;assert(x);}while(0)
int main(){
 using namespace re4dc::pvsproof;
 Panel panel{0,0,0,0,0,{0,1,2,3,2,1}};
 pvr_vertex_t cache[4]={{10,10,.001f},{10,100,.001f},{100,10,.001f},{100,100,.001f}};
 std::uint8_t codes[4]={0,0x40,0x80,0xc0},both[5]={4,0,1,2,3},first[4]={3,0,1,2},second[4]={3,3,2,1};
 auto sent=[&](const std::uint8_t* stream,unsigned bytes){return panel_sent(panel,cache,codes,4,stream,bytes,2,64);};
 CHECK(sent(both,5));CHECK(!sent(first,4));CHECK(!sent(second,4));CHECK(!sent(both,4));
 codes[3]=16;CHECK(!sent(both,5));codes[3]=0xc0;
 auto original=cache[3];cache[3]=cache[2];CHECK(!sent(both,5));cache[3]=original;
 unsigned char table=0;auto guard=[&](){return re4dc_pvs23_table_guard(0x10d,&table,1,1,1,1);};
 CHECK(guard());ps2w.package.c.level_count=2;CHECK(!guard());ps2w.package.c.level_count=1;
 parts[0].pass=1;CHECK(!guard());parts[0].pass=0;
 parts[0].reserved=1;CHECK(!guard());parts[0].reserved=0;
 placements[0].placement=1;CHECK(!guard());placements[0].placement=0;CHECK(guard());
 auto arm=[&](){CHECK(guard());proof23::valid=true;proof23::checked_frame=frame;proof23::checked_generation=pvs::generation;};
 auto observe=[&](const std::uint8_t* stream,unsigned bytes,unsigned pending[3]){re4dc_pvs23_observe(0,0,0,cache,codes,4,stream,bytes,2,64,pending);};
 auto commit=[&](unsigned pending[3]){unsigned key[6]{};re4dc_pvs23_commit(0,0,pending,key);};
 unsigned pending[3]{};arm();observe(first,4,pending);CHECK(!pending[2]);commit(pending);CHECK(!pvs::can_cut(1));
 arm();observe(second,4,pending);CHECK(!pending[2]);commit(pending);CHECK(!pvs::can_cut(1));
 arm();observe(both,5,pending);CHECK(pending[2]==1);CHECK(!pvs::can_cut(1));commit(pending);CHECK(pvs::can_cut(1));
 arm();observe(both,5,pending);material=false;commit(pending);CHECK(!pvs::can_cut(1));material=true;
 arm();observe(both,5,pending);++scene;commit(pending);CHECK(!pvs::can_cut(1));
 arm();observe(both,5,pending);++frame;commit(pending);CHECK(!pvs::can_cut(1));
 arm();observe(both,5,pending);++pvs::generation;commit(pending);CHECK(!pvs::can_cut(1));
 arm();pending[0]=pending[1]=pending[2]=0;codes[3]=32;observe(both,5,pending);CHECK(!pending[2]);commit(pending);CHECK(!pvs::can_cut(1));codes[3]=0xc0;
 arm();observe(both,5,pending);intact=false;commit(pending);CHECK(!pvs::can_cut(1));intact=true;
 arm();observe(both,5,pending);commit(pending);CHECK(pvs::can_cut(1));proof23::key[0]=1;CHECK(!pvs::can_cut(1));
 std::printf("checks=%u\n",checks);
}
'''
 inc=a.source_tree/'port/dreamcast/game/platform/include';header=inc/'pvs23_proof.hpp';runtime=inc/'pvs23_runtime.inc'
 pins={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (header,runtime)}
 if pins!={'pvs23_proof.hpp':'1881d1d814fdc7bb787991a2cd6f67ebab293d5c2a7efa42cdd515fb07821ba4','pvs23_runtime.inc':'09a05d430e31216570bcce9e7ef6a8c5fde929bd32f4c2b6979a25df967609a0'}:raise ValueError('Unreviewed production sources')
 cert='const Panel panels[]={{0,0,0,0,0,{0,1,2,3,2,1}}};\nconst Certificate certificates[]={{0x10d,1,1,1,1,0xd202ef8dU,0,1,32,panels,{1000,1000,1000}}};\n'
 records=[]
 with tempfile.TemporaryDirectory(prefix='iv23-union-receipt-',dir='/dev/shm') as tmp:
  tmp=Path(tmp);(tmp/'fixture.cpp').write_text('#include <cstdio>\n'+prefix+controls);(tmp/'cert.inc').write_text(cert)
  for label,mutation in [('baseline',None),('missing-triangle-mutant',('if(found!=3U)return false;','if(false)return false;')),('material-mutant',('!re4dc_pvs23_opaque_ready(key,re4dc::vp::kCacheSlots+64U)','false')),('epoch-mutant',('pending[0]!=epoch[0] || pending[1]!=epoch[1] ||','false ||'))]:
   h=header.read_text();r=runtime.read_text()
   if mutation:
    old,new=mutation
    if h.count(old)+r.count(old)!=1:raise ValueError('Mutation anchor changed')
    h=h.replace(old,new);r=r.replace(old,new)
   (tmp/header.name).write_text(h);(tmp/runtime.name).write_text(r);exe=tmp/label
   subprocess.run(['g++','-std=c++17','-O1','-fsanitize=undefined','-fno-sanitize-recover=all','-DRE4DC_PVS23_CERTIFICATES="cert.inc"','-I'+str(tmp),str(tmp/'fixture.cpp'),'-o',str(exe)],check=True,capture_output=True,text=True)
   run=subprocess.run([str(exe)],capture_output=True,text=True)
   if (run.returncode==0)!=(mutation is None):raise ValueError('Unexpected control '+label+' '+run.stdout+run.stderr)
   records.append(dict(label=label,returncode=run.returncode,stdout=run.stdout,stderr=run.stderr,expected='pass' if mutation is None else 'assertion failure'))
 out=dict(kind='Unchanged actual-source two-triangle Panel/receipt controls on synthetic shared-cache transcript',tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),sources=pins,fixture_donor_sha256=hashlib.sha256(donor.read_bytes()).hexdigest(),variants=records,renderer_admission=False,scope='Controlled valid receipt state only; actual target frame/arithmetic/material/raster/source emission unqualified.',limits=dict(address_space_bytes=256*1024*1024,peak_child_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,jobs=1))
 a.out.parent.mkdir(parents=True,exist_ok=True)
 with a.out.open('x') as f:json.dump(out,f,indent=1);f.write('\n')
 print(json.dumps(out))

if __name__=='__main__':main()
