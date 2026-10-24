"""Fail closed until exact reviewed future helper and host-compile pins bind."""
import hashlib,json
from pathlib import Path
EXPECTED_HELPER_SHA256='PENDING_FROZEN_RUNTIME_HELPER'
EXPECTED_RECEIPT_SHA256='PENDING_HOST_COMPILED_CAPABILITY'

def verify_capability(path):
    if EXPECTED_HELPER_SHA256.startswith('PENDING') or EXPECTED_RECEIPT_SHA256.startswith('PENDING'):raise ValueError('Future runtime helper and compiled capability are not frozen')
    path=Path(path);raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=EXPECTED_RECEIPT_SHA256:raise ValueError('Exact host capability receipt required')
    receipt=json.loads(raw)
    if receipt['status']!='HOST_COMPILED_CAPABILITY_ONLY' or receipt['runtime_admitted'] is not False or receipt['helper']['sha256']!=EXPECTED_HELPER_SHA256 or receipt['compiled_macros']!={'RE4DC_PS2_PVS_EFFECTIVE0_SOURCES':1,'RE4DC_PS2_WORLD_NONEMPTY_LOD':1,'RE4DC_MESH_LOD':1,'RE4DC_PS2_WORLD_MESH':1}:raise ValueError('Exact future effective0/NONEMPTY capability contract required')
    p=Path(receipt['helper']['path'])
    if hashlib.sha256(p.read_bytes()).hexdigest()!=EXPECTED_HELPER_SHA256:raise ValueError('Actual future source helper changed')
    return dict(receipt_path=str(path),receipt_sha256=EXPECTED_RECEIPT_SHA256,helper=receipt['helper'],status='REQUIRES_FUTURE_CAPABILITY_NO_CURRENT_RUNTIME_ADMISSION')
