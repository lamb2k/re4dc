$ErrorActionPreference = 'Stop'
$castleEvidenceRoot = 'C:\Flycast-Evidence\re4-dreamcast\castle18-20261018\Test21'
$castleReceipt = Join-Path $castleEvidenceRoot 'inactive-executable-compression-historical-current-j-101-200-except127-20261021.json'
if (Test-Path -LiteralPath $castleReceipt) { throw 'Never overwrite compression receipt' }
$castleBefore = (Get-PSDrive C).Free
$castleLivePaths = @(Get-CimInstance Win32_Process -Filter "Name = 'flycast.exe'" | ForEach-Object { $_.ExecutablePath })
$castleRows = @()
foreach ($castleRunNumber in (101,102,103,104,105,106,107,108,109,110,111,112,113,114,115,116,117,118,119,120,121,122,123,124,125,126,128,129,130,132,133,134,135,136,137,138,139,140,141,142,143,144,145,146,147,148,149,150,151,152,153,154,155,156,157,158,159,160,161,162,163,164,166,167,168,169,170,171,172,173,174,175,176,177,178,179,180,181,182,183,184,185,186,187,188,189,190,191,192,193,194,195,196,197,199,200)) {
    $castleCap = Join-Path $castleEvidenceRoot ('current-j-route-walk' + $castleRunNumber)
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
$castleReport = [pscustomobject]@{ scope = 'Only Castle-owned inactive historical-current-J executable copies excluding127. Lossless LZX filesystem compression, every byte hash unchanged. No deletion, state/image/program or gameplay mutation.'; free_before = $castleBefore; free_after = (Get-PSDrive C).Free; rows = $castleRows }
$castleReport | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $castleReceipt -Encoding utf8
Write-Output ($castleReport | Select-Object scope, free_before, free_after | ConvertTo-Json)
