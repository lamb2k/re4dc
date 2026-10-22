from pathlib import Path
import hashlib,json,datetime
L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18');D=Path(r'C:\Flycast-Evidence\re4-dreamcast\castle18-20261018\Test21\recovered-j-content-20261021');R=D.parent
pins=[(D/'master/track03.iso','b67ac21eff8d819ef9ca5f0997b4c16401cb98a3d304feb65aa4b90f7affbeb6'),(R/'builds/c21jmW/re4dc-game.elf','4d823b496b9a402baadabe7f679c089fa0fd55c7ffd175ec634915745a11487f'),(D/'route-walk127/data/disc.state','ec9ed07928efec777400317762bb1730a0644def73d610a1631c20381ca40e16'),(D/'route-walk292/data/disc.state','8cb3c0145e6e13aa159ff4b2b36cf0b753f444e0569446df05f44c7cfb40fb4f')]
rows=[]
for p,expected in pins:
 h=hashlib.sha256()
 with p.open('rb')as f:
  for b in iter(lambda:f.read(8*1024**2),b''):h.update(b)
 assert h.hexdigest()==expected,(p,h.hexdigest());rows.append(dict(path=str(p),sha256=h.hexdigest(),bytes=p.stat().st_size))
p=D/'prepared293-frozen-program-image-127-292-identities-20261021.json';assert not p.exists();p.write_text(json.dumps(dict(scope='Full streamed SHA verification before prepared293; read only. No guest, no image/state writes.',checked=datetime.datetime.now().astimezone().isoformat(),identities=rows),indent=2)+'\n');print('PASS full image/ELF/protected127/current292 hashes')
