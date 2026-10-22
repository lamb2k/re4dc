from pathlib import Path
import hashlib,re,json
L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18')
castlePlannerPath=L/'trace-r201-dungeon-floor-wall-navigation-20261019.py';s=castlePlannerPath.read_text()
s,n=re.subn(r'start=\([^)]*\);goal=\([^)]*\)', 'start=(24341.2109375,-2000,-41091.8359375);goal=(19000,-2000,-45000)',s,count=1);assert n==1
s=s.replace("o=R/'r201-native-dungeon-floor-wall-route-20261019.json'","o=R/'Test21/recovered-j-content-20261021/resume-212-full-west-sourceSAT-route-20261021.json'")
s=s.replace('conservative500mm grid,300mm wallclearance','250-unit grid,220-unit wall clearance')
o=Path(r'C:\Flycast-Evidence\re4-dreamcast\castle18-20261018\Test21\recovered-j-content-20261021\resume-212-full-west-sourceSAT-route-20261021.json')
if o.exists():
 s=s.replace("assert not o.exists();o.write_text", "o.write_text")
exec(compile(s,str(castlePlannerPath),'exec'))
j=json.loads(o.read_text());j.update(base_planner_sha256=hashlib.sha256(castlePlannerPath.read_bytes()).hexdigest(),actual212_state_sha256='84edc508245ebd3bb47ebae7010c4db9db4458cc51f3985006c553bb87f3090a',source_SAT_json_sha256=hashlib.sha256((o.parents[2]/'r201-original-source-sat-navigation-20261019.json').read_bytes()).hexdigest())
def source_segment_clear(a,b):
 n=max(1,int(math.dist(a[:3],b[:3])/100)+1)
 for i in range(n+1):
  x,y,z=[a[k]+(b[k]-a[k])*i/n for k in range(3)]
  if blocked(round(x/step),round(z/step),y):return False
  if not any((yy:=plane(t,x,z))is not None and abs(yy-y)<50 for t in floors):return False
 return True
pp=j['all_points'];simple=[pp[0]];ii=0
while ii<len(pp)-1:
 jj=next(k for k in range(len(pp)-1,ii,-1)if source_segment_clear(pp[ii],pp[k]));simple.append(pp[jj]);ii=jj
j['simplified_source_checked_segments']=simple;j['normal_xz_targets']=[[v[0],v[2]]for v in simple[1:]]
o.write_text(json.dumps(j,indent=2)+'\n');print('Source checked simplified XZ targets',j['normal_xz_targets'])
