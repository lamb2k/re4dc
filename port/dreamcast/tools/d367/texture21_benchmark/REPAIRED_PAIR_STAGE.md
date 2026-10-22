# Matched texture pipeline stage template

**HOLD: 7ed1984d combined994 is invalidated by the canonical CRC defect. Do not stage its virtual predictions.** The 845/4ef/f42 static receipts and byte predictions remain historical evidence. Repair/rekey all selected assets, reseal provenance certificates, link the selected new programme, independently inspect its actual ELF/raw/all14/flags, and generate a new source-bound plan first. This template does not allocate a stage or guest.

`matched994_stream.py plan` now takes explicit `--source`, `--combined` manifest file, `--combined-sha256`, `--candidate-pack`, and `--candidate-worlds` JSON. The latter must map exactly the three full `/dc/native/r{100,103,101}/ps2-world.r4pw` paths to `source_path`, `bytes`, `sha256`, each matching the new manifest. It never silently inherits old C candidate worlds after a rekey. Existing whole6501 policy/composition is reused. The original18f control retains protected Ganado mipmaps; this is a full texture pipeline comparison, not globally mip-off or isolated mip causality.

The writer and readback are parameterized by the new immutable plan, rather than hardcoded programme hashes or runtime addresses. `programme994_inspect.py` is the specifically source845 static inspector; a future source's admission must independently bind its selected source/flags/ELF, not relabel that receipt. Runtime04 e08 addresses/states are forbidden. The root resource receipt must bind the exact plan SHA/arm, `stage_authorized:true`, `candidate_contract_valid:true`, and record current peer reservations/cumulative allocation. No automatic retries or cleanup. A failed partial remains charged.

After root allocates the repaired pair, the concrete Windows commands are below. Variables `$plan`, `$root`, `$m1Allocation`, `$m0Allocation` refer to the **new repaired** frozen plan and main-owned allocations; they are deliberately not populated with held994 paths. `$root` is a fresh approved pair directory containing both stage attempts and any failures. Each allocation JSON supplies `allocation_cap_bytes` and fresh `peer_reserved_bytes`. Parent must own the one writer process and its deadline; no concurrent writer or build enters these directories.

```powershell
$py = 'C:\Users\lambd\AppData\Local\Programs\Python\Python312\python.exe'
$tools = '\\wsl.localhost\Ubuntu-24.04\root\probe\codex-texture21-benchmark\port\dreamcast\tools\d367\texture21_benchmark'
$historical = 'C:\Flycast-Evidence\re4-dreamcast\texture-rect21-20261021'
$planSHA = (Get-FileHash -LiteralPath $plan -Algorithm SHA256).Hash.ToLowerInvariant()
$m1 = Get-Content -LiteralPath $m1Allocation -Raw | ConvertFrom-Json
New-Item -ItemType Directory -Path "$root\M1\gdemu" -ErrorAction Stop
& $py "$tools\matched994_stream.py" write --plan $plan --plan-sha256 $planSHA --arm M1 --allocation-receipt $m1Allocation --allocation-root $root --allocation-cap $m1.allocation_cap_bytes --peer-reserved $m1.peer_reserved_bytes --smalltracks "$historical\standalone-C-01\gdemu" --output "$root\M1\gdemu\track03.iso"
if ($LASTEXITCODE) { throw 'M1 writer stopped; preserve and charge its partial output' }
& $py "$tools\matched_pair_readback.py" --plan $plan --plan-sha256 $planSHA --arm M1 --image "$root\M1\gdemu\track03.iso" --baseline-manifest "$historical\standalone-C-01\verified-staged-image.json" --directory-records "$historical\image-plan-04\directory-records.json" --out "$root\M1\full-readback.json"
if ($LASTEXITCODE) { throw 'M1 readback stopped; no compression, second writer or guest' }
compact.exe /C /EXE:LZX /Q "$root\M1\gdemu\track03.iso"
if ($LASTEXITCODE) { throw 'NTFS compression failed; preserve file and replan resources' }
& $py "$tools\ntfs_image_readback.py" --image "$root\M1\gdemu\track03.iso" --readback "$root\M1\full-readback.json" --out "$root\M1\ntfs-identity-allocation.json"
if ($LASTEXITCODE) { throw 'Logical identity/allocation readback failed' }
# Main now checks actual free bytes, outstanding peers and cumulative failed/
# closed outputs, then grants the separate M0 allocation. Never assume a ratio.
$m0 = Get-Content -LiteralPath $m0Allocation -Raw | ConvertFrom-Json
New-Item -ItemType Directory -Path "$root\M0\gdemu" -ErrorAction Stop
& $py "$tools\matched994_stream.py" write --plan $plan --plan-sha256 $planSHA --arm M0 --allocation-receipt $m0Allocation --allocation-root $root --allocation-cap $m0.allocation_cap_bytes --peer-reserved $m0.peer_reserved_bytes --smalltracks "$historical\standalone-C-01\gdemu" --output "$root\M0\gdemu\track03.iso"
if ($LASTEXITCODE) { throw 'M0 writer stopped; preserve and charge its partial output' }
& $py "$tools\matched_pair_readback.py" --plan $plan --plan-sha256 $planSHA --arm M0 --image "$root\M0\gdemu\track03.iso" --baseline-manifest "$historical\standalone-C-01\verified-staged-image.json" --directory-records "$historical\image-plan-04\directory-records.json" --out "$root\M0\full-readback.json"
if ($LASTEXITCODE) { throw 'M0 readback stopped; no guest' }
```

Each writer streams one cooked historical C image, substitutes exact bounded ranges, checks every LE/BE metadata precondition, preserves 1743 LBAs, hashes the entire base and output, copies exact cooked GDI/small tracks, and keeps failed partials. It checks prospective bytes each write, probes disk/charged files at most 5Hz, and stops after a 120s writer deadline. Root supplies whole-process containment. Static fit or a closed writer is not readback/boot acceptance.

Independent readback parses ISO/RockRidge records itself, hashes all1743 physical members, verifies common15 and permitted assets, every extent/record/size field, PVD/noJoliet/IP/TOC/zero tail and small tracks. NTFS readback hashes the full logical image again and records actual Windows `GetCompressedFileSizeW` allocation. No gzip, raw deletion, uncompressed image duplication or guest occurs. Full byte identity across NTFS compression is a lossless artifact check, not a performance result.

Future target qualification still requires exact new ABI, canonical Package integrity, behavioral metadata equivalence, complete post-update phase coverage, same scene/camera/player/health/controls/presentation/counters, admitted relevant keys/owners and actual sampling evidence, look, full allocator/headroom accounting. Farm/woods do not accept r101nine approximation or all20 actor draw coverage. Host Flycast, modelled costs and physical Dreamcast results stay separate.
