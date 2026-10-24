"""Verify archived Git LF blobs and reconstruct each physical source digest.

Does not import or execute any archived admission/runner/acceptance helper.
"""
import argparse,hashlib,json,pathlib,subprocess
sha=lambda b:hashlib.sha256(b).hexdigest()

def check_record(row,blob):
    if sha(blob)!=row['git_lf_sha256'] or len(blob)!=row['git_lf_bytes']:
        raise ValueError('Git blob differs: '+row['archive_path'])
    positions=set(row['physical_crlf_newline_ordinals'])
    if len(positions)!=len(row['physical_crlf_newline_ordinals']):raise ValueError('duplicate newline ordinal')
    output=bytearray();ordinal=0
    for byte in blob:
        if byte==10:
            if ordinal in positions:output.append(13)
            ordinal+=1
        output.append(byte)
    if any(n<0 or n>=ordinal for n in positions):raise ValueError('out-of-range newline ordinal')
    raw=bytes(output)
    if sha(raw)!=row['physical_sha256'] or len(raw)!=row['physical_bytes']:
        raise ValueError('Physical reconstruction differs: '+row['archive_path'])
    return raw

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--revision',default='INDEX');p.add_argument('--out',type=pathlib.Path);a=p.parse_args()
    here=pathlib.Path(__file__).resolve().parent
    repo=pathlib.Path(subprocess.check_output(['git','-C',str(here),'rev-parse','--show-toplevel'],text=True).strip())
    prefix=here.relative_to(repo).as_posix()
    mapping=json.loads((here/'EXPORT-MAP.json').read_text())
    results=[];seen=set();normalized=[]
    for row in mapping['files']:
        rel=pathlib.PurePosixPath(row['archive_path'])
        assert not rel.is_absolute() and '..' not in rel.parts and str(rel) not in seen
        assert rel.suffix in ('.py','.json','.md','.cfg'),rel
        seen.add(str(rel));spec=(':'+prefix+'/'+str(rel)) if a.revision=='INDEX' else a.revision+':'+prefix+'/'+str(rel)
        blob=subprocess.check_output(['git','-C',str(repo),'show',spec])
        assert b'\0' not in blob
        check_record(row,blob)
        if row['normalization']!='IDENTICAL':normalized.append((row,blob))
        results.append(dict(path=str(rel),git_lf_sha256=sha(blob),physical_sha256=row['physical_sha256'],physical_reconstructs=True))
    assert normalized,'actual normalized records are required for these controls'
    row,blob=normalized[0]
    mutants=0
    for mutant in (dict(row,git_lf_sha256='0'*64),dict(row,physical_crlf_newline_ordinals=[])):
        try:check_record(mutant,blob)
        except ValueError:mutants+=1
        else:raise AssertionError('broken digest/newline map accepted')
    report=dict(status='PASS_SOURCE_ONLY_EXPORT_GIT_AND_PHYSICAL_RECONSTRUCTION',revision=a.revision,
                physical_sources=len(results),normalized_sources=len(normalized),mutants_caught=mutants,
                snapshot_utc=mapping['snapshot_utc'],runtime_source_unchanged=mapping['runtime_source_unchanged'],
                archived_helpers_executed=False,SDK_guest=False,records=results)
    if a.out:
        with a.out.open('x') as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps({k:report[k] for k in ('status','revision','physical_sources','normalized_sources','mutants_caught')}))
if __name__=='__main__':main()
