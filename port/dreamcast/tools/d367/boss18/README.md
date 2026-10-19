# Boss draw attribution by model identity

These host tools observe a private copy of the logic18 exporter. They do not
change game code, the timing model, caller ownership or charge rules. A native
`commonModelTrans` invocation is associated with its actual source model pointer
through the byte load in `re4dc_actor_model_id`, never by dividing a shared render
cost by actor count.

Prerequisites: exact profiled ELF and final pre-strip overlay symbols, verified
relocated runtime image, original loader log, ordered complete traces, and an
unchanged-timing logic18 profile. Use the byte-matched logic18 exporter documentation to build
and verify that profile. Its output directory needs `runtime.elf`, `runtime.json`,
`runtime-symbols.{json,tsv}` and `simulator/`.

```sh
python3 prepare_model_id_witness.py --profile "$PROFILE" --boot "$BOOT" \
  --out "$WITNESS" --descriptors source-descriptor-a,source-descriptor-b \
  --window 340:359
gcc -O2 -o "$WITNESS/hwsim" "$WITNESS/hwsim_profile_witness.c" -lm
L18_SYMBOLS="$PROFILE/runtime-symbols.tsv" \
B18_MODEL_WITNESS="$WITNESS/model-witnesses.tsv" \
  "$WITNESS/hwsim" --elf "$PROFILE/runtime.elf" --out "$WITNESS/nominal" \
  "$TRACE_340" "$TRACE_345" "$TRACE_350" "$TRACE_355"
python3 "$LOGIC18_TOOLS/verify_profile.py" --original "$PROFILE/original/nominal" \
  --profile "$WITNESS/nominal" --out "$WITNESS/validation.json"
python3 summarize_model_draw.py --profile "$PROFILE" --witness-dir "$WITNESS" \
  --ticks 340,345,350,355 --out "$WITNESS/boss-exclusive-draw.json"
```

The generator refuses changed runtime/log hashes, any unsupported accessor
instruction sequence, absent source descriptor admissions, or ownership changes
inside the selected interval. The exact 36-byte accessor contract is deliberately
narrow: a different compiled function requires source/disassembly audit first.
The summary additionally requires byte-identical caller contexts and function
frames. It excludes interrupt self charges and verifies that those plus draw self
charges conserve each invocation's inclusive charge.

Coverage is part of the result. Every incomplete/invalid invocation and every
witness without resolved ancestry remains explicit. Only a common cohort with
complete, valid ownership for every requested model is priced. Costs are per
captured sample; establish the exact build's logic ticks per picture separately
before reporting costs per tick. At steady 30 fps every tick is drawn. Separate
chains, parasites, tentacles, AI and preparation outside the witnessed root are
not included.

Validation on the retained r224 diagnostic: original timing and context outputs
are byte-identical across four ordered traces. Thirty-two field witnesses yield
8 observed roots, 6 complete/non-invalid roots; only two jointly complete samples
are priced. Seven actual-input controls cover changed boot identity, unsupported
getter code, wrong descriptor, interval ownership change, pre-existing output,
incomplete/unresolved coverage exclusion, and wrong field address. No guard,
capacity or material contract was relaxed.
The ownership parser also consumes the source logger's room-less retirement
records (NMRM retire t=... m=...). An actor retired before the interval cannot
remain selected; a selected actor retiring or changing inside the interval is
refused. The retained r11e replacement at tick231 is the regression fixture.
Six lifetime controls pass. Actual r119 full/g70/g50 and current twins
full/type1 controls produce byte-identical witness C/header/proof files.
Malformed retirement records are refused rather than silently ignored.
This is host-only proof handling; runtime ownership and timing are unchanged.
