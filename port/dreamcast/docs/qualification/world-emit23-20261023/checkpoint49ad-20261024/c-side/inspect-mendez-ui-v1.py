import pathlib,re
E=pathlib.Path('C:/Flycast-Evidence/re4-dreamcast')
for label,p in [('worldB',E/'world-emit23-takeover/49ad20f9/captures/B-mendez-r1/run-output.txt'),('auditsR',E/'audits23-takeover/5e4de9a0/decisions-mendez-on-r1/run-output.txt'),('statR',E/'stat-bytes23/takeover-2a14662d/mendez-bounded-on-r3/run-output.txt')]:
 s=p.read_text(errors='replace').replace('\0','').splitlines();print('\n'+label+' '+str(p))
 for i,l in enumerate(s):
  if 'native UI: package rejected:' in l or 'native UI: upload FAILED' in l:
   print('MATCH line',i+1);print('\n'.join(s[max(0,i-5):i+5]))