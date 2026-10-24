from pathlib import Path
import hashlib,json,collections
root=Path(r'\\wsl.localhost\Ubuntu-24.04')
run=root/'dev/shm/gc-port23-current-1d63cffe3-vhytjv63'
report=json.loads((run/'report.json').read_text())
assert report['complete'] and len(report['objects'])==67 and len(report['off_identity'])==14 and all(report['off_identity'].values())
label=lambda r:r['unit'].replace('../','').replace('/','_').rsplit('.',1)[0]+'-'+r['arm']
origin=lambda r:root/Path(r.get('reused_from','/dev/shm/gc-port23-current-1d63cffe3-vhytjv63/report.json')).as_posix().lstrip('/')
byunit=collections.defaultdict(dict)
for row in report['objects']:
 origin_dir=origin(row).parent
 stem=label(row)
 for suffix,key in [('.o','sha256'),('-nodebug.o','nodebug_sha256')]:assert hashlib.sha256((origin_dir/(stem+suffix)).read_bytes()).hexdigest()==row[key]
 fields=row['size'].splitlines()[-1].split()
 byunit[row['unit']][row['arm']]=[int(x) for x in fields[:3]]
delta=[0,0,0]
for unit,arms in byunit.items():
 if 'on' in arms:
  base=arms.get('baseline',arms['zero'])
  delta=[d+a-b for d,a,b in zip(delta,arms['on'],base)]
extra=byunit['platform/gc_asset_disc.cpp']
pin_delta=[a-b for a,b in zip(extra['on-synthetic-pin'],extra['on'])]
stacks=[]
for row in report['objects']:
 path=origin(row).parent/(label(row)+'.su')
 if not path.is_file():continue
 for line in path.read_text().splitlines():
  fields=line.split('\t')
  if len(fields)==3:
   location=fields[0].split(':',3)
   stacks.append(dict(unit=row['unit'],arm=row['arm'],function=location[-1],bytes=int(fields[1]),classification=fields[2],receipt=str(path)))
on=sorted([r for r in stacks if r['arm']=='on'],key=lambda r:r['bytes'],reverse=True)
changes=[]
for unit in byunit:
 off={r['function']:r for r in stacks if r['unit']==unit and r['arm']=='zero'}
 for r in (r for r in on if r['unit']==unit):
  old=off.get(r['function'])
  if old and old['bytes']!=r['bytes']:changes.append(dict(unit=unit,function=r['function'],off=old['bytes'],on=r['bytes'],delta=r['bytes']-old['bytes']))
dest=Path(r'C:\Flycast-Evidence\re4-dreamcast\gc-port23-20261023\target-static1d63-current')
dest.mkdir(exist_ok=True)
(run/'report.json').is_file()
(dest/'report.json').write_bytes((run/'report.json').read_bytes())
metadata={}
for row in report['objects']:
 stem=label(row); od=origin(row).parent
 for suffix in ['-command.json','-inputs.json','.log','.su','-undefined.txt']:
  p=od/(stem+suffix)
  if p.is_file():
   out=dest/(stem+suffix);out.write_bytes(p.read_bytes());metadata[out.name]=dict(bytes=out.stat().st_size,sha256=hashlib.sha256(out.read_bytes()).hexdigest(),original=str(p))
summary=dict(status='SELECTED_TARGET_COMPLETE_ONLY',source=report['source'],baseline=report['baseline'],objects=67,reused=sum('reused_from' in r for r in report['objects']),off14_identical=True,helpers5_off_empty=True,delta=dict(zip(['text','data','bss'],delta)),delta_total=sum(delta),synthetic_catalog_pin_text_data_bss=pin_delta,top_on_compiler_frames=on[:18],changed_compiler_frames=changes,limits=['Actual current fb254 selected compiler commands; no final link/image/map/heap/KOS/H2/guest or installed catalog qualification.','Compiler self-frames are not call-chain high-water or IRQ stack proof.','Required3ff/wired1f6 remains incomplete.','Original77 target failure preserved separately; current rows carry exact compiled source and origin when reused.'])
(dest/'SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n')
(dest/'METADATA-MANIFEST.json').write_text(json.dumps(metadata,indent=2)+'\n')
print(json.dumps({k:v for k,v in summary.items() if k not in ['top_on_compiler_frames','changed_compiler_frames']},indent=2))
print('Top ON self frames:',json.dumps(on[:8],indent=2))
print('Changed compiler frames:',json.dumps(changes,indent=2))