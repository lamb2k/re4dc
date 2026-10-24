"""Real-camera LOD20 graph corner potential. No guest/timing/pixel proof."""
import argparse,json,os,sys,struct
from pathlib import Path
import numpy as np
from estimate_loaded import HERE,TOOLS,SOURCE,sha,pin,groups
sys.path.insert(0,str(TOOLS/'worldlean'))
import sgprice as sg
from camera_selection import cameras,selection,legacy_viewport_audit
from estimate_graph import candidates,require_pin,frozen_variants

def hostpath(s):
 if os.name=='nt':
  if s.startswith('/mnt/c/'):s='C:/'+s[7:]
  elif s.startswith('/root/'):s='//wsl.localhost/Ubuntu-24.04'+s
 return Path(s)
def outcodes(cg,mv,tv,P,near):
 cv=cg@mv.T+tv;a,c=sg.side_coefs(P);oc=np.zeros(len(cv),np.uint8)
 for k in range(4):oc|=np.where(a[k]*cv[:,0 if k<2 else 1]+c[k]*cv[:,2]<0,1<<k,0).astype(np.uint8)
 oc|=np.where(-cv[:,2]<near,16,0).astype(np.uint8);oc|=np.where(-cv[:,2]>sg.PROJ_FAR,32,0).astype(np.uint8)
 return oc
def frame(D,p,variants,cam):
 V=np.array(cam[:12]).reshape(3,4);P=cam[12:19];near=P[6]/(P[5]-1);far=cam[19]
 pairs,mv,tv=selection(D,V,P,near,far,20);out={k:dict(selected_corners=0,post_trivial_reject_preclip_corners=0,near_straddling_strips=0,post_trivial_reject_strips=0,walked_strips=0,optimistic_selected_min_corners=0) for k in variants}
 for (pi,li),sel in pairs.items():
  l=p.lets[li];cs=p.decoded(l);oc=outcodes(np.array(cs)[:,:3],mv[pi],tv[pi],P,near)
  ends=groups(p,p._sg,li);vis=[];start=0
  for end in ends:
   w=sel['walk'][start:end];assert not len(w) or np.all(w==w[0]);vis.append(bool(w[0]) if len(w) else False);start=end
  for mode,lets in variants.items():
   x=lets[li];start=0
   for gi,end in enumerate(x['group_ends']):
    if vis[gi]:
     out[mode]['optimistic_selected_min_corners']+=x['optimistic_group_min_corners'][gi]
     for strip in x['strips'][start:end]:
      oo=oc[strip];out[mode]['selected_corners']+=len(strip);out[mode]['walked_strips']+=1
      if not int(np.bitwise_and.reduce(oo))&63:
       out[mode]['post_trivial_reject_preclip_corners']+=len(strip);out[mode]['post_trivial_reject_strips']+=1
       out[mode]['near_straddling_strips']+=int(bool(np.any(oo&16)))
    start=end
 return dict(selected_meshlets=len(pairs),modes=out)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--inputs',required=True);ap.add_argument('--assets',required=True);ap.add_argument('--output',required=True);ap.add_argument('--camera',action='append',required=True,help='room=PS2CAM-log');a=ap.parse_args();output=Path(a.output)
 if output.exists():raise FileExistsError(output)
 inputs=hostpath(a.inputs);resolved=json.loads(inputs.read_text());assert resolved['source']==SOURCE;assets=hostpath(a.assets)
 byroom=frozen_variants();results={}
 for arg in a.camera:
  room,log=arg.split('=',1);log=hostpath(log);row=resolved['rooms'][room];files={k:hostpath(v['path']) for k,v in row['files'].items()}
  for k,f in files.items():
   if sha(f)!=row['files'][k]['sha256']:raise ValueError('resolved input changed '+k)
  mesh=assets/(room+'-stripshare-v1')/'ps2-dd3.re4mesh';sgfile=mesh.with_suffix('.r4sg') if room=='r101' else None
  for f in [mesh]+([sgfile] if sgfile else []):
   q=byroom[room]['files'][f.name]
   if sha(f)!=q['sha256'] or f.stat().st_size!=q['bytes']:raise ValueError('compact frozen identity')
  sb=sgfile.read_bytes() if sgfile else None;p,variants,loaded=candidates(mesh.read_bytes(),files['r4pw'].read_bytes(),sb);p._sg=sb
  oh=struct.unpack_from('<4s19I',files['re4mesh'].read_bytes())
  if p.h[18]!=oh[3] or (p.h[17] or len(p.data))!=oh[2]:raise ValueError('original extent/CRC binding')
  D=sg.load(files['re4mesh'],files['r4pw'],files.get('r4sg'));assert len(p.lets)==len(D['vc'])
  baseline=[]
  for li,l in enumerate(p.lets):
   assert l['n']==D['vc'][li]
   baseline.append(dict(strips=l['strips'],group_ends=groups(p,sb,li),optimistic_group_min_corners=variants['gouraud_cyclic'][li]['optimistic_group_min_corners']))
  if sb:
   compact_groups=np.frombuffer(sb,'<u2',offset=32).reshape(D['SG'].shape)
   assert np.array_equal(compact_groups[:,:,:7],D['SG'][:,:,:7])
   # Word7 source-corner span is intentionally rekeyed by existing offline dedup.
   # This strip-corner estimate uses only group boxes and membership, not CPU priming.
   D['SG']=compact_groups.astype(np.int64)
  variants={'baseline':baseline,**variants};rows=[]
  for f,cam in cameras(log):rows.append(dict(frame=f,**frame(D,p,variants,cam)))
  totals={k:{metric:sum(x['modes'][k][metric] for x in rows) for metric in rows[0]['modes'][k]} for k in variants}
  for k in totals:
   totals[k]['selected_average_strip_length']=totals[k]['selected_corners']/max(1,totals[k]['walked_strips'])
   totals[k]['post_trivial_reject_average_strip_length']=totals[k]['post_trivial_reject_preclip_corners']/max(1,totals[k]['post_trivial_reject_strips'])
   totals[k]['optimistic_selected_reduction_ceiling_percent']=100*(1-totals[k]['optimistic_selected_min_corners']/totals['baseline']['selected_corners'])
   for metric in ('selected_corners','post_trivial_reject_preclip_corners'):
    totals[k][metric+'_reduction_percent']=100*(1-totals[k][metric]/totals['baseline'][metric])
  results[room]=dict(camera=pin(log),legacy_viewport=legacy_viewport_audit(log),compact=pin(mesh),loaded=loaded,totals=totals,frames=rows);print(room,json.dumps(totals),flush=True)
 output.write_text(json.dumps(dict(source=SOURCE,lod_divisor=20,frames='500..794 stride7',scope='MODELLED real-camera strip corners; post-trivial-reject counts are before actual near clipping. Does not model TA interpolation/coverage/depth ties. SG groups retain exact triangle membership and boxes; no assets/guests.',inputs_sha256=sha(inputs),helper_files={p.name:sha(p) for p in HERE.glob('*.py')},rooms=results),indent=2)+'\n')
if __name__=='__main__':main()
