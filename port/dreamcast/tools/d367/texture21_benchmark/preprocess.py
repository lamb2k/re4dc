#!/usr/bin/env python3
"""Replay selected *logged* target compile flags in preprocessor-only mode."""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import subprocess


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument('--repo',type=Path,required=True);a.add_argument('--build',type=Path,required=True)
    a.add_argument('--out',type=Path,required=True)
    a.add_argument('--compiler',default='/opt/toolchains/dc/sh-elf/bin/sh-elf-g++')
    a.add_argument('--source',action='append',required=True)
    v=a.parse_args();v.out.mkdir(parents=True,exist_ok=False)
    log=v.build/'build.log';lines=log.read_text(errors='replace').splitlines();records={}
    for source in v.source:
        if Path(source).is_absolute() or not (v.repo/'port/dreamcast/game'/source).resolve().is_relative_to(v.repo.resolve()):raise ValueError('source must remain inside the selected repository')
        matches=[]
        for line in lines:
            if line.startswith('kos-c++ ') and source in line:
                args=shlex.split(line)
                if '-c' in args and args[args.index('-c')+1]==source:matches.append(args)
        if len(matches)!=1:raise ValueError(f'expected one actual compile for {source}, found {len(matches)}')
        original=matches[0];args=[v.compiler];output=None;i=1
        while i<len(original):
            token=original[i]
            if token=='-o':output=Path(original[i+1]);i+=2;continue
            if token in ['-c','-MMD','-MP']:i+=1;continue
            args.append(token);i+=1
        if not output or not output.is_file():raise ValueError('original compiled object absent')
        args+=['-E','-dM']
        target=v.out/(source.replace('/','_')+'.macros')
        with target.open('xb') as out:subprocess.run(args,cwd=v.repo/'port/dreamcast/game',stdout=out,check=True)
        macros={}
        for line in target.read_text().splitlines():
            parts=line.split(maxsplit=2)
            if len(parts)>=2 and parts[0]=='#define':macros[parts[1]]=parts[2] if len(parts)==3 else ''
        records[source]={'logged_compile':original,'preprocess_command':args,'macros_sha256':sha(target),
                         'source_sha256':sha(v.repo/'port/dreamcast/game'/source),
                         'existing_object':str(output),'object_sha256':sha(output),
                         'selected_actual_defines':{k:val for k,val in macros.items() if any(s in k for s in ['SH4ZAM','ACTOR_PLAN','MIPMAP','ALIVE_CAP','ANIMALS_OFF','WINDOW_HOLD_RESTORE'])}}
    receipt={'build_log_sha256':sha(log),'compiler':v.compiler,'compiler_sha256':sha(v.compiler),
             'source_head':subprocess.check_output(['git','-C',str(v.repo),'rev-parse','HEAD'],text=True).strip(),
             'units':records,'scope':'actual preprocessor replay of retained compile commands; no object or ELF rebuilt'}
    with (v.out/'receipt.json').open('x') as out:json.dump(receipt,out,indent=2);out.write('\n')
    print(json.dumps({s:r['selected_actual_defines'] for s,r in records.items()},indent=2))

if __name__=='__main__':main()
