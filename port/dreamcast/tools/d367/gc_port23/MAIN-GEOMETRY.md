# Main actor and cached geometry receipts

Diagnostic-only successor to the independently reviewed d629 replacement class
unit. Current profile is still out-au23on5e4drP: COARSE_ONE_SUBMIT1,
ACTOR_TRANSACTION1, COARSE_LEON1, LEON_HAND_PACK1 and RETAIN0. No coverage bits,
catalog, allowance, asset, recipe, rr or cloud animation changes.

Actual reachable boundaries:

- native_model selects the original BIN context after static decline. The
  general re4dc_actor_submit now enters its own diagnostic scope immediately
  after qualification, before conversion/deferral/Frame preparation. It cannot
  inherit an unrelated outer BIN merely because an actor attempt was called.
- The general fallback remains reachable in the actual submit_chunks branch:
  one_chunk returns-1 for explicit arrays, the caller closes its shared window,
  then calls re4dc_actor_submit. The actual branch is executed by the host test.
- Owned runs retain actual source infos through plan_chunk and owned_run_load;
  one_chunk receives the resolved exact source and scopes each accepted owner.
  Legacy nontransaction coarse paths can use descriptor infos; they remain
  outside the current class/accepted-path qualification and grant no mask bits.
- UI packet/direct acknowledgement sees the scope's selected or empty context.
  Shared direct windows also use explicit ActorSourceScope::accepted; it now
  checks its saved selection against the current context so invalidation cannot
  be bypassed by the earlier local snapshot. Actual draw/packet algorithms stay
  unchanged; rejected, culled, failed conversion and no-emission paths do not use.

The main scope chooses frozen replay first. It resolves the current source only
to validate consumed geometry against that saved identity, never to replace the
saved serial, package or consumer mask. For replacement replay the exact current
array/chunk match must still identify the saved proof and serial; otherwise it
returns empty. Original replay validates complete stream and source-array spans
against the saved current member serial. This closes old queued stream A mixed
with newly rebound source arrays B even while both owners remain alive.

Without replay, exact matching replacement/copy identity takes precedence.
An outer original context survives only with the SAME model/info and full live
BIN bounds for submitted stream and resolved original arrays. Explicit array
overrides must equal those original arrays and their expected strides; prepared
or foreign arrays without a controlled-copy receipt remain unknown. Nothing
here treats an address prefix, current model class or caller BIN as replacement
ancestry. Ambiguous original cases fail instead of falling back to a guess.

Both prepare_frame and one_frame stamp a parallel geometry receipt on a new
cache entry and compare it on a cache hit. A source/proof/consumer generation
mismatch clears diagnostic context; it does not change cache lookup, Frame
contents, allocation or render algorithms. Four fixed records hold serial,
mask and proof pointer:48 bytes on SH4, statically checked against the actual
four Frame slots. No Frame or deferred-node layout grows. Target text/stack and
actual linked budget remain unpriced for this successor. These records qualify
geometry origin only; they do NOT bless palette, motion or pose history.

test_runtime_actor_main.py executes the actual main gateway through conversion,
deferral and prepare_frame; actual fallback branch; actual cache hit/stamp
prefixes for both Frame functions; actual UI prepare/accept; real member/core/
payload helpers. Providers and the final acceptance trigger are simulated, and
the full Frame geometry algorithm is not reimplemented by the test. Controls
include ambient BIN replacement, complete versus overrun original stream,
source-array alias, explicit foreign/prepared arrays, different model-info,
no use on rejection/cull/no emission, defer-before-prepare, raw/payload replay
source change, same-address replacement reload, cached Frame mismatch and
saved-scope acceptance bypass. Five compiling mutants must fail assertions:
drop main scope, drop cached-generation check, bypass accepted-context check,
omit complete stream bounds and omit replay-array validation. Existing actual
hand reload/replay controls now reject stale generations earlier at selection.

Full host81 discovered/80 pass/one historical real-pack opt-in skip, plus C++
controls. Actual native_actor_fast gate0 token streams equal d629 in four
coarse/transaction configurations; target object/image identity remains open.
Independent review, actual current-profile path census/target pricing, complete
SourceGeometry/Weapon/Motion coverage, source catalog and final stop remain open.
