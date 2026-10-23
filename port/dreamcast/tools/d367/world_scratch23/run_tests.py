"""Small host controls; no game build, guest or assets."""
from pathlib import Path
import importlib.util, subprocess, tempfile
T=Path(__file__).resolve().parent; D=T.parents[2]; G=D/'game'
def run(args,**kwargs):return subprocess.check_output(list(map(str,args)),text=True,**kwargs)
def main():
 with tempfile.TemporaryDirectory(prefix='world-scratch23-') as tmp:
  o=Path(tmp)
  flags=['-std=c++17','-O2','-Wall','-Wextra','-Werror','-DRE4DC_WORLD_SCRATCH=1','-DRE4DC_WORLD_SCRATCH_HOST=1','-I'+str(G),'-I'+str(D/'room'),'-I'+str(G/'platform/include'),'-I'+str(T/'stubs')]
  print(run(['g++',*flags,G/'world_scratch.cpp',T/'test_scratch.cpp','-o',o/'host']).strip());print(run([o/'host']).strip())
  print(run(['g++',*flags,G/'world_scratch.cpp',T/'test_selector.cpp','-o',o/'selector']).strip());run([o/'selector'])
  runtime_flags=[x for x in flags if x!='-DRE4DC_WORLD_SCRATCH_HOST=1']+['-DRE4DC_WORLD_SCRATCH_RUNTIME_TEST=1','-DRE4DC_DBG_WARP=1']
  run(['g++',*runtime_flags,G/'world_scratch.cpp',T/'test_runtime.cpp','-o',o/'runtime']);run([o/'runtime'])
  for arm in range(5):run([o/'runtime',arm])
  for define,name in [([], 'default'),(['-DRE4DC_WORLD_SCRATCH=0'],'zero')]:
   run(['g++','-std=c++17','-O2',*define,'-c',G/'world_scratch.cpp','-o',o/(name+'.o')])
  assert (o/'default.o').read_bytes()==(o/'zero.o').read_bytes()
  assert not run(['nm',o/'default.o']).strip()
 spec=importlib.util.spec_from_file_location('audit_image',T/'audit_image.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 assert m.section(' 28 .ocram 00002000 7c001000 7c001000 00000964 2**5')['bytes']==8192
 for size,address,align in [('00002100','7c001000','5'),('00002000','7dfff000','5'),('00002000','7c001000','2')]:
  try:m.section(f' 28 .ocram {size} {address} 7c001000 00000964 2**{align}')
  except ValueError:pass
  else:raise AssertionError('accepted bad final section')
 assert 'projected_records' in m.check_symbols('7c001000 00002000 d (anonymous namespace)::projected_records')
 for symbols in ['7c001000 00002000 d foreign','7c001000 00001000 d projected_records','7c001000 00002000 d projected_records\n7c001020 00000020 d peer']:
  try:m.check_symbols(symbols)
  except ValueError:pass
  else:raise AssertionError('accepted conflicting owner')
 # Evaluate actual make fragment, target-specific flags and object dependency.
 text='TARGET=sample.elf\nOBJDIR=obj\nPLATFORM_OBJS=\ninclude '+str(G/'worldscratch.mk')+'\n.PHONY: inspect\ninspect:\n\t@echo objects=$(PLATFORM_OBJS)\nobj/platform/native_ui.o:\n\t@echo flags=$(PLATFORM_CPPFLAGS)\n'
 with tempfile.TemporaryDirectory(prefix='world-scratch-make-') as tmp:
  p=Path(tmp)/'Makefile';p.write_text(text)
  base=['make','--no-print-directory','-f',p,'inspect']
  assert 'world_scratch.o' not in run(base)
  cfg=['WORLD_SCRATCH=1','PS2_WORLD_DRAW=1','PS2_WORLD_MESH=1','MESH_FASTPATH=1','MESH_DIRECT=1','PVR_STREAM=1','CPU_BACKFACE=0','NATIVE_STATIC=1','NATIVE_MESH=1','D349_RENDERER_STACK=1']
  assert 'obj/world_scratch.o' in run(base+cfg)
  for bad in [['WORLD_SCRATCH=2'],cfg+['CPU_BACKFACE=1'],cfg+['MESH_FASTPATH=0']]:
   assert subprocess.run(base+bad,stdout=subprocess.PIPE,stderr=subprocess.PIPE).returncode!=0
 print('PASS: zero/default empty runtime object, linker-audit rejection controls and make admission')
if __name__=='__main__':main()
