from pathlib import Path
import hashlib,json,datetime
R=Path(r'C:\Flycast-Evidence\re4-dreamcast\castle18-20261018');D=R/'Test21/recovered-j-content-20261021';p=D/'retry285-frozen-program-image-127-identities-20261021.json';assert not p.exists();rows=[]
for f,expected in [(D/'master/track03.iso','b67ac21eff8d819ef9ca5f0997b4c16401cb98a3d304feb65aa4b90f7affbeb6'),(R/'Test21/builds/c21jmW/re4dc-game.elf','4d823b496b9a402baadabe7f679c089fa0fd55c7ffd175ec634915745a11487f'),(D/'route-walk127/data/disc.state','ec9ed07928efec777400317762bb1730a0644def73d610a1631c20381ca40e16')]:
 h=hashlib.sha256()
 with f.open('rb')as z:
  for b in iter(lambda:z.read(8*1024*1024),b''):h.update(b)
 sh=h.hexdigest();assert sh==expected;rows.append(dict(path=str(f),bytes=f.stat().st_size,sha256=sh))
p.write_text(json.dumps(dict(scope='Fresh FULL streamed SHA verification after authentic284death/285originalContinue and288normalherbUse. Read-only; original127/source33328 and runtime12a frozen unchanged. Not release or physicalDreamcast acceptance.',timestamp=datetime.datetime.now().astimezone().isoformat(),files=rows),indent=2)+'\n');print(p)
