"""Bounded offline stream batching; retains immutable per-member verification."""
from collections import Counter
from contextlib import ExitStack
import hashlib
import os
from pathlib import Path
import struct
import zlib


def coalesce(blocks, chunk=1048576):
    """At most one chunk buffered; close the upstream generator on failure."""
    if type(chunk) is not int or not 1 <= chunk <= 1048576:
        raise ValueError('bounded positive chunk required')
    pending=bytearray()
    iterator=iter(blocks)
    try:
        for block in iterator:
            view=memoryview(block)
            while view:
                count=min(chunk-len(pending),len(view))
                pending.extend(view[:count]);view=view[count:]
                if len(pending)==chunk:
                    yield bytes(pending)
                    pending.clear()
        if pending:
            yield bytes(pending)
    finally:
        close=getattr(iterator,'close',None)
        if close:
            close()


def source_stream(head,index,rows,guard,*,safe_path,chunk=1048576,max_shared=8,opener=None):
    """Validate each source once; hold only repeatedly used read-only files.

    Each member's exact SHA/descriptor/body CRC is checked before advancing.
    A retained descriptor pins repeated pack reads across path replacement;
    fstat checks its immutable identity/size/mtime at closure. Output writes,
    accounting, publication and whole-pack readback remain the caller's job.
    """
    if type(chunk) is not int or not 1 <= chunk <= 1048576:
        raise ValueError('bounded positive chunk required')
    if type(max_shared) is not int or not 0 <= max_shared <= 8:
        raise ValueError('bounded shared reader count required')
    counts=Counter((Path(r['path']),Path(r['source_root'])) for r in rows)
    shared={key for key,n in counts.items() if n>1}
    if len(shared)>max_shared:
        raise ValueError('too many repeated input files')
    open_read=opener or (lambda path:path.open('rb'))
    def identity(file):
        s=os.fstat(file.fileno())
        return s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns
    def validated(key):
        path,root=key
        safe_path(path,root)
        if path.is_symlink():
            raise ValueError('symlink source refused')
        return path
    with ExitStack() as held:
        readers={}
        try:
            yield head
            yield index
            for r in rows:
                key=Path(r['path']),Path(r['source_root'])
                with ExitStack() as once:
                    if key in shared:
                        if key not in readers:
                            file=held.enter_context(open_read(validated(key)))
                            readers[key]=(file,identity(file))
                        src=readers[key][0]
                    else:
                        src=once.enter_context(open_read(validated(key)))
                    src.seek(r['source_offset'])
                    digest=hashlib.sha256();crc=0;done=0
                    while done<r['bytes']:
                        guard.check()
                        block=src.read(min(chunk,r['bytes']-done))
                        if not block:
                            raise ValueError('source member truncated')
                        if done==0 and r.get('descriptor_hex') is not None:
                            if len(block)<144 or block[:8]!=b'RE4DCTX\0' or block[48:144].hex()!=r['descriptor_hex'] or struct.unpack_from('<I',block,36)[0]!=r['body_crc32']:
                                raise ValueError('sealed append descriptor/header changed')
                        if r.get('descriptor_hex') is not None:
                            crc=zlib.crc32(block[max(0,48-done):],crc)
                        digest.update(block);done+=len(block)
                        yield block
                    if digest.hexdigest()!=r['sha256'] or (r.get('descriptor_hex') is not None and crc&0xffffffff!=r['body_crc32']):
                        raise ValueError('immutable member SHA/bodyCRC changed')
                if r['bytes']%2048:
                    yield bytes((-r['bytes'])%2048)
        finally:
            for file,before in readers.values():
                if identity(file)!=before:
                    raise ValueError('retained source file identity/size/mtime changed')
