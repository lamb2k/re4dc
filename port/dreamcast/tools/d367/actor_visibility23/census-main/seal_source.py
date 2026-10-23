from pathlib import Path
import hashlib,json,subprocess
P=Path(__file__).resolve().parent
if __name__=='__main__':
 if (P/'SOURCE-SEAL.json').exists():raise SystemExit('preserve existing source seal')
 host=json.loads((P/'HOST-TEST-RESULTS.json').read_bytes())
 if host['status']!='PASS' or host['methods']!=8:raise SystemExit('eight host methods required')
 subprocess.run(['wsl.exe','-d','Ubuntu-24.04','-u','root','--','bash','-n','/mnt/c/Game Dev/Emulators/codex-lanes/actor-visibility23/census-main-bea2r3/root-native-census-bea2.sh'],check=True)
 files={str(f.relative_to(P)):dict(bytes=f.stat().st_size,sha256=hashlib.sha256(f.read_bytes()).hexdigest())for f in sorted(P.rglob('*'))if f.is_file()}
 seal=dict(status='ACTOR23_CENSUS_MAIN_SOURCE_HOST_SUPPORT_ONLY',source='bea2d402ba06d41fb7b39946b5a9431a72f5b52a',files=files,bytes=sum(x['bytes']for x in files.values()),cap_bytes=128*1024,profiles_created=0,stages_created=0,guests=0,runtime_admitted=False)
 raw=(json.dumps(seal,sort_keys=True,indent=2)+'\n').encode()
 if seal['bytes']+len(raw)>seal['cap_bytes']:raise SystemExit('128KiB subreservation')
 (P/'SOURCE-SEAL.json').write_bytes(raw);print(hashlib.sha256(raw).hexdigest(),seal['bytes']+len(raw),len(files))
