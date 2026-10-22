# Effect controller validation ordering

The Dreamcast adapter decodes the cached effect record before the original controller checks a dead/reused parent or invalid part. `re4dc_effect_record_ref` reads the borrowed header count before resolving a native binding. Original early refusal can therefore touch retired backing first.

`EFFECT_CONTROLLER_VALIDATE_FIRST=1` delays the decoder until the existing validation and matrix preparation finish. The switch defaults to zero and only targets espgen10.o. PPC and default-off object behavior are preserved.

Qualification: the actual full espgen10_Update body passes 21 host cases in each baseline/unset/zero/enabled arm under UBSan with explicit model, decoder, matrix and emitter boundaries. Twelve rejected-controller cases reproduce the old eager-read boundary and avoid it with the guard. Seven valid cases preserve emissions and controller state. Two remaining lifetime cases explicitly still reach the decoder. The whole SH4 baseline/unset/zero stripped objects match; enabled text grows 52 bytes, data/BSS stay zero and static Update frame decreases 400 to384 bytes. Make default/0/1 and seven invalid controls pass.

This does not establish whole effect lifetime safety: valid parents can read head flags, global controllers still need live backing, and controller quiescence, registry borrowers, source epilog and reset admission remain open. Extended full OFF2598b8a56 matched original QA program8942ad7e and all14 overlays before this repair; it is not a full-program qualification of the new patch. No Flycast, release or physical Dreamcast acceptance is claimed.

Evidence: C:/Flycast-Evidence/re4-dreamcast/cache21-integration-prep-20261021/effect-controller-validation-v2/review.json. Reproduction helpers are tools/cache21/qualify-effect-controller-{validation,sh4}.py; they record exact compiler commands and source hashes and expect the preserved isolated workspace/build recipe.
