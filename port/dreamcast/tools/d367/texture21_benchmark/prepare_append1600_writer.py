"""Create small immutable source-only proposal; no payload roots or allocation."""
import argparse,json
from pathlib import Path
import immutable_append1600_writer as w

def plan(controller):
 return dict(status='SOURCE_ONLY_REQUIRES_EXPLICIT_ROOT_ALLOCATION',family='immutable-append1600',parent1596='/root/probe/texture21-append1596-plan-20261022-01',delta1600='/root/probe/texture21-append1600-delta-20261022-01',parent_input_seal_path=r'C:\Flycast-Evidence\re4-dreamcast\texture21-benchmark-20261021\append1600-delta-01\SHA256SUMS',parent_input_seal_sha256=w.DELTA_SEAL,known_reader='/root/probe/codex-texture-atlas21/port/dreamcast/tools/d367/texpack.py',known_reader_sha256=w.READER_SHA,source_sha256={name:w.sha(Path(w.__file__).parent/name)for name in sorted(w.DEPENDENCIES)},controller_sha256=controller,metadata_root=r'C:\Flycast-Evidence\re4-dreamcast\texture21-benchmark-20261021\append1600-materialization-01',payload_roots=[r'\\wsl.localhost\Ubuntu-24.04\root\re4data\private\texture-append1600-20261022-v1',r'C:\Game Dev\Emulators\re4-assets-private\texture-append1600-20261022-v1'],expected=dict(sha256=w.PACK_SHA,bytes=w.PACK_BYTES,members=7133,mips_if_selected=1600,current6537_byteexact=True,append596=True),aggregate_cap_bytes=w.CAP,runtime_floor_bytes=w.FLOOR,peer_reserved_bytes=w.PEER,inner_seconds=51,outer_seconds=130,accounting='Sum max(4KiB-rounded logical,native allocation where available); unsupported UNC fallback logical; no compression credits',source_only_holds=['29worlds/632descriptors/29certificates UNSELECTED','old disc extent too small: no image overwrite','no programme/image/guest/production/SD/release selection','future TWID18 requires a separately sealed resolver/profile; no automatic adoption'])

def main():
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('--out',type=Path,required=True);a.add_argument('--controller-sha256',required=True);v=a.parse_args()
 if not w.re_hash(v.controller_sha256):raise ValueError('exact reviewed controller source SHA required')
 if v.out.exists():raise FileExistsError('preserve existing proposal namespace')
 p=plan(v.controller_sha256);head,index,rows=w.resolve(p)
 v.out.mkdir();w.json_new(v.out/'writer-plan.json',p);w.json_new(v.out/'RESOLUTION.json',dict(status='METADATA_RESOLUTION_ONLY_NO_LARGE_OUTPUT',members=len(rows),base=sum(r['source']=='canonical1004'for r in rows),append=sum(r['source']!='canonical1004'for r in rows),bytes=w.PACK_BYTES,sha256=w.PACK_SHA,index_bytes=len(index),data_offset=len(head)+len(index),source_payload_bytes_read=0,large_bytes_written=0))
 print(json.dumps(dict(plan_sha256=w.sha(v.out/'writer-plan.json'),writer_sha256=w.sha(w.__file__),resolution_sha256=w.sha(v.out/'RESOLUTION.json'))))
if __name__=='__main__':main()
