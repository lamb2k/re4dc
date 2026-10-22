from pathlib import Path
import tempfile,subprocess,argparse,hashlib,json,re
T=Path(__file__).resolve().parent;R=T.parents[4]
def main():
 p=argparse.ArgumentParser();p.add_argument('--all',action='store_true');p.add_argument('--on',action='store_true');args=p.parse_args()
 source=R/'port/dreamcast/game/platform/native_ui.cpp';s=source.read_text();body=s[s.index('Entry* load(const Re4dcUiImage&'):s.index('#undef RE4DC_OPEN_PACKAGE\n')]
 with tempfile.TemporaryDirectory(prefix='cache21-payload-')as d:
  d=Path(d);(d/'actual_load.inc').write_text(body)
  command=['g++','-std=c++17','-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all','-Wno-int-to-pointer-cast','-DRE4DC_TEX_PAYLOAD_RETRY='+str(int(args.on)),'-I'+str(d),'-I'+str(R/'port/dreamcast/game/platform/include'),str(T/'load_probe.cpp'),'-o',str(d/'probe')]
  subprocess.run(command,check=True);result=subprocess.check_output([str(d/'probe')],text=True)
  if args.all:
   policy=d/'policy';subprocess.run(['g++','-std=c++17','-O1','-fsanitize=undefined','-fno-sanitize-recover=all','-I'+str(R/'port/dreamcast/game/platform/include'),str(T/'policy_probe.cpp'),'-o',str(policy)],check=True);result+=subprocess.check_output([str(policy)],text=True)
  if args.all:
   body_interleaved=body.replace('    const bool in_pack=pack==texpack::kFound;', '    const bool in_pack=pack==texpack::kFound;\n    if(after_find){auto callback=after_find;after_find=nullptr;callback();}')
   (d/'actual_load_interleaved.inc').write_text(body_interleaved)
   inter=d/'interleaved';subprocess.run(['g++','-std=c++17','-O1','-fsanitize=undefined','-fno-sanitize-recover=all','-DRE4DC_TEX_PAYLOAD_RETRY='+str(int(args.on)),'-I'+str(d),'-I'+str(R/'port/dreamcast/game/platform/include'),str(T/'interleaved_probe.cpp'),'-o',str(inter)],check=True);result+=subprocess.check_output([str(inter)],text=True)
   index=d/'index';subprocess.run(['g++','-std=c++17','-O1','-fsanitize=undefined','-fno-sanitize-recover=all','-DRE4DC_TEX_PAYLOAD_RETRY='+str(int(args.on)),'-I'+str(R/'port/dreamcast/game/platform/include'),str(T/'index_probe.cpp'),'-o',str(index)],check=True);result+=subprocess.check_output([str(index)],text=True)
   helper=(R/'port/dreamcast/game/platform/include/texpack_payload_retry.inc').read_text();package=(R/'port/dreamcast/room/texture_package.cpp').read_text()
   for literal in re.findall(r'"([^"\n]+)"',helper[helper.index('static const char* const errors[]'):]):
    assert '"'+literal+'"' in package,literal
   result+='WHITELIST_SOURCE_LITERALS PASS\n'
  print(json.dumps({'actual_source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'mode':int(args.on),'compiler':command,'output':result},indent=2))
if __name__=='__main__':main()
