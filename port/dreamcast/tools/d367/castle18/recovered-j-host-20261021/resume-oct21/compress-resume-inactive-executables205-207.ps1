$ErrorActionPreference = 'Stop'
$castleEvidenceRoot = 'C:\Flycast-Evidence\re4-dreamcast\castle18-20261018\Test21\recovered-j-content-20261021'
$castleReceipt = Join-Path $castleEvidenceRoot 'inactive-executable-compression-205-207-20261021.json'
if (Test-Path -LiteralPath $castleReceipt) { throw 'Never overwrite compression receipt' }
$castleBefore = (Get-PSDrive C).Free
$castleLivePaths = @(Get-CimInstance Win32_Process -Filter "Name = 'flycast.exe'" | ForEach-Object { $_.ExecutablePath })
$castleRows = @()
foreach ($castleRunNumber in 205..207) {
    $castleCap = Join-Path $castleEvidenceRoot ('route-walk' + $castleRunNumber)
    $castleRunResult = Get-Content -Raw -LiteralPath (Join-Path $castleCap 'run-result.json') | ConvertFrom-Json
    if (-not $castleRunResult.emulator_exited) { throw 'Refuse active run' }
    $castleExecutable = [IO.Path]::GetFullPath((Join-Path $castleCap 'flycast.exe'))
    if (-not $castleExecutable.StartsWith($castleEvidenceRoot + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Target escaped owned evidence root' }
    if ($castleLivePaths -contains $castleExecutable) { throw 'Refuse active executable' }
    $castleOriginalHash = (Get-FileHash -LiteralPath $castleExecutable -Algorithm SHA256).Hash
    $castleCompactOutput = & compact.exe /C /EXE:LZX /I /Q $castleExecutable 2>&1
    if ($LASTEXITCODE -ne 0) { throw ('Compression failed: ' + $castleExecutable) }
    $castleAfterHash = (Get-FileHash -LiteralPath $castleExecutable -Algorithm SHA256).Hash
    if ($castleOriginalHash -ne $castleAfterHash) { throw 'Lossless executable hash verification failed' }
    $castleRows += [pscustomobject]@{ path = $castleExecutable; sha256_before = $castleOriginalHash; sha256_after = $castleAfterHash; output = ($castleCompactOutput -join "`n") }
}
$castleReport = [pscustomobject]@{ scope = 'Only owned inactive resumed-run executable copies. Lossless LZX filesystem compression, every byte hash unchanged. No deletion, state/image/program or gameplay mutation.'; free_before = $castleBefore; free_after = (Get-PSDrive C).Free; rows = $castleRows }
$castleReport | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $castleReceipt -Encoding utf8
Write-Output ($castleReport | Select-Object scope, free_before, free_after | ConvertTo-Json)
