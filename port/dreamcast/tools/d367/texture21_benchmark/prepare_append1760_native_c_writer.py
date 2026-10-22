"""Create small immutable source-only proposal; no payload roots or allocation."""
import argparse,json
from pathlib import Path
import immutable_append1760_native_c_writer as w
from native1760_source_binding21 import MANIFEST_PATH,MANIFEST_SHA,PARENT_PATH,PARENT_SHA

def plan(controller):
 meta=r'C:\Flycast-Evidence\re4-dreamcast\texture21-benchmark-20261021\append1760-materialization-native-c-01'
 return dict(status='SOURCE_ONLY_REQUIRES_EXPLICIT_ROOT_ALLOCATION',family='immutable-append1760-native-C',parent_input_seal_path=PARENT_PATH,parent_input_seal_sha256=PARENT_SHA,known_reader='/root/probe/codex-texture-atlas21/port/dreamcast/tools/d367/texpack.py',known_reader_sha256=w.READER_SHA,source_sha256={name:w.sha(Path(w.__file__).parent/name)for name in sorted(w.DEPENDENCIES)},controller_sha256=controller,native_source_manifest_path=MANIFEST_PATH,native_source_manifest_sha256=MANIFEST_SHA,main_authored_stream_helper_sha256=w.STREAM_HELPER_SHA,prior_failed_controller_path=r'C:\Flycast-Evidence\re4-dreamcast\texture21-benchmark-20261021\append1618-materialization-01\controller.json',prior_failed_controller_sha256='194ce0ef2d73a7407910d9376459897b5cc72c0b883b8ab515015dd0bce1d58c',metadata_root=meta,payload_roots=[r'\\wsl.localhost\Ubuntu-24.04\root\re4data\private\texture-append1760-20261022-v1-native-c',r'C:\Game Dev\Emulators\re4-assets-private\texture-append1760-20261022-v1-native-c'],expected=dict(sha256=w.PACK_SHA,bytes=w.PACK_BYTES,members=7293,mips_if_selected=1760,parent7151_byteexact=True,append142=True,index_sectors=57,data_offset=118784),aggregate_cap_bytes=w.CAP,runtime_floor_bytes=w.FLOOR,peer_reserved_bytes=w.PEER,inner_seconds=51,outer_seconds=130,required_environment={'PYTHONDONTWRITEBYTECODE':'1','PYTHONPYCACHEPREFIX':meta+r'\pycache'},pycache_prefix_absent_required=True,accounting='Eachfile max4KiBlogical/nativeallocated; strict1/50/120 fallback; no credits/allpartialscharged',source_only_holds=['All29worlds PRIVATE UNSELECTED; source792 default0/r11f+r200held','No fullpack/programme/image/guest/production/release/SD selection','Actual old1618/v1failedpartial/frozenv2/invalidCLI preserved; oldclosedcharge freshC only, no new-cap doublecharge/credit'])

def main():
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('--out',type=Path,required=True);a.add_argument('--controller-sha256',required=True);v=a.parse_args()
 if not w.re_hash(v.controller_sha256):raise ValueError('exact reviewed controller source SHA required')
 if not v.out.is_dir()or (v.out/'writer-plan.json').exists():raise FileExistsError('existing native143 source namespace and fresh writer-plan required')
 p=plan(v.controller_sha256)
 w.json_new(v.out/'writer-plan.json',p)
 print(json.dumps(dict(plan_sha256=w.sha(v.out/'writer-plan.json'),writer_sha256=w.sha(w.__file__))))
if __name__=='__main__':main()
