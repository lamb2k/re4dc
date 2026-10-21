"""Read-only frozen pair accounting; no guest and no runtime source edits."""
from pathlib import Path
import argparse,subprocess,struct,json,hashlib,tempfile
T=Path(__file__).resolve().parent

def function(text,signature):
 a=text.index(signature);start=text.index('{',a);depth=1;i=start+1
 while depth:
  depth+=(text[i]=='{')-(text[i]=='}');i+=1
 return text[a:i]

def main():
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);p.add_argument('--pack',type=Path,required=True);p.add_argument('--kos-source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();assert not a.output.exists()
 d=json.loads((a.evidence/'window-demand-attribution-02.json').read_text());index={}
 with a.pack.open('rb')as f:
  header=f.read(28);count,at=struct.unpack_from('<II',header,12);f.seek(at);raw=f.read(count*16)
  for i in range(count):
   crc,fnv,offset,size=struct.unpack_from('<IIII',raw,i*16);index[f'{crc:08x}-{fnv:08x}']={'sector':i//128,'offset':offset,'size':size}
  for arm in ('off','on'):
   for e in d['arms'][arm]['events']:
    if e['phase']not in ('held','restore'):continue
    m=index[e['key']];f.seek(m['offset']);blob=f.read(m['size']);tx=struct.unpack_from('<64s8I',blob,48);m['payload_at']=tx[4];m['payload']=tx[5];assert m['size']==m['payload_at']+m['payload'] and m['payload_at']==144
    m['sha256']=hashlib.sha256(blob).hexdigest()
 kosfile=a.kos_source;source=kosfile.read_text();signatures=['static void bgrad_cache(','static int bread_cache(','static inline int bdread(','static inline void iso_abort_stream(void) {','static int iso_stream_done(','static ssize_t iso_read(','static off_t iso_seek(']
 fragments='\n\n'.join(function(source,s)for s in signatures)
 cases=[]
 for armno,arm in enumerate(('off','on')):
  held=[e['key']for e in d['arms'][arm]['events']if e['phase']=='held'];restore=[e['key']for e in d['arms'][arm]['events']if e['phase']=='restore']
  assert len(set(held))==22 and not set(held)&set(restore)
  assert len({index[k]['offset']//2048 for k in held})==22
  for e in d['arms'][arm]['events']:
   if e['phase']not in ('held','restore'):continue
   m=index[e['key']];cases.append({'arm':armno,'restore':int(e['phase']=='restore'),'key':e['key'],**m})
 with tempfile.TemporaryDirectory(prefix='cache21-window-iso-')as work:
  work=Path(work);(work/'actual_iso.inc').write_text(fragments);(work/'cases.inc').write_text('const Case cases[]={\n'+''.join('{%s,"%s"},\n'%(','.join(str(c[x])for x in ['arm','restore','sector','offset','size','payload_at','payload']),c['key'])for c in cases)+'};\n')
  cmd=['g++','-std=c++17','-O1','-fsanitize=undefined','-fno-sanitize-recover=all','-I'+str(work),str(T/'replay_iso.cpp'),'-o',str(work/'replay')];subprocess.run(cmd,check=True);run=subprocess.check_output([str(work/'replay')],text=True)
 result={'kind':'actual-source-host-accounting-not-new-guest','frozen_source':'b21116ec0cf2c984e9f49769a148373553bff00d','count':count,'index_sha256':hashlib.sha256(raw).hexdigest(),'kos_source_path':str(kosfile),'kos_source_sha256':hashlib.sha256(kosfile.read_bytes()).hexdigest(),'fragments_sha256':hashlib.sha256(fragments.encode()).hexdigest(),'cases':cases,'host_output':run,'limits':['Drive calls and file open/directory handling are mocked. This is source accounting, not a retained per-request target trace.','The sealed counter intervals are host-time matched, not frame-identical.','Block microseconds and physical Dreamcast acceptance are not derived.']}
 a.output.write_text(json.dumps(result,indent=2)+'\n');print(run)
if __name__=='__main__':main()
