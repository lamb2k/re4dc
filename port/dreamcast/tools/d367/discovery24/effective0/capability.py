"""Fail closed until exact reviewed future helper and host-compile pins bind."""
import hashlib,json
from pathlib import Path
EXPECTED_HELPER_SHA256='4d01f2bbe696500697c793c2bd40e54be0ead4aa40d93219157e167b5bbfc1da'
EXPECTED_RECEIPT_SHA256='62f000e90cfccb20d734d1f9a1e6d0c47b33fe039f4c4f836b40d37e09b2f06d'

def verify_capability(path):
    if EXPECTED_HELPER_SHA256.startswith('PENDING') or EXPECTED_RECEIPT_SHA256.startswith('PENDING'):raise ValueError('Future runtime helper and compiled capability are not frozen')
    path=Path(path);raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=EXPECTED_RECEIPT_SHA256:raise ValueError('Exact host capability receipt required')
    receipt=json.loads(raw)
    if receipt['status']!='HOST_COMPILED_CAPABILITY_ONLY' or receipt['runtime_admitted'] is not False or receipt['helper']['sha256']!=EXPECTED_HELPER_SHA256 or receipt['compiled_macros']!={'RE4DC_PS2_PVS_EFFECTIVE0_SOURCES':1,'RE4DC_PS2_WORLD_NONEMPTY_LOD':1,'RE4DC_MESH_LOD':1,'RE4DC_PS2_WORLD_MESH':1}:raise ValueError('Exact future effective0/NONEMPTY capability contract required')
    for name in ('helper','nonempty','helper_block','compiler','binary','harness','actual_audit','actual_mesh'):
        pin=receipt[name];p=Path(pin['path']);raw=p.read_bytes()
        if len(raw)!=pin['bytes'] or hashlib.sha256(raw).hexdigest()!=pin['sha256']:raise ValueError('Actual compiled capability member changed '+name)
    if receipt['actual_clusters']!=95 or receipt['all_valid_raw_lods']!=190 or len(receipt['missing_macro_refusals'])!=4:raise ValueError('Complete actual cluster/guard controls required')
    return dict(receipt_path=str(path),receipt_sha256=EXPECTED_RECEIPT_SHA256,helper=receipt['helper'],status='REQUIRES_FUTURE_CAPABILITY_NO_CURRENT_RUNTIME_ADMISSION')
