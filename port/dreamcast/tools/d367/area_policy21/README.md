# Guarded AREA policy candidate

The retained r107 R4ID and R4PW bind all 71 placement ordinals to source CRC
`43dc8ff9`; the six existing AREA group masks match those exact IDs. The prior
static CRC `9081e7fd` therefore leaves AREA inactive for this retained input.
Scoped key remaps also need the original geometry-policy identity rather than
the new physical R4PW body CRC.

With existing `WORLD_RECT21=1`, AREA accepts the retained original profile and
receives `policySourceCrc`. The legacy profile stays supported. With the switch
absent or zero, both added regions reduce to the complete original source byte
for byte; extracted host preprocessing is also identical. The switch and every
recipe remain unchanged.

`area_policy_probe.py` extracts the actual AREA implementation, physical body
CRC predicate, provenance helper, and caller from source. It uses retained
R4ID/R4PW inputs and separately labeled proposed certificate rows. Its test-only
helper fixture changes the certificate-count assertion from 3 to 29; no runtime
header or active certificate table is edited. It checks all 71 IDs/placement
ordinals, authored group visibility, legacy/current/candidate profiles, wrong
rooms/counts, unknown or corrupted fingerprints, and unchanged physical bytes.

The 415 and combined 592 proposal fixtures each pass five UBSan host arms:
parent OFF/ON, candidate default/OFF/ON. Each has four 566-check controls and a
1,442-check enabled arm. This is source/host evidence, not a target object,
programme, guest, culling/look, release or physical Dreamcast acceptance.

Private receipts are under `texture-consumers21-next415-integration-20261022`
and `texture-consumers21-next592-integration-20261022` in the retained evidence
and private mirror. The latter independently validates 3,737 cumulative key-only
part remaps against original geometry/placement bytes. Integration still needs
the exact cohort tables, physical certificates and a new programme.

r200 and r11f physical publication/deep ownership fingerprints remain held.
Never replace those physical checks with a source-policy CRC. In particular,
r11f's owned part 0 also changes its exact texture key in these proposals.
