"""Read-only exact-input registration counts; does not infer co-residency from all files."""
from pathlib import Path
import argparse,json,hashlib,struct,sys

def main():
 p=argparse.ArgumentParser();p.add_argument('--policy',type=Path,required=True);p.add_argument('--tools',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();assert not a.out.exists();sys.path.insert(0,str(a.tools));import le_mirror
 policy=json.loads(a.policy.read_text());rows=[];inputs=[];errors=[]
 def u32(b,o):return struct.unpack_from('<I',b,o)[0]
 for rel,meta in policy['source_files'].items():
  if not meta.get('parsed'):continue
  path=Path(meta['path'])
  if not path.exists():errors.append({'path':rel,'reason':'retained-path-unavailable'});continue
  data=path.read_bytes();digest=hashlib.sha256(data).hexdigest()
  if digest!=meta['sha256']:errors.append({'path':rel,'reason':'hash-differs','actual':digest});continue
  try:slot=le_mirror.native_payload_slot(data)
  except ValueError:body,base=data,0
  else:size,base=struct.unpack_from('<I4xI',data,slot+4);body=data[base:base+size]
  n=u32(body,0);assert 0<n<=4096;end=u32(body,4);end=end if 16+8*n<=end<=len(body)else len(body);offsets=list(struct.unpack_from('<%dI'%n,body,16));bounds=sorted(set(o for o in offsets if 16+8*n<=o<end)|{end})
  inputs.append({'path':rel,'source':str(path),'sha256':digest,'bytes':len(data),'active_base':base,'active_bytes':len(body)})
  for i,off in enumerate(offsets):
   tag=body[16+4*n+4*i:20+4*n+4*i].rstrip(b'\0')
   if tag!=b'EFF':continue
   assert off in bounds;stop=bounds[bounds.index(off)+1];h=struct.unpack_from('<12I',body,off);assert h[0]==11,(rel,i,h[0])
   def ids(at):
    if not at:return []
    at+=off;count=u32(body,at);assert count<4096 and at+4+8*count<=stop;return [struct.unpack_from('<H',body,at+4+8*j)[0]for j in range(count)]
   def points(at):
    if not at:return []
    at+=off;count=u32(body,at);assert count<4096 and at+4+4*count<=stop;return [at+u32(body,at+4+4*j)for j in range(count)]
   tex=ids(h[1]);tpl=points(h[6]);anm=points(h[7]);assert len(tex)==len(tpl)==len(anm);textures=[]
   for tid,tp,an in zip(tex,tpl,anm):
    assert off<=tp+12<=stop and off<=an+10<=stop
    descriptors=u32(body,tp+4);frames=struct.unpack_from('<H',body,an+8)[0]
    textures.append({'id':tid,'frames':frames,'descriptors':descriptors,'tpl_offset':tp,'anm_offset':an})
   models=ids(h[5]);rows.append({'path':rel,'archive_word_index':i+4,'EFF_offset':off,'EFF_bytes':stop-off,'texture_count':len(tex),'texobj_demand':sum(t['frames']for t in textures),'texture_ids':tex,'textures':textures,'model_ids':models,'model_count':len(models),'est_count':len(ids(h[2])),'sst_count':len(ids(h[3])),'path_count':len(ids(h[4]))})
 result={'scope':'Exact original asset registration shape only; all archives are not simultaneously live.','policy_sha256':hashlib.sha256(a.policy.read_bytes()).hexdigest(),'inputs':inputs,'blocks':rows,'errors':errors,'counts':{'input_files':len(inputs),'EFF_blocks':len(rows),'max_block_texobjs':max(r['texobj_demand']for r in rows),'max_single_frames':max(t['frames']for r in rows for t in r['textures']),'ids_above255':sum(t['id']>255 for r in rows for t in r['textures']),'frame_descriptor_mismatches':sum(t['frames']!=t['descriptors']for r in rows for t in r['textures']),'duplicate_texid_blocks':sum(len(set(r['texture_ids']))!=len(r['texture_ids'])for r in rows),'duplicate_modelid_blocks':sum(len(set(r['model_ids']))!=len(r['model_ids'])for r in rows)}}
 a.out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'counts':result['counts'],'errors':errors,'largest':sorted([{'path':r['path'],'slot':r['archive_word_index'],'texobj':r['texobj_demand'],'texids':r['texture_count'],'models':r['model_count']}for r in rows],key=lambda x:x['texobj'],reverse=True)[:12],'core':[r for r in rows if r['path']=='etc/core.das']},indent=2))
if __name__=='__main__':main()
