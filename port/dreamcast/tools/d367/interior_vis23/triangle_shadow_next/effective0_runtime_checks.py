#!/usr/bin/env python3
"""Actual runtime gate/receipts, all95 raw choices, semantic mutants and OFF CPP."""
import argparse,ast,hashlib,json,resource,subprocess,tempfile
from pathlib import Path

def text_constant(path,name):
 t=ast.parse(path.read_text())
 return next(n.value.value for n in ast.walk(t) if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id==name for x in n.targets) and isinstance(n.value,ast.Constant))

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--source-tree',required=True,type=Path);ap.add_argument('--audit',required=True,type=Path);ap.add_argument('--out',required=True,type=Path);a=ap.parse_args()
 if a.out.exists():raise ValueError('Preserve prior controls')
 resource.setrlimit(resource.RLIMIT_AS,(268435456,268435456));here=Path(__file__).resolve().parent;inc=a.source_tree/'port/dreamcast/game/platform/include';header=inc/'pvs23_proof.hpp';runtime=inc/'pvs23_runtime.inc';nonempty=a.source_tree/'port/dreamcast/room/nonempty_lod.hpp';original=runtime.read_text();records=[]
 old=subprocess.check_output(['git','-C',str(a.source_tree),'show','18caa03ca:port/dreamcast/game/platform/include/pvs23_runtime.inc'],text=True)
 protected='extern "C" int re4dc_pvs23_frame_guard'
 if old[old.index(protected):]!=original[original.index(protected):]:raise ValueError('Protected frame/observer/commit/cut context changed')
 if hashlib.sha256(header.read_bytes()).hexdigest()!='1881d1d814fdc7bb787991a2cd6f67ebab293d5c2a7efa42cdd515fb07821ba4':raise ValueError('Panel/numeric/cap changed')
 audit=json.loads(a.audit.read_text());actual=[r for r in audit['physical_clusters'] if r['eligible'] and r['declared_level_count']>1 and r['effective_levels']==[0] and r['invariant_faces']>0]
 if len(actual)!=95 or sum(r['invariant_faces'] for r in actual)!=8168 or not all(r['meshlet_counts'][0]>0 and not any(r['meshlet_counts'][1:]) for r in actual):raise ValueError('Frozen actual source cohort changed')
 prefix=text_constant(here/'duplicate_panel_checks.py','fixture').split('unsigned checks=0;')[0]
 prefix=prefix.replace('unsigned vertex_count=3;','unsigned vertex_count=4;')
 prefix=prefix.replace('struct Level{unsigned first_meshlet=0,meshlet_count=1;} l;','struct Level{unsigned first_meshlet=0,meshlet_count=1;}; Level ls[8]; FakePackage(){for(auto& x:ls)x.meshlet_count=0;ls[0].meshlet_count=1;}')
 prefix=prefix.replace('const Level* levels()const{return &l;}','const Level* levels()const{return ls;}')
 controls=text_constant(here/'union_receipt_checks.py','controls')
 guard='defined(RE4DC_PS2_PVS_EFFECTIVE0_SOURCES) && RE4DC_PS2_PVS_EFFECTIVE0_SOURCES == 1 && defined(RE4DC_PS2_WORLD_NONEMPTY_LOD) && RE4DC_PS2_WORLD_NONEMPTY_LOD == 1 && RE4DC_MESH_LOD == 1 && RE4DC_PS2_WORLD_MESH == 1'
 before='CHECK(guard());ps2w.package.c.level_count=2;CHECK(!guard());ps2w.package.c.level_count=1;'
 after='CHECK(guard());ps2w.package.c.level_count=2;\n#if '+guard+'\n CHECK(guard());ps2w.package.ls[1].meshlet_count=1;CHECK(!guard());ps2w.package.ls[1].meshlet_count=0;ps2w.package.ls[0].meshlet_count=0;CHECK(!guard());ps2w.package.ls[0].meshlet_count=1;CHECK(guard());\n#else\n CHECK(!guard());\n#endif\n ps2w.package.c.level_count=1;'
 if controls.count(before)!=1:raise ValueError('Actual receipt fixture anchor')
 controls=controls.replace(before,after)
 extra=''
 for index,row in enumerate(actual):
  counts=row['meshlet_counts'];extra+=' {FakePackage::Level levels['+str(len(counts))+']{};'
  extra+=''.join('levels['+str(j)+'].meshlet_count='+str(n)+'U;' for j,n in enumerate(counts))
  extra+='for(unsigned raw=0;raw<'+str(len(counts))+'U;++raw)CHECK(re4dc::room::nonempty_lod(levels,'+str(len(counts))+'U,raw)==0U);\n#if '+guard+'\n CHECK(proof23::effective0_source(levels,'+str(len(counts))+'U));\n#endif\n }\n'
 extra+='#if '+guard+'\n FakePackage::Level empty[8]{};for(auto& x:empty)x.meshlet_count=0;CHECK(!proof23::effective0_source(empty,8));CHECK(!proof23::effective0_source(empty,0));CHECK(!proof23::effective0_source<FakePackage::Level>(nullptr,2));empty[0].meshlet_count=1;for(unsigned n=2;n<=8;++n){CHECK(proof23::effective0_source(empty,n));for(unsigned raw=0;raw<n;++raw)CHECK(re4dc::room::nonempty_lod(empty,n,raw)==0);for(unsigned higher=1;higher<n;++higher){empty[higher].meshlet_count=1;CHECK(!proof23::effective0_source(empty,n));CHECK(re4dc::room::nonempty_lod(empty,n,higher)==higher);empty[higher].meshlet_count=0;}}\n#endif\n'
 controls=controls.replace(' std::printf(',extra+' std::printf(')
 cert='const Panel panels[]={{0,0,0,0,0,{0,1,2,3,2,1}}};\nconst Certificate certificates[]={{0x10d,1,1,1,1,0xd202ef8dU,0,1,32,panels,{1000,1000,1000}}};\n'
 configs=[('undefined',None,1,1,1),('off-fallback0',0,0,1,1),('off-fallback1',0,1,1,1),('on-missing-fallback',1,None,1,1),('on-fallback0',1,0,1,1),('on-no-lod',1,1,0,1),('on-no-world',1,1,1,0),('forged-option2',2,1,1,1),('forged-fallback2',1,2,1,1),('on-valid',1,1,1,1)]
 with tempfile.TemporaryDirectory(prefix='iv23-effective0-runtime-',dir='/dev/shm') as temp:
  temp=Path(temp);(temp/header.name).write_bytes(header.read_bytes());(temp/'nonempty_lod.hpp').write_bytes(nonempty.read_bytes());(temp/'cert.inc').write_text(cert);(temp/'fixture.cpp').write_text('#include <cstdio>\n#include "nonempty_lod.hpp"\n'+prefix+controls)
  def invoke(label,source,option,fallback,lod,world,mutation=False,compare_old=False):
   flags=['-DRE4DC_MESH_LOD='+str(lod),'-DRE4DC_PS2_WORLD_MESH='+str(world)]
   if option is not None:flags+=['-DRE4DC_PS2_PVS_EFFECTIVE0_SOURCES='+str(option)]
   if fallback is not None:flags+=['-DRE4DC_PS2_WORLD_NONEMPTY_LOD='+str(fallback)]
   (temp/runtime.name).write_text(source);exe=temp/label;cmd=['g++','-std=c++17','-O1','-fsanitize=undefined','-fno-sanitize-recover=all','-DRE4DC_PVS23_CERTIFICATES="cert.inc"','-I'+str(temp)]+flags+[str(temp/'fixture.cpp'),'-o',str(exe)]
   build=subprocess.run(cmd,capture_output=True,text=True)
   if build.returncode:raise ValueError('Control compilation failed '+label+build.stderr)
   run=subprocess.run([str(exe)],capture_output=True,text=True)
   if (run.returncode==0)==mutation:raise ValueError('Unexpected '+label+run.stdout+run.stderr)
   if mutation and ('Assertion' not in run.stderr or 'failed' not in run.stderr):raise ValueError('Mutant failure is not intended assertion '+label)
   equal=None
   if compare_old:
    cpp=['g++','-std=c++17','-E','-P','-DRE4DC_PVS23_CERTIFICATES="cert.inc"','-I'+str(temp)]+flags+[str(temp/'fixture.cpp')]
    new_cpp=subprocess.check_output(cpp);(temp/runtime.name).write_text(old);old_cpp=subprocess.check_output(cpp);equal=new_cpp==old_cpp
    if not equal:raise ValueError('OFF preprocessor changed '+label)
   records.append(dict(label=label,returncode=run.returncode,stdout=run.stdout,stderr=run.stderr,old_preprocessed_identical=equal))
  for label,option,fallback,lod,world in configs:invoke(label,original,option,fallback,lod,world,compare_old=option in (None,0))
  mutations=[('higher-mutant','if(levels[level].meshlet_count)return false;','if(false)return false;',1,1),('base-mutant',' || !levels[0].meshlet_count','',1,1),('fallback-mutant','defined(RE4DC_PS2_WORLD_NONEMPTY_LOD) && RE4DC_PS2_WORLD_NONEMPTY_LOD == 1 && ','',1,0)]
  for label,before,after,option,fallback in mutations:
   expected=2 if label=='fallback-mutant' else 1
   if original.count(before)!=expected:raise ValueError('Mutation anchor changed '+label)
   invoke(label,original.replace(before,after),option,fallback,1,1,mutation=True)
 out=dict(kind='Actual unchanged receipt paths and effective0 source gate host controls',tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),sources={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (runtime,header,nonempty)},actual_clusters=95,actual_faces=8168,all_actual_raw_choices=190,variants=records,protected_context_identical=True,kMaxPanels=16,runtime_admitted_cuts=0,limits=dict(address_space_bytes=268435456,peak_child_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,jobs=1))
 with a.out.open('x') as dst:json.dump(out,dst,indent=1);dst.write('\n')
 print(json.dumps(out))
if __name__=='__main__':main()
