#!/usr/bin/env python3
"""Synthetic, production-adopted selection cost families; no game assets.

The repeated partial-group family has four three-corner groups per meshlet.
Box-inside/outside controls use a deliberately unselected coarse LOD to widen
the cluster bounds, so the cluster stays partial while selected meshlet bounds
exercise the stated route. This is an explicit boundary control, not a claim
about an observed room's LOD distribution.
"""
import json
from pathlib import Path
import sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"world_setup_spike"))
import selection_cases as original


def cases():
    output=[]
    for case in original.cases():
        output.append(dict(case,cost=False))
    partial=original.meshlet([original.triangle(0,50,0),original.triangle(100,50,0),
                             original.triangle(300,50,0),original.triangle(450,50,0)])
    inside=original.meshlet()
    outside=original.meshlet([original.triangle(6000,100,100)])
    near=original.meshlet([original.triangle(100,100,0),original.triangle(100,100,50)])
    for family in ("partial-groups","box-inside","box-outside","near-split","no-groups"):
        for clusters in (1,8):
            for count in (1,2,4,8,32):
                config=original.defaults()
                let={"partial-groups":partial,"box-inside":inside,"box-outside":outside,
                     "near-split":near,"no-groups":partial}[family]
                cluster=[(0.,[let]*count)]
                if family=="box-inside":cluster.append((1000000.,[outside]))
                if family=="box-outside":cluster.append((1000000.,[inside]))
                if family=="near-split":
                    config["mvq"][11]=0.;config["near"]=2.
                if family=="no-groups":config["use_groups"]=0
                pkg,groups,cones=original.package([[cluster]*clusters],config["groups"])
                output.append(dict(name=f"cost-{family}-c{clusters}-m{count}",config=config,
                    package=pkg,groups=groups,cones=cones,expected=None,cost=True,
                    family=family,clusters=clusters,meshlets_per_cluster=count,
                    selected_level_meshlets=clusters*count))
    # Plane-demand and group-count controls for group-major versus shared-plane
    # candidates. The label describes intended intersecting planes; the actual
    # compiled box-mask and selector remain authoritative for every decision.
    # Historical "mask1" means one demanded plane (actual right-plane bit2).
    # target_run records the actual mask at the unmodified compiled helper edge.
    for mask in (1,3,31):
        for n in (1,2,4,8):
            config=original.defaults();config["groups"]=n
            if mask==1:
                shapes=[[(100,50,0),(450,50,0),(100,58,0)]] if n==1 else [original.triangle(100,50,0)]*(n-1)+[original.triangle(450,50,0)]
            elif mask==3:
                config["mvq"][3]=-40
                shapes=[[(0,50,0),(800,50,0),(400,58,0)]] if n==1 else [original.triangle(0,50,0),original.triangle(800,50,0)]+[original.triangle(400,50,0)]*(n-2)
            else:
                config["mvq"][3]=config["mvq"][7]=-40;config["mvq"][11]=1
                shapes=[[(0,0,0),(800,0,300),(400,800,150)]] if n==1 else [[(0,0,0),(400,0,0),(0,400,0)],[(800,800,300),(400,800,300),(800,400,300)]]+[original.triangle(400,400,300)]*(n-2)
            let=original.meshlet(shapes)
            for count in (1,8):
                pkg,groups,cones=original.package([[[(0.,[let]*count)]]],n)
                output.append(dict(name=f"cost-mask{mask}-g{n}-m{count}",config=dict(config),
                    package=pkg,groups=groups,cones=cones,expected=None,cost=True,
                    family=f"mask{mask}",clusters=1,meshlets_per_cluster=count,
                    selected_level_meshlets=count,group_count=n))
    return output


def write_cases(directory):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    records=[]
    for case in cases():
        row=original.write_case(case,directory/(case["name"]+".bin"))
        row.update({key:case[key] for key in ("cost","family","clusters",
            "meshlets_per_cluster","selected_level_meshlets") if key in case})
        records.append(row)
    (directory/"cases.json").write_text(json.dumps(records,indent=2)+"\n")
    return records
