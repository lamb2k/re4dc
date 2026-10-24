"""Immutable reviewed source references; historical proofs are not current-target gates."""
from pathlib import Path
import hashlib,subprocess
ROOT=Path(__file__).resolve().parents[5]
GC_UNIT="427784b1f48aa30742850bb5025925ab619b740e"
GC_COMPOSITION="c2f9ba8cbcebe30a218fe4fb6cf9ecd2305d853e"
PVS_COMPOSITION="8ce5ee2d00027268c3e69c9c300b819c1b14c63f"
CLOUD_INTEGRATION="9f6a25c61df6ad635c46e837b2371fc8b523ada6"
PINS={('427784b1f48aa30742850bb5025925ab619b740e', 'platform/native_ui.cpp'): 'df4157517b49e5ae6ea0f352863a576d58deb16f5c2fe9cabbab3c5552ec0f85', ('c2f9ba8cbcebe30a218fe4fb6cf9ecd2305d853e', 'ui_bridge.cpp'): 'cb2bd2ca4ace0abf7cc33719ec3f4cc9b4b24ba6bca7c7ddec6d64dd3a6beeb8', ('427784b1f48aa30742850bb5025925ab619b740e', 'platform/native_static.cpp'): 'd0a43e079d22febbbf87cc7ef042bb3f43bac0ad4c3cb8881cdf0d97fec6bcb3', ('427784b1f48aa30742850bb5025925ab619b740e', 'platform/far_shell.inc'): '4ce2055d32f28a37536b1bbfd6bacfba71763efb26845df9f3c76a88318e0822', ('427784b1f48aa30742850bb5025925ab619b740e', 'platform/room_file.c'): 'e8f96e63390271f55fc349350352293fad6d64f2cea974e530b9e498a9ff65d6', ('8ce5ee2d00027268c3e69c9c300b819c1b14c63f', 'platform/native_static.cpp'): '993a1e7cba8f06f4c34b59d38b1efdeecf6985a19842df3f4fa60fd90c6f5fc4', ('8ce5ee2d00027268c3e69c9c300b819c1b14c63f', 'platform/far_shell.inc'): '4ce2055d32f28a37536b1bbfd6bacfba71763efb26845df9f3c76a88318e0822', ('8ce5ee2d00027268c3e69c9c300b819c1b14c63f', 'platform/room_file.c'): 'e8f96e63390271f55fc349350352293fad6d64f2cea974e530b9e498a9ff65d6', ('9f6a25c61df6ad635c46e837b2371fc8b523ada6', 'platform/native_ui.cpp'): '981a19fc92be3833e4b897116b3f58539243372e6be3794a6e2abaea1584914e', ('9f6a25c61df6ad635c46e837b2371fc8b523ada6', 'platform/native_actor_fast.cpp'): 'c054fcd63ec837c45eeea6755859f158b4762ca70a1944d5439b383fda75b544', ('9f6a25c61df6ad635c46e837b2371fc8b523ada6', 'ui_bridge.cpp'): '6658d94417839b71d212f9a22a6f8397cee958e5e2bc03e0135bc9380f3e6171'}
PINS[(CLOUD_INTEGRATION,'src/game/motion.cpp')]='63e72196ab98e230d3dd14b7ad7328433a63e44d4c0406227374cd9a5b522a8f'

def frozen_source(revision,path):
    expected=PINS[(revision,path)]
    raw=subprocess.check_output(['git','-C',str(ROOT),'show',revision+':'+(path if path.startswith('src/') else 'port/dreamcast/game/'+path)])
    assert hashlib.sha256(raw).hexdigest()==expected,('Frozen source identity changed',revision,path)
    return raw.decode('utf-8')
