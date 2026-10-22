from pathlib import Path
import subprocess,hashlib,json,re,ctypes,struct,random
D=Path('/root/probe/codex-backface-sh4zam-review/port/dreamcast/tools/d367/backface_sh4zam_review')
O=Path('/root/probe/lanes/route/out-bfasabcfc8a3pair01crW')
objdump='/opt/toolchains/dc/sh-elf/bin/sh-elf-objdump'
log=(O/'build.log').read_text()
out={'source':'abcfc8a3d','scope':'Actual C target objects and compile commands; host numeric witness only','objects':{}}
for kind in ['native_static','native_actor_fast']:
 p=O/'obj/platform'/f'{kind}.o'
 dis=subprocess.check_output([objdump,'-d','-C',str(p)],text=True)
 sections=re.split(r'(?=Disassembly of section )',dis)
 relevant=[s for s in sections if 'bf::strip<' in s[:1500] or 'Part::bf_send(' in s[:1500]]
 # only retain exact backface functions, rather than unrelated transform FMA.
 (D/f'FINAL-C-{kind}.dis').write_text('\n'.join(relevant))
 cmds=[s for s in log.splitlines() if ' -c ' in s and f'platform/{kind}.cpp' in s]
 out['objects'][kind]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'command':cmds,'backface_sections':len(relevant),'fmac_in_backface_sections':sum(s.count('\tfmac\t') for s in relevant)}
# Finite binary32 almost-collinear triangle witness. FMA operands are exact
# binary32; double products fit 48 bits and cancellation fits a double here.
f=lambda x:struct.unpack('<f',struct.pack('<f',x))[0]
b=lambda x:f'{struct.unpack("<I",struct.pack("<f",x))[0]:08x}'
lib=ctypes.CDLL('libm.so.6');fm=lib.fmaf;fm.argtypes=[ctypes.c_float]*3;fm.restype=ctypes.c_float
rng=random.Random(0xface23)
for i in range(100000):
 bx=f(rng.uniform(32,640));by=f(rng.uniform(32,480));cx=f(bx*2);cy=f(by*2)
 # exact collinear projected triangle can have cancelling rounded products
 # but one product has a nonzero exact residual under FMAC.
 p=f(by*cx);strict=f(f(bx*cy)-p);target=fm(bx,cy,-p)
 if (strict<0)!=(target<0):
  out['finite_witness']={'A':[0,0],'B':[bx,by],'C':[cx,cy],'strict_area':strict,'target_area':target,'strict_hex':b(strict),'target_hex':b(target),'first_fmul_hex':b(p),'cull2_even_strict_front':strict<0,'cull2_even_target_front':target<0,'iteration':i};break
assert 'finite_witness' in out
(D/'FINAL-C-ARITHMETIC.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items() if k!='objects'},indent=2))
print({k:(v['sha256'],v['backface_sections'],v['fmac_in_backface_sections'],len(v['command'])) for k,v in out['objects'].items()})
