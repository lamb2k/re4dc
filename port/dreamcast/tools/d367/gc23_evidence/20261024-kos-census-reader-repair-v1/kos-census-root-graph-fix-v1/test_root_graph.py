from pathlib import Path
import importlib.util,sys,unittest,struct,json,resource,hashlib
resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,)*2)
HERE=Path(__file__).resolve().parent;ORIGINAL=HERE.parent/'kos-census-preparation-v1'
sys.path.insert(0,str(HERE));sys.path.insert(1,str(ORIGINAL))
import graph,prepare
s=importlib.util.spec_from_file_location('original_controls',ORIGINAL/'test_preparation.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(m));assert r.wasSuccessful() and r.testsRun==38
plan=prepare.read(ORIGINAL/'PREPARATION.json');base=Path(plan['root']);data=(base/'off/out/re4dc-game.elf').read_bytes();elf=graph.ELF(data)
h=struct.unpack_from('<16sHHIIIIIHHHHHH',data);sections=[struct.unpack_from('<IIIIIIIIII',data,h[6]+i*h[11]) for i in range(h[12])];symbols=[]
for section in sections:
 if section[1]!=2:continue
 st=sections[section[6]];strings=data[st[4]:st[4]+st[5]]
 for at in range(section[4],section[4]+section[5],16):
  ni,v,size,info,other,index=struct.unpack_from('<IIIBBH',data,at);name=strings[ni:].split(b'\0',1)[0].decode()
  if name and index and info&15==2:symbols.append((name,at,ni,v,size,info,other,index))
provider=next(s for s in symbols if s[0]=='_malloc' and s[5]>>4==1);local=next(s for s in symbols if s[5]>>4==0 and s[0]!='_malloc');other=next(s for s in symbols if s[5]>>4==1 and s[0] not in ['_malloc','___wrap_malloc'])
checks=['actual-13-edges-PASS'];proof=graph.verify(base/'off/out/re4dc-game.elf',base/'off/build.log','off',plan['baseline_wraps']['off']);assert len(proof['routes'])==13
# Existing local names must never shadow a valid global provider.
b=bytearray(data);struct.pack_into('<I',b,local[1],provider[2]);assert graph.ELF(bytes(b)).function('_malloc')==elf.function('_malloc');checks.append('local-name-alias-cannot-shadow-global')
def rejects(label,mutator,fn=lambda x:graph.ELF(x)):
 b=bytearray(data);mutator(b)
 try:fn(bytes(b))
 except (AssertionError,KeyError,ValueError):checks.append(label)
 else:raise AssertionError('Mutant escaped '+label)
rejects('missing-global-no-local-fallback',lambda b:b.__setitem__(provider[1]+12,2),lambda x:graph.ELF(x).function('_malloc'))
rejects('conflicting-global-provider',lambda b:struct.pack_into('<I',b,other[1],provider[2]))
rejects('conflicting-weak-provider',lambda b:(struct.pack_into('<I',b,other[1],provider[2]),b.__setitem__(other[1]+12,0x22)))
rejects('unsupported-function-binding',lambda b:b.__setitem__(other[1]+12,0x32))
# Global->weak keeps one externally resolvable definition with exact extent.
b=bytearray(data);b[provider[1]+12]=0x22;assert graph.ELF(bytes(b)).function('_malloc')==elf.function('_malloc');checks.append('one-weak-definition-is-unambiguous')
result={'original_host_controls':r.testsRun,'actual_reader_controls':checks,'SDK':0,'Make':0,'guest':0,'coverage':'UNKNOWN','graph_sha256':hashlib.sha256((HERE/'graph.py').read_bytes()).hexdigest()}
with (HERE/'ROOT-CONTROLS.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps(result))
