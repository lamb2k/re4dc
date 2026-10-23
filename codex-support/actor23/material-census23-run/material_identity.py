"""Receipt identity is native file identity plus advertised and actual contents."""
import hashlib
def require_bound_receipt(actual,expected,native_path):
 left=native_path(actual['path']);right=native_path(expected['path'])
 if any(p.is_symlink() or not p.is_file() for p in (left,right)):raise ValueError('ordinary bound receipt required')
 if left.resolve(strict=True)!=right.resolve(strict=True) or not left.samefile(right):raise ValueError('bound receipt path identity differs')
 if actual.get('sha256')!=expected['sha256'] or hashlib.sha256(left.read_bytes()).hexdigest()!=expected['sha256']:raise ValueError('bound receipt content identity differs')
 return left
