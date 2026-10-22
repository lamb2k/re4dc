#!/usr/bin/env python3
"""One shared actual Package/stream CRC1 cohort gate; no per-asset builds."""
from pathlib import Path
import hashlib,json,subprocess,sys,zlib,struct
T=Path(__file__).resolve().parents[4];sys.path.insert(0,str(T/'dreamcast/tests'))
# ROOT below is the established Dreamcast tree, not an extracted/reimplemented Package parser.
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'tests'))
import test_ps2_room_r4im_texcrc as fixture

def main():
 out=Path(sys.argv[1]);r=json.loads((out/'conversion-receipt.json').read_text());H=out/'host';H.mkdir();(H/'dc/pvr').mkdir(parents=True);(H/'kos').mkdir()
 stubs={
 'dc/pvr.h':'#pragma once\nusing pvr_ptr_t=void*;\n#define PVR_TXRFMT_RGB565 (1U<<27)\n#define PVR_TXRFMT_ARGB1555 0U\n#define PVR_TXRFMT_ARGB4444 (2U<<27)\n#define PVR_TXRFMT_VQ_ENABLE (1U<<30)\n#define PVR_TXRFMT_TWIDDLED 0U\n#define PVR_TXRFMT_NONTWIDDLED (1U<<26)\nint pvr_wait_ready();int pvr_wait_render_done();\n',
 'dc/pvr/pvr_mem.h':'#include <cstddef>\nvoid* pvr_mem_malloc(std::size_t);void pvr_mem_free(void*);\n',
 'dc/pvr/pvr_txr.h':'#include <cstddef>\n#define PVR_TXRLOAD_16BPP 0\nvoid pvr_txr_load_ex(const void*,void*,unsigned,unsigned,unsigned);void pvr_txr_load(const void*,void*,std::size_t);\n',
 'kos/fs.h':'#pragma once\n#include <sys/types.h>\nusing file_t=int;\n#define FILEHND_INVALID -1\nint fs_open(const char*,int);int fs_close(int);ssize_t fs_total(int);void* fs_mmap(int);ssize_t fs_read(int,void*,size_t);off_t fs_seek(int,off_t,int);\n',
 'kos.h':'#include <kos/fs.h>\n#include <fcntl.h>\n#include <cstdint>\nstd::uint64_t timer_us_gettime64();\n'}
 for name,text in stubs.items():(H/name).write_text(text)
 reader='#include <cstring>\n'+fixture.READER.replace('a.close();s.close();','if(streamed)std::printf("format:%08x\\n",re4dc::texture::pvr_format(*s.textures()));a.close();s.close();')
 (H/'reader.cpp').write_text(reader);source=ROOT/'room';commands={};outputs={}
 paths=[out/x['relative_path']for x in r['selected']]
 for mode in('on','off'):
  exe=H/('reader-'+mode);cmd=['g++','-std=c++17','-O1','-g0','-fsanitize=address,undefined','-fno-omit-frame-pointer','-DRE4DC_CAST_MIPMAP='+('1'if mode=='on'else'0'),'-DRE4DC_TEX_RESIDENT=1','-DRE4DC_TEX_PAYLOAD_CRC=1','-DRE4DC_STORAGE_BOUNCE_BYTES=16384','-I'+str(H),'-I'+str(source),str(H/'reader.cpp'),str(source/'texture_package.cpp'),str(source/'room_storage.cpp'),'-o',str(exe)]
  built=subprocess.run(cmd,capture_output=True,timeout=45);(H/('compile-'+mode+'.txt')).write_bytes(built.stdout+built.stderr);assert built.returncode==0,built.stderr.decode()
  run=subprocess.run([str(exe),*map(str,paths)],capture_output=True,text=True,timeout=30);(H/('output-'+mode+'.txt')).write_text(run.stdout);(H/('stderr-'+mode+'.txt')).write_text(run.stderr);assert run.returncode==0 and not run.stderr,(mode,run.returncode,run.stderr[:3000])
  lines=run.stdout.splitlines()
  if mode=='on':assert len(lines)==2*len(paths) and all(lines[2*i]=='ok|ok'and int(lines[2*i+1].split(':')[1],16)&0xc0000000==0xc0000000 for i in range(len(paths)))
  else:assert len(lines)==len(paths) and all(line!='ok|ok'for line in lines)
  commands[mode]=cmd;outputs[mode]=dict(cases=len(paths),result='all_adopt_and_stream_crc1_pass_VQmip'if mode=='on'else'all_mip_disabled_reject',exe_sha256=hashlib.sha256(exe.read_bytes()).hexdigest())
 # Shared corruption controls one representative per dimension, same strict on-reader process.
 corrupt=[]
 for side in(32,64,128,256):
  row=next(x for x in r['selected']if x['physical'][0]==side);blob=(out/row['relative_path']).read_bytes()
  for kind in('legacy_texel_only_crc','payload_bit','truncated'):
   b=bytearray(blob)
   if kind=='legacy_texel_only_crc':struct.pack_into('<I',b,36,zlib.crc32(b[144:])&0xffffffff);assert b!=blob
   elif kind=='payload_bit':b[-1]^=1
   else:b=b[:-1]
   f=H/('negative-'+str(side)+'-'+kind+'.re4tex');f.write_bytes(b);corrupt.append(dict(path=str(f),dimension=side,kind=kind))
 run=subprocess.run([str(H/'reader-on'),*[x['path']for x in corrupt]],capture_output=True,text=True,timeout=15);(H/'output-negative.txt').write_text(run.stdout);(H/'stderr-negative.txt').write_text(run.stderr);assert run.returncode==0 and not run.stderr and len(run.stdout.splitlines())==len(corrupt)and all(x!='ok|ok'for x in run.stdout.splitlines())
 sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
 report=dict(status='PASS_ACTUAL_PACKAGE_SHARED_BATCH_HOST_ONLY',positive_cases=len(paths),strict_adopt_and_stream_CRC1=True,mip_disabled_rejections=len(paths),negative_cases=corrupt,outputs=outputs,commands=commands,source_pins={str(p):sha(p)for p in(source/'texture_package.cpp',source/'texture_package.hpp',source/'room_storage.cpp',source/'room_storage.hpp',Path(fixture.__file__))},source_stub_explicit=True,limits=['One build perON/OFF variant and oneprocessperwholecohort, no perassetcompile/launch loops.','Actual runtime Package/room_storage code, hostPOSIX filesystem/malloc/stubPVR upload boundaries.','No GPU allocation/highwater/rendering/guest/performance/physical Dreamcast acceptance.'])
 (out/'host-gate.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k]for k in('status','positive_cases','mip_disabled_rejections')}))
if __name__=='__main__':main()