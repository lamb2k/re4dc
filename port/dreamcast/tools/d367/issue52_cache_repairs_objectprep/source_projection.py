"""Private previous-TU source view helper for a separately allocated future runner.
Import only. No main/CLI; source-only preparation never calls materialize().
"""
from pathlib import Path
import gzip,hashlib,subprocess

def materialize(candidate, source_commit, destination, unit, metadata):
    T=Path(candidate).resolve(); D=Path(destination); M=Path(metadata)
    B=unit; rel=Path(B['relative_source']); cwdrel=Path('port/dreamcast/game')
    if subprocess.check_output(['git','rev-parse','HEAD'],cwd=T,text=True).strip()!=source_commit:
        raise RuntimeError('candidate source drift')
    if subprocess.check_output(['git','status','--porcelain'],cwd=T,text=True).strip():
        raise RuntimeError('candidate dirty')
    if not D.is_absolute() or D.exists() or D.is_symlink():
        raise RuntimeError('fresh private view required')
    # Restrict mutations to the one reserved future object tree's projections.
    expected=Path('/root/probe/issue52-cache-repairs-sh4-objects-20261022-01/projections')
    if D.parent!=expected or D.name not in ('sscrn','reset') or not expected.is_dir() or expected.is_symlink() or expected.resolve()!=expected:
        raise RuntimeError('projection ownership mismatch')
    old=gzip.decompress((M/B['compressed_source']).read_bytes())
    if hashlib.sha256(old).hexdigest()!=B['sha256']:
        raise RuntimeError('previous full-TU payload disagreement')
    if old!=subprocess.check_output(['git','show',B['commit']+':'+str(rel)],cwd=T):
        raise RuntimeError('previous full-TU Git disagreement')
    # Both cwd and source ancestors must stay real. A symlinked main.cpp cwd
    # would resolve ../../../src/game/main.cpp back to the live source tree.
    real={Path('.')}
    for leaf in (rel.parent,cwdrel):
        real.add(leaf)
        real.update(leaf.parents)
    D.mkdir()
    def fill(r):
        for child in sorted((T/r).iterdir()):
            q=r/child.name; out=D/q
            if child.name=='.git' and r==Path('.'):
                continue
            if q==rel:
                out.write_bytes(old)
            elif q in real:
                if not child.is_dir() or child.is_symlink():
                    raise RuntimeError('unexpected ancestor shape '+str(child))
                out.mkdir(); fill(q)
            else:
                out.symlink_to(child,target_is_directory=child.is_dir())
    fill(Path('.'))
    argsource='sscrn_bridge.cpp' if D.name=='sscrn' else '../../../src/game/main.cpp'
    selected=(D/cwdrel/argsource).resolve()
    if selected!=D/rel or selected.is_symlink() or selected.read_bytes()!=old:
        raise RuntimeError('relative source escaped private previous-TU view')
    rows=[]
    for p in sorted(D.rglob('*')):
        # Do not recursively follow directory symlinks; pathlib rglob respects it.
        rows.append(dict(path=str(p),symlink=p.is_symlink(),target=str(p.resolve()),allocated_bytes=p.lstat().st_blocks*512))
    # Make real files/directories read-only after materialization. The allocated
    # runner must never chmod through symlinks or delete evidence on failure.
    for p in sorted((p for p in D.rglob('*') if not p.is_symlink()),key=lambda p:len(p.parts),reverse=True):
        p.chmod(0o555 if p.is_dir() else 0o444)
    D.chmod(0o555)
    if subprocess.check_output(['git','status','--porcelain'],cwd=T,text=True).strip():
        raise RuntimeError('candidate changed during source view creation')
    return dict(cwd=str(D/cwdrel),source=str(selected),source_sha256=B['sha256'],inventory=rows)