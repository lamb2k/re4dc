# Validate module before releasing effects

`EVD_MODULE_VALIDATE_FIRST=1` defaults0 and affects Dreamcast EvtReadSub only.
It moves EspEmDataSwapPush after the existing SearchEmModule NULL and event-size
checks. Push releases effect registrations; a known missing/undersized module
must refuse before these side effects. Successful calls still validate, Push,
then MemorySwap and publish the existing success metadata/output.

The two failure branches retain their existing read-row retirement behavior.
This guard does not restore prior metadata or effects, invent a forward receipt,
call blind Pop, or certify MemorySwap completion. These gaps remain explicit.
No datactrl/read/native file is changed by this unit; main approved event/Make.

## Qualification

test_read_admission_characterization.py --actual-effects --module-validate-pair
passes13 cases each OFF/ON, CABIN0/1 under UBSan. Adding --with-preflight passes
28 each OFF/ON, CABIN0/1 with the preceding read admission guard enabled.
Actual EvtReadSub/table, dataCtrl acquisition/unit lifecycle, GetEmEffId,
EspEmDataSwapPush and EspDataRelease bodies execute.

For valid module0x11/effect owner0x10 and ownerCnt1/2, OFF reproduces decrement
and possible five-helper dispatch before NULL/undersized module refusal. ON
retains byte-exact projected effect owner counters with no Push or release
dispatch. Read/unit/data and the existing failure result/row retirement match
their specified controls. Valid equal-size exchange still executes Push once,
all expected release dispatches, the controlled byte swap in both directions,
and swapped/output publication. A controlled void-swap refusal still publishes
success and releases effects: this is an explicit unmodified negative control.

Module lookup, Pop, transport/allocator/native policy and the five effect
subtable helpers remain exact controlled boundaries. Actual owner mapping,
count decrement and final-dispatch decisions are not mocked. Private game data,
real renderer registries, target module allocation and real DVD/ARAM exchange
are not accepted by these synthetic source tests. Earlier outer caller tests
still pass146 OFF per cabin/153 ON cabin0/154 ON cabin1 with this new switch off.

Four whole stripped SH4 event.o OFF identities match6540f37ef across CABIN0/1
and EVD_ADMISSION_TXN0/1. Default/explicit0 commands match; invalid values reject.
ON text is4 bytes smaller in all four objects, data4/BSS640 and EvtReadSub48B
static frame unchanged. This static code-size result is not a performance or
traffic measurement. Selected PPC EvtReadSub preprocessing remains identical.

Source event.cpp SHA256:
`d59d82e351ba81c2eef0a0042324b572ef38c151907097f1b6ad96b685240e60`.
Exact module-validate-first-{host,combined-host,sh4,exec-regression}.json and raw
mirrors module-validate-host-03/combined-host-01/sh4-01/exec-regression-01 retain
commands, source identities and limits. No full program/stage, asset, guest,
release, physical-console, whole-stack or whole-epoch acceptance is claimed.
