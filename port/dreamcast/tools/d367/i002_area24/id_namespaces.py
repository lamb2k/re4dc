"""Finite existing-room ID namespace audit, no geometry search or predicates."""
import argparse,hashlib,json,struct,subprocess,resource
from pathlib import Path
SOURCE='78cbd962ee0d98dc700d0fb452500a16ac35b14c'
ROOMS={'r105':[0x20,0x21,0x22,0x23,0x30,0x31,0x32],'r106':[],'r109':[0x26,0x27,0x28,0x29,0x2a,0x2b,0x2c],'r113':[0x55],'r11f':[0xf,0x1e]}
def pin(p):return dict(path=str(p),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
def main():
 resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,)*2)
 ap=argparse.ArgumentParser();ap.add_argument('--repo',type=Path,required=True);ap.add_argument('--stage',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
 if a.out.exists():raise ValueError('Fresh output required')
 rows=[]
 for room,ids in ROOMS.items():
  path=a.stage/'dc/native'/room/'ps2-world.ids';raw=path.read_bytes();magic,v,n,crc=struct.unpack_from('<4sIII',raw)
  if magic!=b'R4ID' or v!=1 or n>len(raw)-16 or len(raw)%32:raise ValueError('Source ID header/extent')
  body=raw[16:16+n];source=subprocess.check_output(['git','-C',str(a.repo),'show',SOURCE+':src/st1/'+room+'.cpp'],text=True)
  actions=[dict(line=i,text=line.strip()) for i,line in enumerate(source.splitlines(),1) if 'SmdSetTrans('in line]
  rows.append(dict(room=room,ids=pin(path),source_crc=f'{crc:08x}',placements=n,source_path='src/st1/'+room+'.cpp',source_sha256=hashlib.sha256(source.encode()).hexdigest(),literal_group_occurrences={f'{i:02x}':[j for j,x in enumerate(body) if x==i] for i in ids},SmdSetTrans_source_actions=actions,semantic_PS2_provenance='NOT_NEWLY_REESTABLISHED_BY_ID_COUNT',actual_runtime_transition='UNOBSERVED_IN_THIS_AUDIT'))
 out=dict(classification='READ_ONLY_EXISTING_NAMESPACE_RANK_INPUT_NOT_ADMISSION',source=SOURCE,rooms=rows,new_rays=0,new_predicates=0,runtime_edits=0,limitations=['ID headers and new file hashes alone do not reestablish original PS2 semantic lineage.','No new hiding condition, trigger, source/object generation, GPU material receipt or runtime saving is established.','Repeated ID may require a group bridge; changing unique-ID pose logic would be unsafe.'])
 a.out.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(dict(report=pin(a.out),groups={r['room']:r['literal_group_occurrences'] for r in rows})))
if __name__=='__main__':main()
