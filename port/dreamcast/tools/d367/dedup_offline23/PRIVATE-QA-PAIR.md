# Private QA23 pair plan

`plan_private_qa_pair.py` reads the existing qualification plan and emits a
source-pinned, serial OFF/ON command plan. It has no execution or guest path.
The current fullH2 memory result still blocks every QA mutation. The smaller
code/end address alone did not establish heap recovery.

Future destinations (must be absent before root creates either):

* `C:\Game Dev\Emulators\RE4DC-QA23-Dedup-Off-5be38f00`
* `C:\Game Dev\Emulators\RE4DC-QA23-Dedup-On-5be38f00`

The future build tree must be a separate clean exact5be tree allocated by root;
the helper neither allocates it nor uses the live next/OFF control tree. Both
arms use the existing DATA29, same frozen four alternate files under their
alternate filenames, and unchanged original standard files. Existing rr-qa
primitives are reused individually because rr-qa hardcodes one same-source label.

One correction to the original plan is necessary: rW inherits PC_SAMPLER1 from
test15's WP. The new plan appends PC_SAMPLER0 and requires resolved0. It also
requires KOS_WATCH0, KOS_SQUEEZE0 and native registry census0. Standard inherited
TEX_CHECK/MCHECK/VRAM checks are retained; no census or squeeze twin is substituted.
No production recipe or shared tool is edited.

Root's later execution must hold one whole-pair tree lease, take one shared
SDKslot per serial build with JOBS1, and recheck C free>=20GiB before expensive
steps. Labels, work and private destinations must be fresh. Existing ch2-build,
t11 --set, t8-pkgtree, stage_route/mkqa, standard mkgdi and both disc-lint profiles
are listed explicitly. No large output is allocated by planning. Resolved source,
programme/overlay, recipe/data/fixture and README pins plus individual gate
results are required before the private pair is considered complete. A matched
QA-menu heap does not establish the ordinary fullH2 memory floor.
