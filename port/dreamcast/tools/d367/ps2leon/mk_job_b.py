#!/usr/bin/env python3
"""job.json for bl_arm_b.py: arm B's per-role region targets (the PS2 Leon's 5,167 triangles: legs 924 -> 300, the 624
freed given to head/hair +423, back/shoulders +140, arms where they show +61), bone regions, atlas tiles."""
import hashlib, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import leon_sources as ls  # noqa
TARGETS = {
    0: {'torso': 135, 'legs': 300, 'head': 60, 'arms': 730},   # body: PS2 126 / 924 / 58 / 690
    1: {'torso': 1000, 'arms': 40},                              # jacket (back and shoulders): PS2 869 / 36
    2: {'arms': 102},                                            # role 2: PS2 102 (105 stored)
    3: {'head': 562},                                            # face: PS2 562
    4: {'head': 470},                                            # head: PS2 466
    5: {'arms': 330}, 6: {'arms': 330},                          # hands: PS2 322 / 318
    7: {'head': 1108},                                           # hair: PS2 682 (691 stored), today 1,439
}
parents, _ = ls.gc_skeleton()
job = dict(targets={str(k): v for k, v in TARGETS.items()}, regions=ls.bone_regions(parents),
           tiles=json.loads((ls.PROTO / 'deliverables/leon-4k/asset-report.json').read_text())['source_uv_tiles'],
           hair_materials={'ac381b1a-3ade84b1': 1, '7a9de1fd-0e415f15': 2},
           source=str(ls.LEON_SOURCE), source_sha256=hashlib.sha256(ls.LEON_SOURCE.read_bytes()).hexdigest())
total = sum(sum(v.values()) for v in TARGETS.values())
print('targets total', total, {r: sum(v.get(r, 0) for v in TARGETS.values()) for r in ls.REGIONS})
Path(sys.argv[1]).write_text(json.dumps(job, indent=1))
