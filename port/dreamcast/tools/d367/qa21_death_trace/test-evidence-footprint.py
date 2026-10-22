import json,tempfile,os
from pathlib import Path
from unittest.mock import patch
from evidence_footprint import measure
with tempfile.TemporaryDirectory(prefix='qa21-footprint-') as td:
 root=Path(td);disc=root/'disc';cap=root/'case';disc.mkdir();cap.mkdir()
 track=disc/'track03.iso'
 with track.open('wb') as f:f.truncate(1024**3)
 os.link(track,cap/track.name);(cap/'flycast.exe').write_bytes(b'a'*10000);(cap/'baseline.dat').write_bytes(b'b'*3000)
 linked=measure(cap,disc);assert linked['charged_logical_bytes']==13000 and linked['excluded_exact_track_references'][0]['new_file_data_bytes']==0
 (cap/'frame.png').write_bytes(b'c'*5000);grown=measure(cap,disc);assert grown['charged_logical_bytes']-linked['charged_logical_bytes']==5000
 (cap/track.name).unlink();(cap/track.name).write_bytes(b'd'*7000);untrusted=measure(cap,disc);assert untrusted['charged_logical_bytes']==25000 and not untrusted['excluded_exact_track_references']
 real=Path.stat
 def transient(self,*args,**kwargs):
  if self.name=='vanished.tmp':raise FileNotFoundError(self)
  return real(self,*args,**kwargs)
 (cap/'vanished.tmp').touch()
 with patch.object(Path,'stat',transient):assert measure(cap,disc)['charged_logical_bytes']==25000
 print(json.dumps({'status':'PASS','linked_reference':linked,'growth_delta':5000,'preexisting_baseline_charged':True,'untrusted_track_charged':True,'disappearing_temp_tolerated':True},indent=2))
