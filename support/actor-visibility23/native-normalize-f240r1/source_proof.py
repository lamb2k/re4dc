"""Historical generated marker and separate literal-clean live source proof."""
import json,subprocess
TREE='/root/probe/codex-actor-visibility23-eligibility-witness-integration'
MARKER=TREE+'/port/dreamcast/game/obj'
TARGET='/root/probe/lanes/actor-visibility23-eligibility-witness-integration/on2/link-scratch'
RAW='?? port/dreamcast/game/obj\n'

def live_source():
 script="import pathlib,subprocess,json;p=pathlib.Path("+repr(MARKER)+");g=lambda a:subprocess.check_output(['git','-C',"+repr(TREE)+"]+a,text=True);print(json.dumps(dict(head=g(['rev-parse','HEAD']).strip(),raw_status=g(['status','--porcelain']),marker_exists=p.exists(),marker_symlink=p.is_symlink(),marker_tracked=bool(g(['ls-files','--','port/dreamcast/game/obj']).strip()))))"
 return json.loads(subprocess.check_output(['python3','-c',script]))

def validate(source,clean,final,retired,live,head,check):
 marker=source.get('approved_generated_marker',{})
 if source.get('source')!=head or source.get('clean')is not True or source.get('raw_git_status')!=RAW or marker.get('path')!=MARKER or marker.get('target')!=TARGET:raise ValueError('exact historical source marker proof required')
 if source.get('clean_scope')!='Tracked and untracked source, excluding ONLY exact main-approved generated game/obj symlink':raise ValueError('historical scope differs')
 exclude='/root/probe/lanes/actor-visibility23-eligibility-witness-integration/generated-build-exclude'
 if marker.get('command_scoped_exclude')!=exclude or marker.get('exclude_sha256')!='5c304378178027642241ebbc6a777b5c955dcd84a00d18021c2b00cf72390ac3' or check(dict(path=exclude,sha256=marker['exclude_sha256']))!=b'/port/dreamcast/game/obj\n':raise ValueError('exact command-scoped single-path exclude required')
 lines=clean.splitlines()
 if len(lines)!=4 or lines[:3]!=['HEAD '+head,'STATUS_PORCELAIN_RAW '+repr(RAW),"STATUS_SOURCE_SCOPED ''"]or not lines[3].startswith('REMOTE '+head+'\trefs/heads/'):raise ValueError('historical clean/remote evidence differs')
 if final.get('source')!=head or final.get('clean')is not True or final.get('only_owned_generated_marker_retired')is not True or final.get('link_scratch_preserved')!=TARGET or final.get('mapping_sha256')!='076a4856d715f1dd25f7bb966717d955cc543c056f09891ad48c57c7acb5542c' or final.get('runtime_admitted')is not False:raise ValueError('actual main final clean receipt differs')
 if live!=dict(head=head,raw_status='',marker_exists=False,marker_symlink=False,marker_tracked=False):raise ValueError('live source not literally clean with marker absent')
 return dict(live=live,historical_generated_marker_only=marker,final_literal_clean=True)
