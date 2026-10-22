"""Native FILE_STANDARD_INFO allocation for OWNED fixture outputs only."""
from pathlib import Path

def file_charge(api,path):
    # Attribute-only, share writers: inventory may be truncated/written concurrently.
    # OPEN_REPARSE_POINT avoids following a substituted final component.
    h=api.k.CreateFileW(str(path),0x80,7,None,3,0x00200000,None)
    if h in (None,0,-1,0xffffffffffffffff):api.checked(False)
    try:
        value=api.stat(h)
        if value['attributes']&0x400 or value['deleted'] or value['directory']:raise RuntimeError('owned allocation file replaced/deleted/directory/reparse')
        if value['size']<0 or value['allocated']<0:raise RuntimeError('invalid native allocation extent')
        return max(value['size'],value['allocated'])
    finally:api.close(h)

def measure(api,root):
    total=4096 # Conservative declared root directory charge; not GetCompressedFileSize.
    for path in Path(root).rglob('*'):
        if path.is_dir():total+=4096
        else:total+=file_charge(api,path)
    return total
