# Effect registration failure and emitter lifetime audit

This continues A10/A11 on exact d4a3b31f source after six-fix runtime qualification. It reuses the existing 19-site image/audio map; no new room inventory, game build, guest, runtime repair or screenshot was produced.

## Confirmed E03 registration failure

Unmodified EspDataLoad increments the u8 owner count before checking version 0xB. A bad initial version returns failure with count one. Replacing the fixture with a correct file and retrying flag zero returns success with count two, before registering textures, sequences, paths or models. A counted or forced release before the corrected retry restores admission. A strict flag-one retry returns failure and also increments the count. NULL data returns before incrementing.

The actual extracted EspDataLoad and EspDataRelease bodies pass eight characterization cases under ASan/UBSan (356 assertions, including saturation checks). This PASS confirms the bad state; it is not repair acceptance. Registration/release callees are instrumented stubs. Empty but structurally valid tables isolate the admission/count logic. A low static host address preserves the source u32 pointer argument without widening its ABI. The source u8 counter and file structures are unchanged.

Run: python3 port/dreamcast/tools/d367/cache21/test_effect_registration_failure.py --source /path/to/repo --out /private/output

Selected malformed gameplay input, caller retry occurrence and physical-console impact remain OPEN. This is not established as the shooting slowdown. A repair must validate before publishing the first reference, preserve valid repeated loads and strict-duplicate behavior, and cover partial downstream registration separately. No runtime policy is changed here.

## T03 payload retry remains distinct from index retry

native_ui.cpp load returns resident hits first. A texpack index error is handled by texpack_index.inc retry cadence. After a successful index lookup, however, package open/validation or upload errors close the package and return without a resident entry. Only loose-file open failure enters the missing-key ring. General packed payload errors do not acquire the index's cooldown. PVR fragmentation has its own guarded latch. A subsequent draw can therefore attempt a packed bad payload again even while the index is healthy. This is a source policy gap, not a measured count of gameplay reads; injected actual package/load integration and selected failing key attribution remain OPEN. Do not blanket-cache transient I/O or allocation failures as permanently missing content.

## E01/E02 lifetime ordering narrowed, not globally cleared

- ReadWepData calls cPlayer::weaponRelease before ReleaseWepData. weaponRelease removes matching player effects/controllers/models; ReleaseWepData then runs InitModule/unbind/archive free. Weapon effect-table release occurs before the controller deletion inside weaponRelease, so table release alone is not a controller sweep.
- PushEspgen sets its delete bit and invokes its destructor synchronously. EspgenMove clears delete-marked slots before invoking their move callback in both baseline and scan paths. Deferred slot reuse therefore does not itself prove one more head-pointer evaluation.
- Event ExeEndEvt releases its registered effect owner, then EventAllEffDelete targets exact event flag groups 0x3001 and 0x2001. This is a filtered delete, not a global owner/range sweep.
- InitModule calls native effect unbind before freeing the archive. Native unbind removes registry metadata but does not scan the original live controller pool. Matching live source pointers must already have been retired by the caller.
- EstSet stores the borrowed head pointer in controller work, and espgen10_Update reads it later. Module replacement, non-player/foreign attached emitters, failed initialization, callback/destructor scheduling and reset ordering still need a complete caller-lifetime proof. These remain OPEN under A08/A11; the animation reset reproduction is tracked separately by Boss.

No claim is made that every emitter outlives its source, or that these narrower source orderings prove all owners safe. No geometry, enemy behavior, animation rate, gameplay state, assets or shipped program changed.