"""Only metadata-eligible source triangles may enter this discovery BVH."""
import sys,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from rays import Scene,dot,sub

def source_allowed(source):
    p=source['prerequisites']
    return (p['static'] and p['unconditional'] and p['nonsingular'] and p['level_count']==1 and p['pass']==0 and p['cull'] in (0,2) and not p['vertex_alpha'] and p['material_eligible'])
class EligibleScene(Scene):
    def __init__(self,token):super().__init__();self.token=token;self.refused=0
    def add_source(self,source,vertices,triangles):
        if not source_allowed(source):self.refused+=1;return False
        self.add_let(source,vertices,triangles);return True
    def nearest(self,eye,target,exclude_cluster=None,exclude_meshlet=None,near_mm=100.,source_before=None):
        self.token.take()
        if source_before is None:raise ValueError('Traversal source placement boundary required')
        return super().nearest(eye,target,exclude_cluster,exclude_meshlet,near_mm,source_before)
    def brute(self,eye,target,exclude_cluster=None,source_before=None,near_mm=100.):
        self.token.take()
        if source_before is None:raise ValueError('Brute source placement boundary required')
        direction=sub(target,eye);length=math.sqrt(dot(direction,direction))
        if length<=near_mm:return None
        best=1-1/length;hit=None
        for i in range(len(self.patch)):
            p=self.provenance(i)
            if p['placement']>=source_before or exclude_cluster==(p['placement'],p['cluster']):continue
            q=self.ray_triangle(i,eye,direction)
            if q and q[0]<best:best=q[0];hit=(i,best)
        return hit
