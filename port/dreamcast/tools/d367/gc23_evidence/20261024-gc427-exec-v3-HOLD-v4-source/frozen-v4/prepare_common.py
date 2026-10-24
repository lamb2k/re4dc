"""Derive only the necessary V2 recovery binding/context changes from7b512."""
from pathlib import Path
import hashlib
HERE=Path(__file__).resolve().parent
old=HERE.parent/'kos-budget-retest-guest-prep-v1/common.py';raw=old.read_bytes()
# The preparation source verifies every original seal member before copying.
# Revalidate this particular source directly against the frozen original seal.
import json
assert hashlib.sha256((old.parent/'TOOLCHAIN-SEAL.json').read_bytes()).hexdigest()=='7b5120956b13f1d25f50280120686a8efe45ed70f09ca14042722cb4eaa9997e'
assert {'size':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}==json.loads((old.parent/'TOOLCHAIN-SEAL.json').read_bytes())['members']['common.py']
text=raw.decode();text=text.replace("'review-kos-budget-retest-media-poststage-v1','kos-budget-retest-guest-root-review-v1'","'review-kos-budget-retest-media-poststage-v2','kos-budget-retest-guest-root-review-v2'")
def replace_function(name,nextname,new):
 global text
 start=text.index('def '+name+'(');end=text.index('def '+nextname+'(',start)
 text=text[:start]+new+'\n\n'+text[end:]
replace_function('context','sealed',"""def context():
 assert sha(MEDIA/'TOOLCHAIN-SEAL.json')==MEDIA_SEAL
 pins=read(MEDIA/'TOOLCHAIN-SEAL.json')['members']
 for n,p in pins.items():verify(MEDIA/n,p)
 base=module('retest_stage_core',MEDIA/'core.py',pins['core.py']['sha256'])
 pin=read(HERE/'TOOLCHAIN-SEAL.json')['members']['recovery_context.py']
 recovery=module('recovery_context',HERE/'recovery_context.py',pin['sha256'])
 return recovery.adapt(base,sys.modules[__name__])""")
replace_function('capacity','metadata_guard',"""def capacity(k,required=None):
 return k.capacity(k.FLOOR if required is None else required)""")
text=text.replace("read(MEDIA/'GUEST-PROPOSAL.json')","read(HERE/'PLAN.json')")
replace_function('check_poststage','check_inputs',"""def check_poststage(g,k,arm,hash_tracks=True):
 return k.check_poststage(g,arm,hash_tracks)""")
token=" assert g['kit_sha256']==seal and g['media_kit_sha256']==MEDIA_SEAL"
assert text.count(token)==1
text=text.replace(token,token+"\n assert g['recovery_context']=='EXPLICIT_NEW_CURRENT_BASELINE_NO_OLD_HASH_RESTORATION'")
with (HERE/'common.py').open('xb') as f:f.write(text.encode())
