from pathlib import Path
import hashlib,json,sys
T=Path(r'\\wsl.localhost\Ubuntu-24.04\root\probe\codex-qa21-combined-regression')
sys.path[:0]=[str(T/'port/dreamcast/tools'),str(T/'port/dreamcast/tools/d367/ps2ref'),str(T/'port/dreamcast/tools/d367/fullplay')]
import room_smd,ps2roomdiff,fp_iso
R=Path('C:/Flycast-Evidence/re4-dreamcast/qa21-combined-regression-20261021');M=json.loads((R/'combined-input/file-manifest.json').read_text());matches=[x for x in M if x.lower().endswith('/r100.dar')];assert len(matches)==1
path=matches[0];entry=M[path];tr=fp_iso.Track(R/'combined-input/gdemu/track03.iso',45000);data=tr.read_bytes(entry['extent'],entry['bytes']);assert hashlib.sha256(data).hexdigest()==entry['sha256']
arc,endian=room_smd.payload_archive(data);rows=ps2roomdiff.aev_records(arc,endian,0x9c,0x5c)
for key,row in rows.items():
 floor,h,shape,points=row['xz4'];row['center']=[sum(p[0] for p in points)/len(points),floor,sum(p[1] for p in points)/len(points)]
result={'source':'6f9d31b0e00497a75fdd7e25bb04f92305103087','program':'ce080eb290aec073f406e93da27911f4fa70b457768288f52a893175a6846e8e','asset':{'path':path,'bytes':len(data),'sha256':entry['sha256']},'archive_endian':endian,'aev_rows':rows,'door_source':{'file':'src/st1/r100.cpp','function':'r100_DoorCk','door_id':2,'normal_requirement':'Original RsfCheck room bit4 must become true; before that the normal door is open-locked or close-locked by original ambush logic. No flag poke or warp can qualify the normal route.'},'source_order':['Original s03 and first Ganado death callback','Original s20, radio and post-event ambush','Original source room-bit4 completion/unlock','Ordinary door interaction, source leave/entry to a new room','Repeat QA reopen only at the actual new-room source-safe state'],'scope':'Source/asset fixture preparation only. Coordinates do not prove a traversed route or unlocked door.'}
out=R/'r100-route-fixture-v2.json';assert not out.exists();out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'asset':result['asset'],'aev_records':len(rows),'out':str(out)}))