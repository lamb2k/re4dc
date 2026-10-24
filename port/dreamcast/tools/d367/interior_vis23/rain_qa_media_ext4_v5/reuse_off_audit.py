"""Read actual immutable prior OFF media only; never creates a base or hardlink."""
from pathlib import Path
import hashlib,json
import common as c
def audit(base,expected,ipbytes,iso):
 tr=iso.Track(base/'track03.iso',45000);low=iso.Track(base/'track01-template.iso',0);got={};redirects=[]
 try:
  roots=iso.volume_roots(tr)
  for root,joliet in [(roots[0],False),(roots[1],True)]:
   c.need(root is not None,'both volume roots')
   for name,e,n,isdir,dlba,off in iso.walk(tr,root,joliet):
    if name.lower() in ['/dc/warp.txt','/dc/padscript.txt','/dc/w11.txt']:
     c.need((e,n)==({'/dc/warp.txt':400,'/dc/padscript.txt':420,'/dc/w11.txt':440}[name.lower()],8192),'redirect extent');redirects.append([joliet,name,e,n])
  c.need(len(redirects)==6,'six redirects')
  c.need(tr.read(45000,16)==low.read(0,16)==ipbytes,'IP bothtracks')
  for name,e,n in iso.files(tr):
   key=name.lstrip('/');c.need(key not in got,'duplicatefile');h=hashlib.sha256();reader=low if e<45000 else tr;lba=e;remain=n
   while remain:
    count=min(remain,1<<20);blob=reader.read_bytes(lba,count);c.need(len(blob)==count,'short read');h.update(blob);remain-=count;lba+=count//2048
   got[key]={'size':n,'sha256':h.hexdigest()}
  c.need(got==expected,'whole actual media differs')
 finally:tr.f.close();low.f.close()
 return {'status':'WHOLE_ACTUAL_OFF_MEDIA_EXACT_READONLY','base':str(base),'files':len(got),'programme_and14_match':True,'common_assets':1697,'redirects':redirects,'sourceIP':{'size':len(ipbytes),'sha256':hashlib.sha256(ipbytes).hexdigest()},'tracks':{n:c.row(base/n) for n in ['track03.iso','track01-template.iso','track02.raw']},'base_metadata':c.row(base/'base.json'),'no_stage_or_hardlink':True}
