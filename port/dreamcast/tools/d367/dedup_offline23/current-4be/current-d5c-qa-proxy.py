"""Current4be normal QA proxy creation/identity; no SDK."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,shutil
E=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/dedup-offline23-20261023/current-4be08e01')
T=Path('/root/work/lanes/dedup-offline23-qa-4be08e01/port/dreamcast/tools/d367')
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
arm=sys.argv[1];assert arm in ('off','on')
m=json.loads((E/'qa-media-r1/pair-media-identity.json').read_text());x=m['arms'][arm];r=Path(x['work']);final=Path(x['path'])/'gdemu';base=E/('qa-proxy-'+arm+'-r1');assert not base.exists()
assert shutil.disk_usage('/mnt/c').free>=24*1024**3
assert sha(final/'track03.bin')==x['tracks']['track03.bin']['sha256']
env=dict(os.environ,PRUNE_AUTO='0',PYTHONDONTWRITEBYTECODE='1',RE4DC_STAGE_EXT4='0')
with (r/'logs/proxy-master.txt').open('w') as f:subprocess.run(['bash',str(T/'fullplay/fp_master.sh'),str(r/'pkgtree'),x['manifest'],str(final/'IP.BIN'),str(base),x['programme']['path']],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
a=json.loads(Path(x['manifest']).read_text());b=json.loads((base/'base-manifest.json').read_text())
allowed={'dc/warp.txt','dc/padscript.txt','dc/w11.txt'}
diff=[n for n in a.keys()|b.keys() if a.get(n,{}).get('sha256')!=b.get(n,{}).get('sha256')]
assert set(diff)==allowed,diff
assert json.loads((base/'base.json').read_text())['elf']==x['programme']['path']+'/re4dc-game.elf'
report=dict(status='PASS_EXACT_FINAL_QA_PROGRAMME_ALL14_DATA_PROXY_FIXTURES_ONLY',source=m['source'],arm=arm,final_manifest_sha256=sha(Path(x['manifest'])),proxy_manifest_sha256=sha(base/'base-manifest.json'),track03_sha256=sha(base/'track03.iso'),only_differences=diff,final_track03_sha256=x['tracks']['track03.bin']['sha256'],base=str(base))
assert report['track03_sha256']==(base/'track03.sha256').read_text().strip()
(E/('qa-proxy-'+arm+'-identity-r1.json')).write_text(json.dumps(report,indent=2)+'\n')
assert shutil.disk_usage('/mnt/c').free>=24*1024**3
print('QA_OWNED_PROXY_READY',arm,flush=True)

