"""Compile only builtin offsetof constants using the exact retained Make-expanded em.cpp command."""
from pathlib import Path
import argparse,hashlib,json,os,shlex,struct,subprocess
ap=argparse.ArgumentParser();ap.add_argument('--tree',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--scratch',type=Path,required=True);ap.add_argument('--source',required=True);args=ap.parse_args()
root=args.tree;output=args.output;tmp=args.scratch;tmp.mkdir(exist_ok=False);source=args.source
assert subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()==source
assert not subprocess.check_output(['git','-C',str(root),'status','--porcelain'],text=True).strip()
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
lib=Path('/root/work/kos-re4dc-d367/lib/dreamcast/libkallisti.a');before=sha(lib)
commands=[s for s in (output/'build.log').read_text().splitlines() if s.startswith('kos-c++ ') and ' -c ../../../src/game/em.cpp ' in s]
assert len(commands)==1
original=shlex.split(commands[0]);assert original[0]=='kos-c++'
bridge=root/'port/dreamcast/game/parts_bridge.cpp';bridge_source=bridge.read_text();start=bridge_source.index('template<class T> struct alignas(32) Chunk');end=bridge_source.index('static_assert(sizeof(Chunk<cParts>)',start);decls=bridge_source[start:end]
fields=[('magic','0x33494241u'),('schema','3u'),('pointer_bytes','sizeof(void*)'),('u32_bytes','sizeof(u32)'),('manager.sizeof','sizeof(cEmMgr)'),('manager.pArray','__builtin_offsetof(cEmMgr,pArray)'),('manager.nArray','__builtin_offsetof(cEmMgr,nArray)'),('manager.stride','__builtin_offsetof(cEmMgr,size)'),('manager.pAlive','__builtin_offsetof(cEmMgr,pAlive)'),('manager.Guid','__builtin_offsetof(cEmMgr,Guid)'),('manager.pArrayPush','__builtin_offsetof(cEmMgr,pArrayPush)'),('manager.pAlivePush','__builtin_offsetof(cEmMgr,pAlivePush)'),('manager.nArrayPush','__builtin_offsetof(cEmMgr,nArrayPush)'),('actor.sizeof','sizeof(cEm)'),('actor.be_flag','__builtin_offsetof(cEm,be_flag)'),('actor.pNext','__builtin_offsetof(cEm,pNext)'),('actor.serial','__builtin_offsetof(cEm,serial)'),('actor.id','__builtin_offsetof(cEm,id)'),('actor.type','__builtin_offsetof(cEm,type)'),('actor.kindid','__builtin_offsetof(cEm,kindid)'),('actor.emset_no','__builtin_offsetof(cEm,emset_no)'),('actor.pos','__builtin_offsetof(cEm,pos)'),('actor.stat','__builtin_offsetof(cEm,stat)'),('actor.pMotion','__builtin_offsetof(cEm,pMotion)'),('actor.motState','__builtin_offsetof(cEm,motState)'),('actor.frame','__builtin_offsetof(cEm,frame)'),('actor.frameMax','__builtin_offsetof(cEm,frameMax)'),('roomdata.sizeof','sizeof(cRoomData)'),('roomdata.num','__builtin_offsetof(cRoomData,num)'),('roomdata.pSaveBuf','__builtin_offsetof(cRoomData,pSaveBuf)'),('roomdata.pSave','__builtin_offsetof(cRoomData,pSave)'),('roomsave.sizeof','sizeof(RoomSave)'),('global.SF1','__builtin_offsetof(GlobalWork,Status_flg)+sizeof(u32)'),('global.Frame_cnt','__builtin_offsetof(GlobalWork,Frame_cnt)'),('global.room_id','__builtin_offsetof(GlobalWork,room_id)')]
fields += [('pool.sizeof','sizeof(Pool<cEm>)'),('chunk.sizeof','sizeof(Chunk<cEm>)')]+[('pool.'+name,'__builtin_offsetof(Pool<cEm>,'+name+')') for name in ['chunks','capacity','bytes','peak','chunks_count','reclaims','failures','heap','handle']]+[('chunk.'+name,'__builtin_offsetof(Chunk<cEm>,'+name+')') for name in ['next','first','count','bytes']]+[('target.WORKAT_INLINE','RE4DC_WORKAT_INLINE')]
cpp='#include "em.h"\n#include "room_data.h"\n#include "global.h"\n'+decls+'\nstatic_assert(sizeof(unsigned int)==4);\nextern "C" __attribute__((used,section(".rodata.aud23_abi"))) const unsigned int aud23_abi_v3[] = {\n'+',\n'.join('  '+expr+' /* '+name+' */' for name,expr in fields)+'\n};\n'
(tmp/'probe.cpp').write_text(cpp)
command=[];skip=False
for i,arg in enumerate(original):
 if skip:skip=False;continue
 if arg in ['-c','-o']:skip=True;continue
 if arg in ['-MMD','-MP']:continue
 command.append('/root/work/kos-re4dc-d367/utils/build_wrappers/kos-c++' if i==0 else arg)
command+=['-g0','-c',str(tmp/'probe.cpp'),'-o',str(tmp/'probe.o')]
proc=subprocess.run(command,cwd=root/'port/dreamcast/game',text=True,capture_output=True)
(tmp/'compile.log').write_text(proc.stdout+proc.stderr);assert proc.returncode==0,proc.stderr
prefix='/opt/toolchains/dc/sh-elf/bin/sh-elf-'
subprocess.run([prefix+'objcopy','--dump-section','.rodata.aud23_abi='+str(tmp/'layout.bin'),str(tmp/'probe.o')],check=True)
data=(tmp/'layout.bin').read_bytes();assert len(data)==4*len(fields)
values=struct.unpack('<'+'I'*len(fields),data);layout={name:v for (name,_),v in zip(fields,values)}
assert layout['magic']==0x33494241 and layout['schema']==3 and layout['pointer_bytes']==4 and layout['u32_bytes']==4
assert before==sha(lib)
elf=output/'re4dc-game.elf';record={'source':source,'elf':str(elf),'elf_sha256':sha(elf),'original_make_command':original,'actual_probe_command':command,'make_build_log_sha256':sha(output/'build.log'),'probe_source_sha256':sha(tmp/'probe.cpp'),'probe_object_sha256':sha(tmp/'probe.o'),'layout_bytes_sha256':sha(tmp/'layout.bin'),'sdk_library_sha256_before':before,'sdk_library_sha256_after':sha(lib),'compiler_version':subprocess.check_output(['/opt/toolchains/dc/sh-elf/bin/sh-elf-g++','--version'],text=True).splitlines()[0],'compiler_sha256':sha('/opt/toolchains/dc/sh-elf/bin/sh-elf-g++'),'layout':layout,'fields':fields,'parts_bridge_sha256':sha(bridge),'exact_native_declarations_sha256':hashlib.sha256(decls.encode()).hexdigest(),'exact_native_declarations':decls,'parts_budget_header':str(output/'obj/parts-budget.h'),'parts_budget_header_sha256':sha(output/'obj/parts-budget.h'),'parts_budget_header_text':(output/'obj/parts-budget.h').read_text(),'scope':'One isolated RAM TU, compile only under exact retained Make-expanded em.cpp flags; no full build/link/SDK mutation/guest.'}
(tmp/'target-abi-receipt.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({'compiler':record['compiler_version'],'layout':layout,'receipt':str(tmp/'target-abi-receipt.json')},indent=2))
