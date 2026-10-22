"""No-selector fallback: all four decoded buffers must agree, without image selection."""
import argparse,hashlib,json
from pathlib import Path
from PIL import Image

def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def compare(c,asm):
 rows=[];reference=None;shape=None;passed=True
 for arm,event in [('C',c),('ASM',asm)]:
  if not event.get('qualified') or len(event.get('framebuffer_source_offsets',[]))!=2:raise ValueError('qualified source-offset-pinned capture event required')
  if event.get('stock_grace_seconds')!=8 or event.get('stock_stop_deadline_monotonic')!=event['freeze_observed_monotonic']+8:raise ValueError('exact stock stop observation missing')
  if not 0<=event['capture_start_monotonic']-event['freeze_observed_monotonic']<=8:raise ValueError('capture start outside stock grace')
  if not 0<=event['capture_end_monotonic']-event['freeze_observed_monotonic']<=26:raise ValueError('frozen capture window differs')
  for index in (0,1):
   path=Path(event['path'])/f'fb{index}.png'
   if sha(path)!=event['images'][path.name]:raise ValueError('retained image bytes changed')
   with Image.open(path) as image:
    image=image.convert('RGB');current_shape=image.size;data=image.tobytes()
   if reference is None:reference=data;shape=current_shape
   identical=current_shape==shape and data==reference;passed=passed and identical
   rows.append(dict(arm=arm,index=index,source_offset=event['framebuffer_source_offsets'][index],size=current_shape,
                    file_sha256=sha(path),decoded_sha256=hashlib.sha256(data).hexdigest(),identical_to_first=identical))
 return dict(pixel_equivalent_without_selector=passed,images=rows,
             selection='No selected/best-match image; all four must be mutually identical.',
             limitation='Does not certify a clean gameplay frame, target memory, performance, or hardware acceptance.')
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--c-event',required=True);p.add_argument('--asm-event',required=True);p.add_argument('--output',required=True);a=p.parse_args()
 output=Path(a.output)
 if output.exists():raise FileExistsError('preserve existing comparison')
 result=compare(json.loads(Path(a.c_event).read_text()),json.loads(Path(a.asm_event).read_text()))
 output.write_text(json.dumps(result,indent=2)+'\n')
 if not result['pixel_equivalent_without_selector']:raise SystemExit(1)
if __name__=='__main__':main()
