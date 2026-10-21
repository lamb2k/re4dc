# Valid module effect-release characterization

This source-only unit extends the admission fixture using real GetEmEffId,
EspEmDataSwapPush and EspDataRelease. With --actual-effects --preflight-pair,
13 OFF/28 ON cases pass each CABIN0/1 at source5e087a802. The existing admission
guard does not repair the later module-validation ordering.

The valid synthetic module is0x11, which the actual source maps to effect
owner0x10. On both module-NULL and undersized-module refusal, the actual caller
has already called actual Push/Release. With ownerCnt2 the count becomes1;
with ownerCnt1 it becomes0 and the actual final-release function dispatches
all five texture/est/sst/path/model release helpers. Those five helper bodies
are explicit exact-owner boundaries; real renderer/effect registries are not
constructed in this host fixture. Module lookup, Pop and void swap remain
boundaries. The void-swap refusal case still publishes success and retains
these release side effects.

The earlier module1 controls intentionally used a Push boundary; module1 has no
valid effect-owner mapping in actual GetEmEffId. They characterized caller order
and mutations, not actual effect release. This new unit uses a valid mapped id
to prove the count and dispatch effects through the real source functions.

Only the Push definition binding is renamed so its wrapper can count entries;
the actual owner mapping, decrement, final-release decisions and dispatch are
unchanged. Source extracted methods, all file hashes, ABI adapters and resource
limits are in read-admission-effects-host.json. Output is under20MiB, mirrored
as read-admission-effects-host-02. No production source change, private asset,
linked program, emulator run, release or physical Dreamcast gate is added.

Moving module existence/size validation ahead of Push can avoid this confirmed
side effect on those two refusals. Read-row retirement and failed forward
exchange completion remain separate ownership contracts; blind Pop on a NULL
module is unsafe because its own source dereferences the module archive.
