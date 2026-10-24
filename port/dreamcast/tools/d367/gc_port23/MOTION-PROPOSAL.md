# Separate visual motion provenance

Source-only proposal after root's explicit ruling: motion/animation/FCV/EVD
payloads that drive visible poses are visual assets. Preserve GC/unknown until
exact PS2 ancestry is proved. Collision/sequencing logic has only the exemption
stated in CLAUDE178-184. No motion/event asset conversion, source swap or cloud
animation implementation is authorized by this document. Current GC-ASSET is
incomplete and cannot claim absence of GC assets with these inputs unattributed.

The initial trace is deliberately within existing read/model bridge declarations:

- read.cpp binds a prepared enemy motion archive with exact pArc/len around731;
  InitModule unbinds the same archive around422 before freeing it. Existing
  player/core/weapon/room immutable-load hooks know their authoritative extents,
  but those BIN geometry bindings do not yet prove every motion source.
- native_motion.h keeps source FCV identities archive-owned; acquire/release
  leases evaluated key tables temporarily and restore the resident proxy table.
  A cache table address is therefore not an original source identity.
- model_bridge.cpp already uses real cModel declarations; its static hint checks
  pMotion but has no evaluated-pose provenance accessor. Any diagnostic accessor
  must live here rather than duplicating cModel/MotionWork layout in platform.
- model.h MotionWork has primary pMot, pHermite_data, previous-pose interpolation,
  blend work, remap and blend tables. MotionData key offsets relocate in place.
  Current pMot alone cannot establish all inputs of the visible pose. A stopped
  motion can leave its last pose visible; null pMot does not erase that origin.

Minimum contract, before implementation claims:

1. Capture full exact immutable motion/FCV/EVD member bytes at an authoritative
   bounded loader before relocation/detachment. Bind archive owner+generation,
   exact member offset/extent and full SHA. Cache/proxy/moved keys inherit that
   same checked identity only through authenticated lease/copy lifetimes. GC
   containers can hold PS2 bytes; neither key, filename nor API establishes origin.
2. Record the inputs of the pose actually committed to model parts/palette:
   primary motion, every active blend/interpolation/history source and event
   pose override. Controlled evaluation preserves their origin. Free/reload,
   info rebinding, stale async completion, failed evaluation or unknown writer
   invalidates the pose receipt before any new output can inherit it. This
   precise evaluation boundary needs coordination/new claims with cloud animation;
   no edit to motion.cpp/native_motion or cloud animation8 is made here.
3. A real model_bridge accessor exposes a bounded copied receipt for that exact
   current model/info pose generation. Freeze it with the accepted source scope,
   deferred node, owned Frame/palette/cache reuse and replay. A later source or
   pose rebind must never relabel already queued geometry. Motion load/evaluation
   without accepted visible slots does not count as drawn use.
4. At the actual accepted geometry acknowledgement, latch Motion independently
   of geometry. Direct, packet, shared-window, coarse/compiled replacement and
   deferred paths all need it. A PS2 replacement mesh token cannot satisfy Motion.
   Procedural/bind-pose output needs explicit producer coverage, not an inference
   from a null pointer. Unknown/mixed/ambiguous inputs fail or emit exact unknown
   identities for reviewed exceptions; no auto-learning.

The smallest reporting change would append Motion after Movie, retaining all
existing consumer bit positions. Required would become3ff; the current wired
mask stays1f6 until Motion, SourceGeometry and Weapon actually close. Update the
strict judge/schema/checkpoints/only-shrinking allowances and regenerate maximum
production log-length controls before accepting the new row. Ten consumers add
one counter, not a resident identity table; measured formatting and queue/index
capacity checks must cover it. This is a proposal, not a schema/coverage change.

Use existing stable owner/Frame records or bounded borrowed metadata once their
real lifetimes are proved. Do not add a generic pose cache or unpriced arrays.
Price every receipt copied into deferred nodes, retained frames and blend chains
against actual SH4 linked heap/KOS budgets before growth. Hash/catalog/file work
belongs only at safe load/flush boundaries, never pose evaluation, SQ, audio,
G2 or scheduler locks. Default0 must retain OFF object/image identity.

Meaningful controls must include: hidden/evaluated-but-not-drawn pose (no use),
accepted primary+blend (both original identities), stopped motion with retained
pose, source proxy/cache reuse, failed/partial read, retired key source, stale
async completion, model-info/palette rebind, old deferred pose after a new pose,
event override with a PS2 mesh, unknown blend depth/owner, and an explicitly
fresh no-motion producer. Independent negative mutants must remove one lifetime
hop and be rejected. Final stop must quiesce pending motion evaluations/copies
along with all existing audio/draw producers before its terminal checkpoint.
