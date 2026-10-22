from pathlib import Path
import subprocess,json,os
R=Path('/root/probe/codex-backface-sh4zam-review');D=R/'port/dreamcast/tools/d367/backface_sh4zam_review';C=Path('/mnt/c/Game Dev/Emulators/codex-lanes/backface-sh4zam-review')
def files(p):return[p for p in p.rglob('*')if p.is_file()]
repo=files(D);mirror=files(C)
objects=subprocess.check_output(['git','-C',str(R),'rev-list','--objects','HEAD','^5fa6add0e'],text=True).splitlines();ids=[x.split()[0]for x in objects]
info=subprocess.check_output(['git','-C',str(R),'cat-file','--batch-check=%(objectsize:disk)'],input='\n'.join(ids)+'\n',text=True).splitlines();disk=[int(x)for x in info]
print(json.dumps(dict(repo_files=len(repo),repo_allocated=sum(x.stat().st_blocks*512 for x in repo),repo_logical=sum(x.stat().st_size for x in repo),mirror_files=len(mirror),mirror_cluster_upper=sum((x.stat().st_size+4095)//4096*4096 for x in mirror),new_git_objects=len(ids),new_git_loose_upper=sum((x+4095)//4096*4096 for x in disk),scope='Current review files plus C mirror rounded4KiB, new own Git objects since prior sealed baseline; prior metadata outside these paths may add cost'),indent=2))
