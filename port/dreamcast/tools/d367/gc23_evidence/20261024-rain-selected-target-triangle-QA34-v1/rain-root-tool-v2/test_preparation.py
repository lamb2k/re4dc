#!/usr/bin/env python3
"""Host-only controls for the future selected-target harness. No compiler/SDK."""
import copy, hashlib, importlib.util, json, pathlib, resource, struct, tempfile
import matrix, readback
CHECKS=0
def yes(value):
 global CHECKS
 assert value;CHECKS+=1
def reject(call):
 global CHECKS
 try:call()
 except (ValueError,FileNotFoundError,KeyError,struct.error):CHECKS+=1;return
 raise AssertionError('negative accepted')
def elf(path, *, text=b'\x09\x00\x0b\x00', debug=b'old', record=False, align=32, record_size=128, reloc=1, symval=0, machine=42, symbind=1, symvisibility=0, symtype=2, symsize=4, textaddress=0, reloc_symbol=1):
 # Minimal actual ELF32/SH bytes, not a fake Elf class.
 names=['','.text','.bss','.debug_info','.strtab','.symtab','.rela.text','.shstrtab'];shnames=b'\0';offsets={}
 for name in names[1:]:offsets[name]=len(shnames);shnames+=name.encode()+b'\0'
 strings=b'\0defined\0external\0re4dc_rain_r10c_diag\0'
 syms=bytes(16)+struct.pack('<IIIBBH',1,symval,symsize,(symbind<<4)|symtype,symvisibility,1)+struct.pack('<IIIBBH',9,0,0,0x12,0,0)
 if record:syms+=struct.pack('<IIIBBH',18,0,record_size,0x11,0,2)
 values=[b'',text,b'',debug,strings,syms,struct.pack('<IIi',0,(reloc_symbol<<8)|reloc,0),shnames]
 kinds=[0,1,8,1,3,2,4,3];flags=[0,6,3,0,0,0,0,0];links=[0,0,0,0,0,4,5,0];infos=[0,0,0,0,0,1,1,0];aligns=[0,2,align,1,1,4,4,1];ents=[0,0,0,0,0,16,12,0]
 blob=bytearray(bytes(52));rows=[]
 for i,data in enumerate(values):
  while len(blob)%max(1,aligns[i]):blob.append(0)
  off=len(blob);blob+=data;size=(128 if record else 0) if i==2 else len(data)
  rows.append((offsets.get(names[i],0),kinds[i],flags[i],textaddress if i==1 else 0,off,size,links[i],infos[i],aligns[i],ents[i]))
 while len(blob)%4:blob.append(0)
 sho=len(blob)
 for row in rows:blob+=struct.pack('<IIIIIIIIII',*row)
 blob[:16]=b'\x7fELF\x01\x01\x01'+bytes(9)
 struct.pack_into('<HHIIIIIHHHHHH',blob,16,1,machine,1,0,0,sho,0x10,52,0,0,40,len(rows),7)
 path.write_bytes(blob)

def main():
 resource.setrlimit(resource.RLIMIT_AS,(128*1024**2,128*1024**2))
 with tempfile.TemporaryDirectory(prefix='rain-diag24-prep-controls-',dir='/dev/shm') as tmp:
  root=pathlib.Path(tmp)
  for name,opts in [('a',{}),('debug',{'debug':b'changed source lines'}),('text',{'text':b'\x08\x00\x0b\x00'}),('reloc',{'reloc':2}),('symbol',{'symval':2}),('record',{'record':True}),('align',{'record':True,'align':16}),('size',{'record':True,'record_size':124}),('arch',{'machine':3})]:elf(root/name,**opts)
  # All changed functions stay inside the eight-byte .text extent and are
  # deliberately NOT the symbol referenced by the relocation.
  stable=dict(text=b'\x09\x00\x0b\x00'*2,reloc_symbol=2)
  elf(root/'abi-base',**stable);abi=readback.Elf(root/'abi-base')
  for name,change in [('value',{'symval':2}),('binding',{'symbind':2}),('visibility',{'symvisibility':2}),('type',{'symtype':1}),('size',{'symsize':2}),('address',{'textaddress':16})]:
   elf(root/('abi-'+name),**dict(stable,**change))
   reject(lambda name=name:readback.require_identity(abi,readback.Elf(root/('abi-'+name))))
  elf(root/'abi-unique-base',**dict(stable,symbind=10,symtype=1))
  elf(root/'abi-unique-value',**dict(stable,symbind=10,symtype=1,symval=2))
  unique=readback.Elf(root/'abi-unique-base')
  reject(lambda:readback.require_identity(unique,unique))
  reject(lambda:readback.require_identity(unique,readback.Elf(root/'abi-unique-value')))
  elf(root/'abi-debug',**dict(stable,debug=b'unrelated debug bytes'))
  readback.require_identity(abi,readback.Elf(root/'abi-debug'));yes(True)
  yes('cc1' in matrix.TOOLS)
  toolpins={'tools':{name:matrix.pin(path) for name,path in matrix.TOOLS.items()}}
  yes(matrix.validate_tools(toolpins))
  missing=copy.deepcopy(toolpins);del missing['tools']['cc1'];reject(lambda:matrix.validate_tools(missing))
  changed=copy.deepcopy(toolpins);changed['tools']['cc1']['sha256']='0'*64;reject(lambda:matrix.validate_tools(changed))

  a=readback.Elf(root/'a');debug=readback.Elf(root/'debug')
  yes(a.raw!=debug.raw);readback.require_identity(a,debug);yes(True)
  for name in ('text','reloc','symbol'):reject(lambda name=name:readback.require_identity(a,readback.Elf(root/name)))
  yes(readback.Elf(root/'record').record(True)['bytes']==128)
  reject(lambda:a.record(True));reject(lambda:readback.Elf(root/'record').record(False))
  for name in ('align','size'):reject(lambda name=name:readback.Elf(root/name).record(True))
  reject(lambda:readback.Elf(root/'arch'))
  (root/'truncated').write_bytes((root/'a').read_bytes()[:-1]);reject(lambda:readback.Elf(root/'truncated'))
  p={'base':matrix.BASE,'source':matrix.SOURCE,'runtime':matrix.RUNTIME,'case_names':[x[0] for x in matrix.case_specs()],'tools':{'cxx':{'path':'kos-c++'}},'normal':{f'{f}/{u}':{'argv':['-O1']+(['-O2'] if u=='espgen44' else [])+(['-DRE4DC_RAIN_R10C_DC=1'] if f and u=='filter06' else [])+['-MMD','-MP','-c','../../../src/game/'+u+'.cpp','-o','old.o']} for f in (0,1) for u in matrix.UNITS}}
  for f in (0,1):
   for u in matrix.UNITS:
    for d in (None,'absent','0','1'):
     a=matrix.argv(p,f,u,d,'new.o');yes(a.count('-fstack-usage')==1);yes(a[a.index('-o')+1]=='new.o');yes(sum(x.startswith('-DRE4DC_RAIN_R10C_DIAG=') for x in a)==(d in('0','1')))
  reject(lambda:matrix.argv(p,0,'filter06','01','x'))
  yes(matrix.deps('out: a.h \\\n b.h\na.h:\n')==['a.h','b.h'])
  reject(lambda:matrix.deps('bad'))
  yes(matrix.source_rel('../../../include/a.h')=='include/a.h');reject(lambda:matrix.source_rel('../../../../escape'))
  pp=root/'pins.json';pp.write_text(json.dumps(p));output='/dev/shm/rain-diag24-target-hosttestonly'
  g={'kind':'ROOT_SELECTED_SH4_GRANT','source':matrix.SOURCE,'base':matrix.BASE,'pins_sha256':matrix.digest(pp.read_bytes()),'output':output,'jobs':1,'address_space_bytes':matrix.CAP,'owned_output_bytes':matrix.CAP,'command_seconds':60,'wall_seconds':360,'case_names':p['case_names'],'authorized':True,'grant_id':'HOST_TEST_ONLY_NOT_AUTHORITY'}
  matrix.grant_check(p,pp,g,output);yes(True)
  for key,value in [('source','bad'),('base','bad'),('pins_sha256','bad'),('output',output+'x'),('jobs',4),('address_space_bytes',matrix.CAP+1),('owned_output_bytes',matrix.CAP+1),('command_seconds',61),('wall_seconds',361),('authorized',False),('grant_id',''),('case_names',p['case_names'][:-1])]:
   bad=copy.deepcopy(g);bad[key]=value;reject(lambda bad=bad:matrix.grant_check(p,pp,bad,output))
  for name in ('/tmp/rain-diag24-target-hosttestonly','/dev/shm/rain-diag24-target-x','/dev/shm/rain-diag24-target-../../x',str(root)):reject(lambda name=name:matrix.path_check(name))
  oversize=root/'oversize';oversize.touch()
  with oversize.open('r+b') as f:f.truncate(matrix.CAP+1)
  reject(lambda:matrix.cap_check(root));oversize.unlink()
  reject(lambda:matrix.execute(p,pp,g,output))
  symlink=root/'link';symlink.symlink_to(root/'a');reject(lambda:matrix.cap_check(root));symlink.unlink()
  # Exercise full readback inventory and on/off reports with actual ELF bytes.
  provider=root/'provider';elf(provider)
  pins={'source':matrix.SOURCE,'base':matrix.BASE,'case_names':p['case_names'],'provider':{'path':str(provider),'sha256':readback.sha(provider)},'runtime':matrix.RUNTIME,'limits':matrix.LIMITS}
  for case,commit,f,d in matrix.case_specs():
   q=root/'cases'/case;q.mkdir(parents=True)
   for suffix in ('.log','.stdout'):(root/(case+'-partial-link'+suffix)).write_text('retained log\n')
   for unit in matrix.UNITS:
    for phase in ('deps','includes','compile','strip','disassemble'):
     (root/(case+'-'+unit+'-'+phase+'.log')).write_text('retained log\n')
     if phase in ('compile','strip'):(root/(case+'-'+unit+'-'+phase+'.stdout')).write_text('retained stdout\n')
    for suffix in ('.o','-nodebug.o'):elf(q/(unit+suffix),record=d=='1' and unit=='filter06')
    for suffix in ('.d','.ii','-argv.json','-before.d','-before-pins.json','-actual-pins.json'):(q/(unit+suffix)).write_text('retained artifact\n')
    (q/(unit+'.su')).write_text('unit.cpp:1:1:void function()\t32\tstatic\n')
    (q/(unit+'-disassembly.txt')).write_text('ocbwb @r4\n')
   elf(q/'pair.o',record=d=='1')
  actual_pins_sha=matrix.digest((json.dumps(pins,indent=2)+'\n').encode())
  actual_grant={'kind':'ROOT_SELECTED_SH4_GRANT','authorized':True,'source':pins['source'],'base':pins['base'],'pins_sha256':actual_pins_sha,'output':str(root),'jobs':1,'address_space_bytes':matrix.CAP,'owned_output_bytes':matrix.CAP,'command_seconds':60,'wall_seconds':360,'case_names':pins['case_names'],'grant_id':'HOST_TEST_ONLY_SYNTHETIC'}
  for rel,value in [('RESERVED.json',{'pins_sha256':actual_pins_sha,'grant':actual_grant}),('grant.json',actual_grant),('pins.json',pins)]:
   (root/rel).write_text(json.dumps(value,indent=2)+'\n')
  for rel in ('environment-bootstrap.log','environment.nul'):(root/rel).write_text('retained allocation\n')
  run={'pins_sha256':actual_pins_sha,'grant_id':actual_grant['grant_id'],'runtime':matrix.RUNTIME,'limits':matrix.LIMITS,'source':matrix.SOURCE,'base':matrix.BASE,'selected_compilation_complete':True,'case_names':p['case_names'],'artifacts':{}}
  for q in root.rglob('*'):
   if q.is_file():run['artifacts'][str(q.relative_to(root))]={'bytes':q.stat().st_size,'sha256':readback.sha(q)}
  def save(): (root/'matrix-result.json').write_text(json.dumps(run))
  save();report=readback.check(root,pins);yes(len(report['off_identity'])==8);yes(len(report['objects'])==12);yes(report['opcodes_require_root_review'])
  badpins=copy.deepcopy(pins);badpins['provider']['sha256']='bad';reject(lambda:readback.check(root,badpins))
  oldsha=run['pins_sha256'];run['pins_sha256']='bad';save();reject(lambda:readback.check(root,pins));run['pins_sha256']=oldsha
  oldid=run['grant_id'];run['grant_id']='wrong';save();reject(lambda:readback.check(root,pins));run['grant_id']=oldid
  key='new-f0-dabsent-filter06-includes.log';kept=run['artifacts'].pop(key);save();reject(lambda:readback.check(root,pins));run['artifacts'][key]=kept
  key='cases/new-f0-dabsent/filter06.su';kept=run['artifacts'].pop(key);save();reject(lambda:readback.check(root,pins));run['artifacts'][key]=kept
  run['selected_compilation_complete']=False;save();reject(lambda:readback.check(root,pins));run['selected_compilation_complete']=True
  q=root/'cases/new-f0-dabsent/filter06.o';q.write_bytes(q.read_bytes()+b'drift');save();reject(lambda:readback.check(root,pins))
  # Future launcher wiring is inspected, not run or sourced.
  shell=(pathlib.Path(__file__).parent/'run-matrix.sh').read_text()
  yes(shell.index('matrix.py\" check')<shell.index('d367-buildslot.sh'))
  yes(shell.index('matrix.py\" reserve')<shell.index('source /root/work/lanes/rain-diag24/port/dreamcast/kos-env.sh'))
  yes('ulimit -v 262144' in shell and '380 bash' in shell and 'flock 7' in shell)
 print(json.dumps({'host_preparation_checks':CHECKS,'SDK_invocations':0,'scope':'synthetic ELF readback, argument/grant/path/resource/protocol controls; no SH4 generated evidence'},indent=2))
if __name__=='__main__':main()
