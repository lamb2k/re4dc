"""Opt-in future effective0 discovery prerequisite; old pool is unchanged."""
import importlib.util,sys
from pathlib import Path
BASE=Path(__file__).resolve().parent.parent/'eligible'
sys.path[:0]=[str(BASE),str(BASE.parent)]
spec=importlib.util.spec_from_file_location('original_eligible_pool',BASE/'pool.py');original=importlib.util.module_from_spec(spec);spec.loader.exec_module(original)
from capability import verify_capability
ENABLED=False;CAPABILITY=None

def effective0_counts(counts):
    return bool(counts) and all(type(n)is int and 0<=n<=0xffffffff for n in counts) and counts[0]>0 and not any(counts[1:])

def configure(enabled=False,receipt=None):
    global ENABLED,CAPABILITY
    if type(enabled)is not bool:raise ValueError('Explicit boolean option required')
    if enabled and receipt is None:raise ValueError('Future compiled NONEMPTY1 capability receipt required')
    if not enabled and receipt is not None:raise ValueError('Capability receipt supplied without explicit option')
    CAPABILITY=verify_capability(receipt) if enabled else None;ENABLED=enabled

def capability_identity():return CAPABILITY

def source_allowed(source):
    if original.source_allowed(source):return True
    p=source['prerequisites'];counts=source.get('authored_meshlet_counts',[])
    if not ENABLED or CAPABILITY is None or source.get('level')!=0 or len(counts)!=p['level_count'] or not effective0_counts(counts):return False
    single=dict(source);single['prerequisites']=dict(p,level_count=1)
    return original.source_allowed(single)

class EligibleScene(original.EligibleScene):
    def add_source(self,source,vertices,triangles):
        if not source_allowed(source):self.refused+=1;return False
        self.add_let(source,vertices,triangles);return True
