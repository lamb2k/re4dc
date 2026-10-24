"""Point-eye discovery rays over real triangles. Never a coverage certificate."""
from array import array
import math

MAX_TRIANGLES=200000
MAX_RAYS=110000
FIELDS=('placement','field','owner','part','cluster','level','meshlet','triangle','i0','i1','i2')

def sub(a,b):return tuple(a[i]-b[i] for i in range(3))
def dot(a,b):return sum(a[i]*b[i] for i in range(3))
def cross(a,b):return(a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def samples(box):
    lo,hi=box
    if any(not math.isfinite(v) for b in box for v in b) or any(lo[k]>hi[k] for k in range(3)):raise ValueError('invalid target box')
    from itertools import product
    return sorted(set(product(*[(lo[k],(lo[k]+hi[k])/2,hi[k]) for k in range(3)])))

class Scene:
    def __init__(self):
        self.xyz=array('d');self.meta=array('I');self.patch=array('I');self.patches=[]
        self.boxes=array('d');self.nodes=[];self.order=array('I');self.rays=0;self.degenerate=0

    def add_let(self,source,vertices,triangles):
        start=len(self.patch);local=[]
        for ordinal,indices in enumerate(triangles):
            if len(indices)!=3 or any(i<0 or i>=len(vertices) for i in indices):raise ValueError('source index extent')
            tri=[vertices[i] for i in indices]
            if any(not math.isfinite(v) for p in tri for v in p):raise ValueError('nonfinite source')
            if not dot(cross(sub(tri[1],tri[0]),sub(tri[2],tri[0])),cross(sub(tri[1],tri[0]),sub(tri[2],tri[0]))):
                self.degenerate+=1;continue
            if len(self.patch)>=MAX_TRIANGLES:raise ValueError('full scene exceeds triangle budget; never truncate')
            self.xyz.extend(v for point in tri for v in point)
            self.meta.extend([source[k] for k in FIELDS[:7]]+[ordinal,*indices])
            self.patch.append(0);local.append(tuple(indices))
            self.boxes.extend([min(p[k] for p in tri) for k in range(3)]+[max(p[k] for p in tri) for k in range(3)])
        # Exact cache-index adjacency within this actual whole meshlet only.
        # Same-position seams across other cache/owner/LOD/material cohorts are
        # never welded. The real union may retain holes and nonplanar faces.
        edges={};parent=list(range(len(local)))
        def find(i):
            while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
            return i
        for i,tri in enumerate(local):
            for k in range(3):
                a,b=tri[k],tri[(k+1)%3];edges.setdefault(tuple(sorted((a,b))),[]).append((i,a<b))
        for uses in edges.values():
            for i,_ in uses[1:]:parent[find(i)]=find(uses[0][0])
        groups={}
        for i in range(len(local)):groups.setdefault(find(i),[]).append(i)
        for members in groups.values():
            belongs=set(members);related=[v for v in edges.values() if v[0][0] in belongs]
            pid=len(self.patches)
            self.patches.append(dict(source=source,triangles=[start+i for i in members],
                boundary_edges=sum(len(v)==1 for v in related),nonmanifold_edges=sum(len(v)>2 for v in related),
                winding_conflicts=sum(len(v)==2 and v[0][1]==v[1][1] for v in related),
                adjacency='actual shared corner indices in one whole meshlet; no cross-cohort weld',
                connected=True,continuous_coverage_proven=False))
            for i in members:self.patch[start+i]=pid

    def build(self):
        if not self.patch:raise ValueError('empty eligible scene')
        def build(ids):
            lo=tuple(min(self.boxes[6*i+k] for i in ids) for k in range(3))
            hi=tuple(max(self.boxes[6*i+3+k] for i in ids) for k in range(3))
            node=len(self.nodes);self.nodes.append(None)
            if len(ids)<=8:
                begin=len(self.order);self.order.extend(ids);self.nodes[node]=(lo,hi,-1,-1,begin,len(ids))
            else:
                axis=max(range(3),key=lambda k:hi[k]-lo[k]);ids.sort(key=lambda i:self.boxes[6*i+axis]+self.boxes[6*i+3+axis])
                half=len(ids)//2;left=build(ids[:half]);right=build(ids[half:]);self.nodes[node]=(lo,hi,left,right,0,0)
            return node
        build(list(range(len(self.patch))))

    @staticmethod
    def ray_box(origin,direction,lo,hi,limit):
        lower=0.0;upper=limit
        for k in range(3):
            if abs(direction[k])<1e-18:
                if origin[k]<lo[k] or origin[k]>hi[k]:return None
            else:
                a=(lo[k]-origin[k])/direction[k];b=(hi[k]-origin[k])/direction[k]
                lower=max(lower,min(a,b));upper=min(upper,max(a,b))
                if lower>upper:return None
        return lower

    def ray_triangle(self,index,eye,direction):
        offset=9*index;v=tuple(self.xyz[offset+k] for k in range(3))
        e1=tuple(self.xyz[offset+3+k]-v[k] for k in range(3));e2=tuple(self.xyz[offset+6+k]-v[k] for k in range(3))
        h=cross(direction,e2);det=dot(e1,h)
        scale=math.sqrt(max(0,dot(e1,e1)*dot(e2,e2)*dot(direction,direction)))
        if abs(det)<=1e-12*scale:return None
        s=sub(eye,v);u=dot(s,h)/det;q=cross(s,e1);w=dot(direction,q)/det;t=dot(e2,q)/det
        if u < -1e-10 or w < -1e-10 or u+w>1+1e-10 or not 0<t<1:return None
        return t,min(u,w,1-u-w)<1e-9,1 if det>0 else -1

    def nearest(self,eye,target,exclude_cluster=None,exclude_meshlet=None,near_mm=100.0,source_before=None):
        self.rays+=1
        if self.rays>MAX_RAYS:raise ValueError('ray budget exceeded; never silently omit targets')
        direction=sub(target,eye);length=math.sqrt(dot(direction,direction))
        if not math.isfinite(length) or length<=near_mm:return dict(kind='near_or_zero_target',hit=None)
        best=1.0-1.0/length;hit=None;stack=[0]
        while stack:
            ni=stack.pop();lo,hi,left,right,start,count=self.nodes[ni]
            if self.ray_box(eye,direction,lo,hi,best) is None:continue
            if left>=0:stack.extend((left,right));continue
            for index in self.order[start:start+count]:
                offset=11*index;placement=self.meta[offset];cluster=self.meta[offset+4];meshlet=self.meta[offset+6]
                if exclude_cluster==(placement,cluster) or exclude_meshlet==(placement,cluster,meshlet) or (source_before is not None and placement>=source_before):continue
                result=self.ray_triangle(index,eye,direction)
                if result and result[0]<best:
                    best=result[0];hit=dict(triangle=index,patch=int(self.patch[index]),t=best,distance_mm=best*length,
                        source_edge_contact=result[1],facing_sign=result[2])
        if hit is None:return dict(kind='no_prior_hit',hit=None)
        return dict(kind='nearest_inside_near' if hit['distance_mm']<near_mm else 'prior_triangle_hit',hit=hit)

    def provenance(self,index):return dict(zip(FIELDS,self.meta[11*index:11*index+11]))


def discover(scene,eye,box,exclude_cluster=None,exclude_meshlet=None,source_before=None):
    rows=[];patches={}
    for point in samples(box):
        row=scene.nearest(eye,point,exclude_cluster,exclude_meshlet,source_before=source_before);rows.append(row)
        if row['kind']=='prior_triangle_hit':
            pid=row['hit']['patch'];patches[pid]=patches.get(pid,0)+1
    usable=sum(patches.values());dominant=max(patches,key=patches.get) if patches else None
    return dict(sample_count=len(rows),usable_hit_count=usable,sample_miss_count=sum(r['kind']=='no_prior_hit' for r in rows),
                near_blocker_count=sum(r['kind'] in ('near_or_zero_target','nearest_inside_near') for r in rows),
                source_edge_contacts=sum(bool(r['hit'] and r['hit']['source_edge_contact']) for r in rows),
                sampled_patch_hit_counts=patches,dominant_patch=dominant,dominant_patch_hits=0 if dominant is None else patches[dominant],
                all_fixed_samples_hit=usable==len(rows),rays=rows,
                discovery_only=True,full_domain_coverage_proven=False,certificate=None,
                runtime_admitted=False,modelled_ms=None)
