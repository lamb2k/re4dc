# El Gigante g50 landing preparation for Test 18

I-005 records the user's approval of g50 for both r119 and r11e. This side branch prepares the measured data and an explicit chapter staging entry for the coordinator to land. Test 17 stays frozen with r11e g70. No integration, tag, publication or SD copy is performed here.

| Fight | Previous MODELLED ms/frame | g50 | Saving against previous | Saving against full |
|---|---:|---:|---:|---:|
| r119 | full69.097 | 67.650 | 1.447 | 1.447 |
| r11e | shipped g7070.844 | 69.925 | 0.919 | 1.577 |

The r11e1.577ms quotation compares against full71.502, not against the shipped g70. The user's explicit approval applies to the0.919ms incremental choice too. Measurements use b18srT ELF daac42cfdc2cbadf82166f33638b86882eeefb6b4a7d30c230c678767e7c08bb: r119230:249 and r11e290:309, four actual traced frames per20-tick source window. These are hwproject MODELLED SH-4 costs, not console timing or host FPS. Detailed model, visual and memory evidence is in BOSS18_EL_GIGANTE_20261018.md.

## Chapter recipe and explicit selection

CH2REC already enables NATIVE_MODEL_REGISTRY_FIRST=1 and NATIVE_MODEL_REGISTRY_LOD=1. Both ch2/ch2-build.sh and test15/t15-build.sh are byte-unchanged. Build the coordinator's Test18 chapter arm using that recipe, then stage its qualified current chapter baseline with:

```sh
bash port/dreamcast/tools/d367/ch2/ch2-gigante-g50.sh ARM OUT.json \
  --base CHAPTER_FIXTURE.json --base-label BASE_ARM
```

The wrapper requires an explicit base and label and appends data set boss18g50 after the caller's baseline/data sets. It changes only r119/r11e registry packages and their two source atlases. The data set is never included in T15_DATA or T17_DATA. No runtime C++ knob, game logic, loader, selector, recipe flags or gate changes are required. B18G50D optionally selects the private data root; its default is /root/re4data/private/boss18-gigante-g50-t18-20261018. Missing files fail the existing staging checks.

Full remains in the original source event/grab states: unchanged coarse_actor_owner_registry.inc registry_lod_want selects the full descriptor while Status_flg[1]&0x10000000. The diagnostic r11e source grab at hold500 selects full and all three level arms have pixel-identical images. Both packages contain their own full PS2 model plus its approved gameplay descriptor; no reference/candidate model is drawn twice.

## Private data and exact staged bytes

Original qualified source set boss18-gigante-20261018 remains unchanged:607files/58,365,574 B, SHA256SUMS2bdee6acb5fc6472184261bd26e710bbffdc2618af24f9fb686f831567982f6b. The small landing set copies the exact measured registries/atlases, not regenerated models:

- /root/re4data/private/boss18-gigante-g50-t18-20261018
- C:/Game Dev/Emulators/re4-assets-private/boss18-gigante-g50-t18-20261018
- 5files/522,721 B; SHA256SUMS7f5f1856d727212524291a870ae3aed156446fedd50fb087950e4dbc2ebd44d1
- r119 registry1751fad08333086bc6ef55b60656181391b216c21ee874028381ff943dd7955a; logical arena143104 B
- r11e registryc99cd11a2938494476a78453bdaa06d03ef05cd1230145611b88c6312b3065e8; logical arena141248 B
- source atlasescd6162c8-d918ba45 and a383881d-dc463009,133264 B each

The manifest gigante-g50-data.json traces each copied file to the sealed original set and records both timing comparisons. Assets and images remain private; only source/specs/docs are committed.

## Validation and limits

Evidence root C:/Flycast-Evidence/re4-dreamcast/boss18-20261018. gigante-g50-landing/landing-proof.json proves the new explicit wrapper's r119/r11e active-room registries, textures and all11 program files equal their previously qualified g50 fixtures. The other approved room registry is additionally staged. Data-off old/new stager outputs are byte-identical. Both chapter and T15 build recipe files are byte-identical. Shell syntax, Python syntax and diff checks pass. Existing fresh b18irP knob-off boot+10overlays match frozen c18irP; no compiled source changed in this landing commit. A new release build/run is the coordinator's integration gate, not claimed here.

Existing qualification covers source STRICT plus MUST-IDENTICAL decisions651roomticks r119 and601 r11e, A/A and+3000us controls, actual hardware source20/20 per fight, native id2b drawn/GC0/no declines, TEX0, actual49152 B KOS pressure and heap4/VRAM. Protected parasite/fingertip geometry remains exact. Inspected corrected el-gigante-r119-sheet.png and el-gigante-r11e-sheet.png prove their body source hold330; r11e grab hold500. Original early pictures were withdrawn and are excluded from approval evidence.

Lowest observed r11e g50 heap4 free393856/largest393536 B. Tick600 VRAM pinned873024/dynamic724576/other90112/free879712/largest856064 B, zero refusals/no-contiguous/evictions/retries. r119 s20 death completes782/782pictures with source callback and heap retirement; one audio underrun/18556silencebytes remains documented. No all-movie, whole-route, clean-audio or console30fps claim.

The existing diagnostic chapter baseline has resident-list shortfalls outside the tested boss windows. The stager reports these unchanged; no resident gate is bypassed. The coordinator must use the current Test18 resident/texture-pack baseline and retain its release checks when landing. This branch changes no resident lists or packed textures.
