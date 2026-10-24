import pathlib,json,hashlib
D=pathlib.Path('C:/Game Dev/Emulators/RE4DC-QA23-Audits-5e4de9a0'); E=pathlib.Path('C:/Flycast-Evidence/re4-dreamcast/audits23-takeover/5e4de9a0')
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for x in iter(lambda:f.read(4194304),b''):h.update(x)
 return h.hexdigest()
p=D/'IDENTITY.json';j=json.loads(p.read_text());j['pending']=['root final integration landing and fresh full release tier','physical Dreamcast acceptance including arena two-minute challenge','historical arena failure cause and exact overlay phase/failure injection not proven'];p.write_text(json.dumps(j,indent=2)+'\n')
fs=sorted(f for f in D.rglob('*') if f.is_file() and f.name!='SHA256SUMS.txt');(D/'SHA256SUMS.txt').write_text(''.join(f'{sha(f)}  {f.relative_to(D).as_posix()}\n' for f in fs))
p=E/'qa-identity/docs-refresh-v1.json';r=json.loads(p.read_text());r['docs']={n:sha(D/n) for n in ['README.txt','STEPS.txt','IDENTITY.json','SHA256SUMS.txt']};assert all(sha(D/k)==v for k,v in r['tracks_unchanged'].items());p.write_text(json.dumps(r,indent=2)+'\n');print('RESOLVED pending metadata and resealed; tracks unchanged')