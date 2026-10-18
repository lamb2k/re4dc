param([string[]]$Rooms)
$T = '\\wsl.localhost\Ubuntu-24.04\root\probe\lanes-20261013\ch22\port\dreamcast\tools\ps2_room_r4im.py'
$W = '\\wsl.localhost\Ubuntu-24.04\root\probe\lanes-20261013\ch22w\rooms'
$X = '\\wsl.localhost\Ubuntu-24.04\root\probe\lanes\ps2rooms\extract\inputs'
foreach ($R in $Rooms) {
  $out = "$W\$R-ps2"
  if (Test-Path $out) { Remove-Item -Recurse -Force $out }
  python $T $R "$X\$R" $out --lights 0,5 --color-light ps2 --gc-lit "$W\$R-gc-lit-cut0.json" --lod-uv-guard 0.002 --vertex-alpha tr4 --cutout-max-alpha 224 2>&1 | Out-File -Encoding utf8 "$W\$R-ps2.log"
  Write-Output "== $R rc=$LASTEXITCODE"
  Get-Content "$W\$R-ps2.log" -Tail 2
}
