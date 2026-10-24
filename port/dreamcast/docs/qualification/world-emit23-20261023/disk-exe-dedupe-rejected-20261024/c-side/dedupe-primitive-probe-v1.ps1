$ErrorActionPreference='Stop'
$dir='C:\Game Dev\Emulators\codex-lanes\world-emit23\dedupe-primitive-probe-v1'
if(Test-Path -LiteralPath $dir){throw 'Preserve prior controls'}
New-Item -ItemType Directory -Path $dir|Out-Null
$canonical=Join-Path $dir 'canonical.txt';$original=Join-Path $dir 'original.txt';$temp=Join-Path $dir 'temp-link.txt';$backup=Join-Path $dir 'backup.txt'
[IO.File]::WriteAllText($canonical,'tiny immutable payload');[IO.File]::WriteAllText($original,'tiny immutable payload')
New-Item -ItemType HardLink -Path $temp -Target $canonical|Out-Null
(Get-Item -LiteralPath $canonical).IsReadOnly=$true
$handle=[IO.File]::Open($original,[IO.FileMode]::Open,[IO.FileAccess]::Read,([IO.FileShare]::Read -bor [IO.FileShare]::Delete))
try{[IO.File]::Replace($temp,$original,$backup,$false);$result='PASS'}catch{$result=$_.Exception.ToString()}finally{$handle.Dispose()}
[pscustomobject]@{Result=$result;CanonicalReadonly=(Get-Item -LiteralPath $canonical).IsReadOnly;OriginalReadonly=(Get-Item -LiteralPath $original).IsReadOnly;BackupExists=(Test-Path -LiteralPath $backup);SourceStill=(Get-Content -LiteralPath $original -Raw);Links=(& fsutil.exe hardlink list $canonical)}|ConvertTo-Json -Depth 5
