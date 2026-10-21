#!/usr/bin/env python3
"""Emit snapshot structure offsets with the selected target compiler/actual flags."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--repo',type=Path,required=True)
    p.add_argument('--preprocessing',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--objcopy',default='/opt/toolchains/dc/sh-elf/bin/sh-elf-objcopy')
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    source=a.out/'layout.cpp';headers=['global.h','main_mem.h','model.h','cam_ctrl.h','camera.h']
    names=['room','frame','player_pos','player_ang','camera','camera_param','camera_mat','camera_vmat','camera_proj','CameraControl_size','Camera_size']
    expressions=['__builtin_offsetof(GlobalWork,room_id)','__builtin_offsetof(GlobalWork,Frame_cnt)',
                 '__builtin_offsetof(cCoord,pos)','__builtin_offsetof(cCoord,ang)','__builtin_offsetof(CameraControl,camera)',
                 '__builtin_offsetof(Camera,param)','__builtin_offsetof(Camera,mat)','__builtin_offsetof(Camera,v_mat)',
                 '__builtin_offsetof(Camera,ProjMat)','sizeof(CameraControl)','sizeof(Camera)']
    source.write_text(''.join('#include "'+str(a.repo/'include'/h)+'"\n' for h in headers)+
                     'extern "C" const unsigned offsets[] __attribute__((used,section(".rodata.benchlayout"))) = { '+', '.join(expressions)+' };\n')
    proof=json.loads(a.preprocessing.read_text());command=proof['units']['platform/native_actor_fast.cpp']['preprocess_command']
    command=[arg for arg in command if arg not in ['-E','-dM','platform/native_actor_fast.cpp']]+['-c',str(source),'-o',str(a.out/'layout.o')]
    with (a.out/'compile.log').open('x') as log:subprocess.run(command,cwd=a.repo/'port/dreamcast/game',stdout=log,stderr=log,check=True)
    subprocess.run([a.objcopy,'-O','binary','-j','.rodata.benchlayout',str(a.out/'layout.o'),str(a.out/'layout.bin')],check=True)
    data=(a.out/'layout.bin').read_bytes()
    if len(data)!=4*len(names):raise ValueError('target layout extent differs')
    sha=lambda path:hashlib.sha256(Path(path).read_bytes()).hexdigest()
    result={'source':subprocess.check_output(['git','-C',str(a.repo),'rev-parse','HEAD'],text=True).strip(),
            'target_compiler_flags':command,'layout':dict(zip(names,struct.unpack('<'+'I'*len(names),data))),
            'headers':{h:sha(a.repo/'include'/h) for h in headers},'layout_source_sha256':sha(source),
            'layout_object_sha256':sha(a.out/'layout.o'),'compiler_sha256':sha(command[0]),
            'preprocessing_receipt_sha256':sha(a.preprocessing),
            'scope':'target-compiled offsets only; no game program or original object changed'}
    with (a.out/'layout.json').open('x') as output:json.dump(result,output,indent=2);output.write('\n')
    print(json.dumps(result['layout']))

if __name__=='__main__':main()
