#!/usr/bin/env python3
"""Read selected existing target DWARF member offsets; never compiles or runs a guest."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess


def number(value):
    value=value.strip().split()[0]
    return int(value,16 if value.startswith('0x') else 10)


def parse(lines,wanted):
    dies=[];current=None
    for line in lines:
        m=re.match(r'\s*<(\d+)><([0-9a-f]+)>:.*\((DW_TAG_\w+)\)',line)
        if re.match(r'\s*<\d+><[0-9a-f]+>: Abbrev Number: 0',line):
            if current:dies.append(current)
            current=None
            continue
        if m:
            if current:dies.append(current)
            current={'depth':int(m[1]),'offset':m[2],'tag':m[3],'attrs':{}}
            continue
        if current:
            m=re.search(r'DW_AT_(\w+)\s*:\s*(.*)',line)
            if m:current['attrs'][m[1]]=m[2].strip()
    if current:dies.append(current)
    byoffset={die['offset']:i for i,die in enumerate(dies)}
    def promoted(index,seen=()):
        die=dies[index]
        if index in seen:raise ValueError('cyclic anonymous DWARF type')
        result={};depth=die['depth'];union=die['tag']=='DW_TAG_union_type'
        for child in dies[index+1:]:
            if child['depth']<=depth:break
            if child['tag']!='DW_TAG_member' or child['depth']!=depth+1:continue
            a=child['attrs'];location=a.get('data_member_location')
            if location is None and not union:continue
            offset=number(location) if location is not None else 0
            if 'name' in a:
                result[a['name'].split(': ')[-1]]=offset
            elif 'type' in a:
                ref=re.search(r'<0x([0-9a-f]+)>',a['type'])
                if not ref or ref[1] not in byoffset:raise ValueError('anonymous member type unavailable')
                for name,at in promoted(byoffset[ref[1]],seen+(index,)).items():
                    if name in result and result[name]!=offset+at:raise ValueError('conflicting promoted DWARF member '+name)
                    result[name]=offset+at
        return result
    results={}
    for i,die in enumerate(dies):
        if die['tag'] not in ['DW_TAG_structure_type','DW_TAG_class_type']:continue
        name=die['attrs'].get('name','').split(': ')[-1]
        if name not in wanted or 'byte_size' not in die['attrs']:continue
        members=promoted(i)
        if not members:continue
        record={'size':number(die['attrs']['byte_size']),'members':members,'DIE_offset':die['offset'],'declaration_file_index':die['attrs'].get('decl_file'),'declaration_line':die['attrs'].get('decl_line')}
        if name in results and (results[name]['members']!=members or results[name]['size']!=record['size']):raise ValueError('ambiguous complete DWARF type '+name)
        results[name]=record
    missing=set(wanted)-set(results)
    if missing:raise ValueError('missing complete DWARF type: '+','.join(sorted(missing)))
    return results


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--object',required=True);p.add_argument('--out',required=True)
    p.add_argument('--type',action='append',required=True);p.add_argument('--readelf',default='/opt/toolchains/dc/sh-elf/bin/sh-elf-readelf')
    a=p.parse_args()
    proc=subprocess.Popen([a.readelf,'--debug-dump=info',a.object],stdout=subprocess.PIPE,text=True)
    types=parse(proc.stdout,a.type)
    if proc.wait():raise SystemExit('target readelf failed')
    result={'object_sha256':hashlib.sha256(Path(a.object).read_bytes()).hexdigest(),'object':a.object,'types':types,
            'scope':'Existing target object DWARF offsets only; runtime access/admission/draw use not observed'}
    with Path(a.out).open('x') as out:json.dump(result,out,indent=2);out.write('\n')
    print(json.dumps({name:record['size'] for name,record in types.items()}))

if __name__=='__main__':main()
