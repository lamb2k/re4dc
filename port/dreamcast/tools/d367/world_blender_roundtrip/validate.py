#!/usr/bin/env python3
"""Reproduce Build11 public host/Blender gates and a compact evidence receipt."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time

import fixtures
import package as codec
import sidecars

HERE=Path(__file__).resolve().parent
DC=codec.TOOLS.parent
REPO=DC.parents[1]
ARCHIVE_SHA256='8d3be07d2bc412b502c6bfe3cfe3e22195a4164076867da987ce148d73c27946'
ARCHIVE_URL='https://download.blender.org/release/Blender4.4/blender-4.4.3-linux-x64.tar.xz'
DEPENDENCIES=[codec.TOOLS/'convert_room_bins.py',codec.TOOLS/'mesh_lod.py',
    codec.TOOLS/'ps2_world_r4im.py',codec.TOOLS/'assetpipe/r4im.py',
    codec.TOOLS/'d367/visibility23/metadata.py',codec.TOOLS/'d367/scenery19/scdd_compile.py',
    DC/'room/instanced_mesh.hpp',DC/'room/room_package.hpp']


def file_sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def git(*args):
    return subprocess.check_output(['git',*args],cwd=REPO)


def source_hashes():
    return {p.relative_to(REPO).as_posix():file_sha(p) for p in
            sorted(list(HERE.glob('*.py'))+DEPENDENCIES)}


def run(command,work,name,env=None):
    log=work/(name+'.log');start=time.perf_counter()
    with log.open('wb') as output:
        process=subprocess.Popen([str(x) for x in command],cwd=REPO,stdout=output,
                                 stderr=subprocess.STDOUT,env=env)
        pid,status,usage=os.wait4(process.pid,0)
        process.returncode=os.waitstatus_to_exitcode(status)
    result=dict(exit_code=process.returncode,elapsed_seconds=round(time.perf_counter()-start,6),
                peak_resident_kib=usage.ru_maxrss,user_seconds=round(usage.ru_utime,6),
                system_seconds=round(usage.ru_stime,6),log_sha256=file_sha(log))
    if process.returncode:
        raise RuntimeError(name+' failed:\n'+log.read_text(errors='replace')[-12000:])
    return result


def host_adoption(work,inputs):
    (work/'kos').mkdir()
    (work/'kos/fs.h').write_text('#pragma once\ntypedef int file_t;\n#define FILEHND_INVALID (-1)\n')
    source=work/'runtime-adopt.cpp'
    source.write_text('''#include "instanced_mesh.hpp"
#include <fstream>
#include <iterator>
#include <vector>
#include <cstdio>
int main(int argc,char** argv){
 for(int i=1;i<argc;++i){std::ifstream f(argv[i],std::ios::binary);
  std::vector<unsigned char>b((std::istreambuf_iterator<char>(f)),{});
  re4dc::room::MeshPackage p;
  if(!p.adopt(b.data(),unsigned(b.size()),true,true)){std::fprintf(stderr,"reject %s\\n",p.error());return 1;}
  std::printf("RUNTIME_ADOPT_OK meshes=%u parts=%u meshlets=%u vertices=%u\\n",
    p.header().mesh_count,p.header().part_count,p.header().meshlet_count,p.header().vertex_count);
 }return 0;}
''')
    exe=work/'runtime-adopt'
    compile_result=run(['g++','-std=c++17','-O2','-Wall','-Wextra','-I'+str(DC/'room'),'-I'+str(work),
                        source,'-o',exe],work,'runtime-adopt-compile')
    execution=run([exe,*inputs],work,'runtime-adopt')
    return dict(compiler=subprocess.check_output(['g++','--version']).decode().splitlines()[0],
        fixture_sha256=file_sha(source),compile=compile_result,execution=execution,
        scope='actual current MeshPackage::adopt(..., true, true) on host; file_t/FILEHND_INVALID '
            'declarations stubbed because no KOS filesystem function is called; no SH4 timing')


def baseline_control(work,baseline):
    original=git('show',baseline+':'+(codec.TOOLS/'convert_room_bins.py').relative_to(REPO).as_posix())
    codec.require(original==(codec.TOOLS/'convert_room_bins.py').read_bytes(),'baseline converter changed')
    path=work/'baseline-convert.py';path.write_bytes(original)
    spec=importlib.util.spec_from_file_location('b11_baseline_converter',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    before=fixtures.converter_files(module);after=fixtures.converter_files()
    codec.require(before==after,'unchanged existing converter output')
    stable={}
    for path in DEPENDENCIES:
        key=path.relative_to(REPO).as_posix();data=git('show',baseline+':'+key)
        codec.require(data==path.read_bytes(),'existing dependency changed '+key)
        stable[key]=codec.sha(data)
    return dict(baseline_commit=git('rev-parse',baseline).decode().strip(),
        existing_dependencies_byte_identical=stable,baseline_fixture_hashes=sidecars.hashes(before),
        current_fixture_hashes=sidecars.hashes(after),builder_integration='absent: explicit standalone tools only')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--blender',type=Path,required=True)
    ap.add_argument('--archive',type=Path,required=True)
    ap.add_argument('--work',type=Path,required=True,help='new directory, preferably under /tmp')
    ap.add_argument('--receipt',type=Path,required=True)
    ap.add_argument('--baseline',default='HEAD')
    args=ap.parse_args()
    args.blender=args.blender.resolve();args.archive=args.archive.resolve();args.work=args.work.resolve()
    codec.require(not args.work.exists(),'refuse existing validation directory')
    codec.require(file_sha(args.archive)==ARCHIVE_SHA256,'official Blender archive SHA256 mismatch')
    binary=file_sha(args.blender);initial_sources=source_hashes()
    version=subprocess.check_output([str(args.blender),'--background','--version']).decode()
    codec.require('Blender 4.4.3' in version and 'build hash: 802179c51ccc' in version,'wrong Blender build')
    args.work.mkdir(parents=True)
    baseline=baseline_control(args.work,args.baseline)
    host=run([sys.executable,HERE/'test_identity.py'],args.work,'host-controls')
    suites=[];outputs=[]
    env=dict(os.environ,BLENDER_USER_CONFIG=str(args.work/'blender-config'),
             BLENDER_USER_SCRIPTS=str(args.work/'blender-scripts'))
    common=[args.blender,'--background','--factory-startup','--disable-autoexec','--python-exit-code','1']
    for name,make in [('complete_v2',fixtures.complete_files),('legacy_v1',lambda:fixtures.complete_files(True)),
                       ('existing_converter',fixtures.converter_files)]:
        source=args.work/(name+'-input');destination=args.work/(name+'-output');blend=args.work/(name+'.blend')
        begin=time.perf_counter();files=make();fixtures.write(source,files)
        conversion_seconds=time.perf_counter()-begin
        codec.require(file_sha(args.blender)==binary,'Blender executable changed before run')
        import_result=run([*common,'--python',HERE/'blender_bridge.py','--','import',
            '--source',source,'--blend',blend],args.work,name+'-import',env)
        export_result=run([*common,'--python',HERE/'blender_bridge.py','--','export',
            '--source',source,'--blend',blend,'--out',destination],args.work,name+'-export',env)
        actual=sidecars.inventory(destination)
        codec.require(files==actual,'Blender roundtrip byte mismatch '+name)
        codec.require(files==sidecars.inventory(source),'Blender changed its input bundle')
        codec.require(file_sha(args.blender)==binary,'Blender executable changed during run')
        d=codec.decode(files['ps2-world.re4mesh'],files['ps2-world.r4pw'])
        suites.append(dict(name=name,input_bytes=sum(map(len,files.values())),blend_bytes=blend.stat().st_size,
            output_bytes=sum(map(len,actual.values())),identity=True,fixture_build_seconds=round(conversion_seconds,6),
            counts={key:len(d[key]) for key in ('meshes','parts','meshlets','vertices','placements','clusters','levels')},
            files={key:dict(bytes=len(value),sha256=codec.sha(value)) for key,value in sorted(files.items())},
            import_process=import_result,export_process=export_result))
        outputs.append(destination/'ps2-world.re4mesh')
    mutation_result=run([*common,'--python',HERE/'blender_controls.py','--',
        '--source',args.work/'complete_v2-input','--blend',args.work/'complete_v2.blend',
        '--report',args.work/'mutations.json'],args.work,'blender-mutations',env)
    mutations=json.loads((args.work/'mutations.json').read_text())
    adoption=host_adoption(args.work,outputs)
    codec.require(initial_sources==source_hashes(),'source files changed during validation')
    codec.require(file_sha(args.blender)==binary,'Blender executable changed after validation')
    receipt=dict(build=11,status='PASS identity foundation; no geometry or performance acceptance',
        base_commit=git('rev-parse','HEAD').decode().strip(),
        blender=dict(version='4.4.3',build_hash='802179c51ccc',archive_url=ARCHIVE_URL,
            release_manifest_url='https://download.blender.org/release/Blender4.4/blender-4.4.3.sha256',
            archive_sha256=ARCHIVE_SHA256,executable_sha256=binary,pre_post_executable_identity=True),
        source_sha256=initial_sources,host_platform=dict(system=platform.system(),machine=platform.machine(),
            python=platform.python_version(),timing_scope='host wall/user/system including process startup; RSS is per child peak KiB'),
        host_controls=dict(test_methods=11,process=host),blender_roundtrips=suites,
        blender_mutations=dict(process=mutation_result,**mutations),runtime_host_admission=adoption,
        absent_tool_off_identity=baseline,companion_registry=sidecars.REGISTRY,
        proof_scope='Known proof records are structurally checked and byte-identical. Existing geometric proofs, '
            'external SAT/source provenance and compiled guards are inherited, not certified. Unknown formats fail closed.',
        runtime_delta=dict(sh4_cycles=0,loads=0,stores=0,architectural_32byte_lines=0,
            executable_bytes=0,static_stack_bytes=0,main_ram_bytes=0,vram_bytes=0,
            modeled_world_cpu_frame_delta_ms=0.0,
            basis='No runtime/build integration changes; every accepted output file is byte-identical.'),
        performance_claim='None. Host conversion measurements are not Dreamcast timing; no real r101 assets or captures used.')
    args.receipt.parent.mkdir(parents=True,exist_ok=True)
    args.receipt.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
    print(json.dumps(dict(status='PASS',roundtrips=len(suites),blender_mutations=mutations['controls'],
        host_test_methods=11,receipt=str(args.receipt))))


if __name__=='__main__':main()
