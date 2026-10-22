from pathlib import Path
import hashlib,json,os,datetime
D=Path(r'C:\Flycast-Evidence\re4-dreamcast\castle18-20261018\Test21\recovered-j-content-20261021');source=D/'segments/route-walk294/track03.iso';target=D/'master/track03.iso';assert not target.exists();h=hashlib.sha256()
with source.open('rb')as f:
 for b in iter(lambda:f.read(8*1024**2),b''):h.update(b)
assert h.hexdigest()=='b67ac21eff8d819ef9ca5f0997b4c16401cb98a3d304feb65aa4b90f7affbeb6';before=source.stat();os.link(source,target);after=target.stat();assert before.st_ino==after.st_ino and before.st_dev==after.st_dev and before.st_size==after.st_size
failed=D/'segments/route-walk-controlled-event001';saved=D/'segments/route-walk-controlled-event001-prelaunch-missing-master';assert failed.is_dir()and not any(failed.iterdir())and not saved.exists();failed.rename(saved)
p=D/'controlled001-missing-master-hardlink-restoration.json';assert not p.exists();p.write_text(json.dumps(dict(scope='Failedprelaunch no process launched. Missingmasterpathname restored asNTFShardlink toexistingowned294 exactimage; no bytescopied/deleted/rebuilt/retargeted. Emptyfailedsegmentrenamed/preserved.',time=datetime.datetime.now().astimezone().isoformat(),source=str(source),restored=str(target),sha256=h.hexdigest(),same_file_id=before.st_ino,bytes=before.st_size,preserved_failed_segment=str(saved)),indent=2)+'\n');print('ExactMASTERhardlink restored; failedemptysegment preserved')
