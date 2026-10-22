#!/usr/bin/env python3
"""Replay every geometric certificate from current immutable package bytes.

No frame/runtime admission is inferred. Usage: pvs_verify.py PACKAGE WORK ROOM
"""
import hashlib,json,sys
from pathlib import Path
import numpy as np
from pvs_emit import load_cells,load_inst
from pvs_prove import triangle_hides,quad_hides
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'interior'))
from r4im import Pkg


def verify(pkgdir,work,room):
    pkgdir,work=Path(pkgdir),Path(work)
    R=json.loads((work/'proof.json').read_text())
    assert R['room']==room and R['runtime_admitted'] is False
    for name,expected in R['input_hashes'].items():assert hashlib.sha256((pkgdir/name).read_bytes()).hexdigest()==expected,name
    for name,expected in R['hashes'].items():assert hashlib.sha256((work/name).read_bytes()).hexdigest()==expected,name
    p=Pkg(pkgdir/'ps2-world.re4mesh',pkgdir/'ps2-world.r4pw')
    C,I=load_cells(work),load_inst(work);rows=list(p.iter_clusters())
    margin=R['vertex_uncertainty_mm']
    lo,hi=[],[]
    for pi,part,cl,_,_,_,_ in rows:
        lv=[p.cluster_tris_world(pi,cl,l).reshape(-1,3) for l in range(p.clusters[cl]['level_count'])]
        pts=np.concatenate(lv)
        lo.append(np.nextafter(pts.min(0)-margin,-np.inf) if len(pts) else np.full(3,-1e9))
        hi.append(np.nextafter(pts.max(0)+margin,np.inf) if len(pts) else np.full(3,1e9))
    lo,hi=np.array(lo),np.array(hi)
    for key,D in R['used_occluders'].items():
        pi,part,cl,pas,cull,_,_=rows[D['instance']]
        assert [pi,part,cl]==[D['placement_index'],D['part'],D['cluster']]
        assert pas==0 and cull==D['cull'] and not I['dyn'][D['instance']]
        if 'pair' not in D:
            assert p.clusters[cl]['level_count']==1
            actual=p.cluster_tris_world(pi,cl,0)[D['triangle_index']]
            assert np.array_equal(actual,np.array(D['triangle']))
        else:
            panels=D['pair']['all_lod_panels']
            assert len(panels)==p.clusters[cl]['level_count']
            for level,Q in enumerate(panels):
                assert Q['level']==level
                first,count,_=p.levels[p.clusters[cl]['first_level']+level]
                assert first<=Q['meshlet']<first+count
                gc,indices=p.let_tris(Q['meshlet']);M=p.wq(p.placements[pi])
                world=gc[:,:3].astype(np.float64)@M[:,:3].T+M[:,3]
                for ti,ix in zip(Q['triangle_indices'],Q['corner_indices']):assert list(indices[ti])==ix
                assert len(set(Q['corner_indices'][0])&set(Q['corner_indices'][1]))==2
                assert np.array_equal(world[np.array(Q['corner_indices'])],Q['triangles'])
                assert np.array_equal(world[Q['boundary_corner_indices']],Q['boundary'])
    expected=np.ones((C['nx']*C['nz'],C['ninst']),bool)
    seen=set()
    for cell,target,dep in R['cell_target_proofs']:
        assert (cell,target) not in seen;seen.add((cell,target))
        assert C['has'][cell] and not I['dyn'][target] and I['pas'][target]==0
        assert target not in R['pinned_instances']
        assert rows[target][0]>R['opaque_prefix_max_placement']
        ix,iz=cell%C['nx'],cell//C['nx']
        elo=np.array([C['x0']+ix*C['cell'],np.floor((C['ylo'][cell]-1000)/100)*100,C['z0']+iz*C['cell']])-32.
        ehi=np.array([C['x0']+(ix+1)*C['cell'],np.ceil((C['yhi'][cell]+1000)/100)*100,C['z0']+(iz+1)*C['cell']])+32.
        D=R['used_occluders'][str(dep)]
        if 'pair' in D:
            assert all(quad_hides(Q['triangles'],Q['boundary'],elo,ehi,lo[target],hi[target],two_sided=D['cull']==0,vertex_error=margin,clearance=2000.) for Q in D['pair']['all_lod_panels'])
        else:assert triangle_hides(D['triangle'],elo,ehi,lo[target],hi[target],two_sided=D['cull']==0,vertex_error=margin,clearance=2000.)
        expected[cell,target]=False
    raw=np.frombuffer((work/'proof-bits.bin').read_bytes(),np.uint8).reshape(-1,C['nb'])
    actual=np.unpackbits(raw,axis=1,bitorder='little')[:,:C['ninst']].astype(bool)
    assert np.array_equal(actual,expected)
    result=dict(room=room,replayed_proofs=len(seen),dependencies=len(R['used_occluders']),runtime_admitted=False,status='geometric candidate replay passed')
    (work/'replay.json').write_text(json.dumps(result,indent=1)+'\n')
    print(json.dumps(result))


if __name__=='__main__':verify(sys.argv[1],sys.argv[2],int(sys.argv[3],16))
