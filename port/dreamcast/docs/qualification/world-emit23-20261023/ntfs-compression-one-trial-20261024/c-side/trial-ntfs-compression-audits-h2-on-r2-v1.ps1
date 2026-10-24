param([switch]$ExecuteApprovedOne)
$ErrorActionPreference='Stop'
$PSNativeCommandUseErrorActionPreference=$false
$target='C:\Flycast-Evidence\re4-dreamcast\audits23-takeover\5e4de9a0\h2-on-r2\flycast.exe'
$allowedRoot='C:\Flycast-Evidence\re4-dreamcast\audits23-takeover'
$lane='C:\Game Dev\Emulators\codex-lanes\world-emit23'
$reportDir=Join-Path $lane 'ntfs-compression-one-trial-v1'
$inventory=Join-Path $lane 'DISK-EXE-DEDUPE-INVENTORY-20261024-v1.json'
$controls=Join-Path $lane 'NTFS-COMPRESSION-CONTROLS-20261024-v2.json'
$sourcePin=Join-Path $lane 'NTFS-COMPRESSION-ONE-TRIAL-SOURCE-PIN-v1.json'
$expectedHash='8e6c49871013c25b1a1c77c789167e3aaed8193e828adb7e2bbce9248d2add4a'
$expectedId='E8D47561:00050000004F12B7'
if(-not$ExecuteApprovedOne){throw 'Explicit -ExecuteApprovedOne required; ONE exact root-admitted old capture only.'}
function Hash([string]$p){(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}
if((Hash $inventory)-ne'ef062a4655f3f84ca56248373cee77b749e12828cc6e614ec33e71777a336955'){throw 'Inventory changed'}
if((Hash $controls)-ne'7d40c885604c179797220a3f4e29d34e94f91d84cfe448bde2b8fef4f981083e'){throw 'Controls changed'}
$pin=Get-Content -LiteralPath $sourcePin -Raw|ConvertFrom-Json
if($pin.ScriptSHA256-ne(Hash $PSCommandPath)-or$pin.ScopeTarget-ne$target-or-not$pin.OriginExactVerified){throw 'Sealed source checkpoint missing/mismatched'}
$control=Get-Content -LiteralPath $controls -Raw|ConvertFrom-Json
if($control.Status-ne'PASS_TINY_CONTROLS_ONLY'){throw 'Tiny controls not passed'}
$compact=$control.Utility.Path
if((Hash $compact)-ne$control.Utility.SHA256){throw 'Native utility changed'}
$rows=@((Get-Content -LiteralPath $inventory -Raw|ConvertFrom-Json).Files|Where-Object {$_.Path-eq$target})
if($rows.Count-ne 1-or-not$rows[0].Eligible-or$rows[0].FileId-ne$expectedId-or$rows[0].Sha256-ne$expectedHash-or$rows[0].HardlinkCount-ne 1){throw 'Fixed eligible admission mismatch'}
$row=$rows[0]
$clusterBytes=[long](Get-Volume -DriveLetter C).AllocationUnitSize
if($clusterBytes-le 0-or(Get-Volume -DriveLetter C).FileSystem-ne'NTFS'){throw 'NTFS allocation unit unavailable'}
Add-Type -TypeDefinition @"
using System;using System.ComponentModel;using System.Runtime.InteropServices;using Microsoft.Win32.SafeHandles;
public static class OneApprovedNtfsTrialV1 {
 [StructLayout(LayoutKind.Sequential)]struct Info{public uint Attr;public System.Runtime.InteropServices.ComTypes.FILETIME C,A,W;public uint Volume,Hi,Lo,Links,IndexHi,IndexLo;}
 [StructLayout(LayoutKind.Sequential)]struct Standard{public long Allocation,Length;public uint Links;public byte Deleted,Directory;}
 [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)]static extern SafeFileHandle CreateFile(string p,uint a,uint s,IntPtr sec,uint c,uint f,IntPtr t);
 [DllImport("kernel32.dll",SetLastError=true)]static extern bool GetFileInformationByHandle(SafeFileHandle h,out Info f);
 [DllImport("kernel32.dll",SetLastError=true)]static extern bool GetFileInformationByHandleEx(SafeFileHandle h,int c,out Standard f,uint n);
 [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)]static extern uint GetCompressedFileSize(string p,out uint hi);
 public sealed class Result{public string FileId;public uint Links;public long LogicalBytes,StandardAllocationBytes,PhysicalStorageBytes;}
 public static Result Read(string p){using(var h=CreateFile(p,0x80,7,IntPtr.Zero,3,0x80,IntPtr.Zero)){if(h.IsInvalid)throw new Win32Exception(Marshal.GetLastWin32Error());Info f;Standard s;if(!GetFileInformationByHandle(h,out f)||!GetFileInformationByHandleEx(h,1,out s,(uint)Marshal.SizeOf(typeof(Standard))))throw new Win32Exception(Marshal.GetLastWin32Error());uint hi;uint lo=GetCompressedFileSize(p,out hi);if(lo==0xffffffff)throw new Win32Exception(Marshal.GetLastWin32Error());return new Result{FileId=f.Volume.ToString("X8")+":"+f.IndexHi.ToString("X8")+f.IndexLo.ToString("X8"),Links=f.Links,LogicalBytes=s.Length,StandardAllocationBytes=s.Allocation,PhysicalStorageBytes=((long)hi<<32)|lo};}}
}
"@
function State(){
 $n=[OneApprovedNtfsTrialV1]::Read($target);$f=Get-Item -LiteralPath $target
 [pscustomobject]@{Path=$target;FileId=$n.FileId;Links=$n.Links;LogicalBytes=$n.LogicalBytes;StandardAllocationBytes=$n.StandardAllocationBytes;PhysicalStorageBytes=$n.PhysicalStorageBytes;AllocatedStorageBytes=[long]([Math]::Ceiling([double]$n.PhysicalStorageBytes/[double]$clusterBytes)*$clusterBytes);ClusterBytes=$clusterBytes;SHA256=(Hash $target);Readonly=$f.IsReadOnly;Compressed=(($f.Attributes-band[IO.FileAttributes]::Compressed)-ne 0);Attributes=[string]$f.Attributes;LastWriteUtc=$f.LastWriteTimeUtc.ToString('o')}
}
function Ancestry(){
 $full=[IO.Path]::GetFullPath($target)
 if($full-ne$target-or-not$full.StartsWith($allowedRoot+'\',[StringComparison]::OrdinalIgnoreCase)-or[IO.Path]::GetFileName($full)-ne'flycast.exe'){throw 'Absolute exact scope mismatch'}
 $f=Get-Item -LiteralPath $full;if(($f.Attributes-band[IO.FileAttributes]::ReparsePoint)-ne 0){throw 'File reparse refused'}
 $d=$f.Directory;while($d){if(($d.Attributes-band[IO.FileAttributes]::ReparsePoint)-ne 0){throw 'Ancestor reparse refused'};$d=$d.Parent}
}
$cap=Split-Path -Parent $target
$runPath=Join-Path $cap 'run-result.json';$boundPath=Join-Path $cap 'bounded-launch.json'
function Admission(){
 Ancestry
 if((Hash $runPath)-ne$row.RunReceiptSha256-or(Hash $boundPath)-ne$row.BoundReceiptSha256){throw 'Completion proof changed'}
 $run=Get-Content -LiteralPath $runPath -Raw|ConvertFrom-Json;$bound=Get-Content -LiteralPath $boundPath -Raw|ConvertFrom-Json
 if($run.status-ne'RUN_COMPLETE'-or$run.errors.Count-gt 0-or$bound.guest_exited-ne$true-or$bound.deadline_fired-ne$false-or-not$bound.pid){throw 'Not closed complete capture'}
 if([DateTimeOffset]::Parse($run.end_utc).UtcDateTime-gt[DateTime]::UtcNow.AddMinutes(-5)){throw 'New/current completion refused'}
 $processes=@(Get-CimInstance Win32_Process);$ids=@{};foreach($p in $processes){$ids[[int]$p.ProcessId]=$true}
 $pidText=(Get-Content -LiteralPath (Join-Path $cap 'flycast.pid') -Raw).Trim()
 if($pidText-notmatch'^\d+$'-or$ids.ContainsKey([int]$pidText)-or$ids.ContainsKey([int]$bound.pid)){throw 'Recorded/bound PID currently present, including reuse'}
 foreach($p in $processes){if($p.ExecutablePath-and$p.ExecutablePath.Equals($target,[StringComparison]::OrdinalIgnoreCase)){throw 'Active executable path'}}
 $s=State
 if($s.FileId-ne$expectedId-or$s.Links-ne 1-or$s.LogicalBytes-ne 14416384-or$s.SHA256-ne$expectedHash-or$s.Readonly){throw 'File identity/hash/size/link/readonly admission mismatch'}
 $h=[IO.File]::Open($target,[IO.FileMode]::Open,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None);$h.Dispose()
 return $s
}
function SidecarInventory(){
 $result=@{};foreach($f in @(Get-ChildItem -LiteralPath $cap -Recurse -File)){
  if($f.FullName.Equals($target,[StringComparison]::OrdinalIgnoreCase)){continue}
  if(($f.Attributes-band[IO.FileAttributes]::ReparsePoint)-ne 0){throw 'Sidecar reparse refused'}
  $result[$f.FullName]=[pscustomobject]@{Size=$f.Length;SHA256=(Hash $f.FullName)}
 };return $result
}
function SidecarsSame($baseline){$now=SidecarInventory;if($now.Count-ne$baseline.Count){throw 'Capture sidecar set changed'};foreach($k in $baseline.Keys){if(-not$now.ContainsKey($k)-or$now[$k].Size-ne$baseline[$k].Size-or$now[$k].SHA256-ne$baseline[$k].SHA256){throw 'Capture sidecar changed'}}}
function FullBytesSame(){if(-not[Linq.Enumerable]::SequenceEqual([byte[]][IO.File]::ReadAllBytes($target),[byte[]]$script:originalBytes)){throw 'Original full byte sequence changed'}}
function Journal([string]$phase,$data){[pscustomobject]@{Utc=[DateTime]::UtcNow.ToString('o');Phase=$phase;Data=$data}|ConvertTo-Json -Depth 10 -Compress|Add-Content -LiteralPath (Join-Path $reportDir 'journal.jsonl') -Encoding UTF8}
function Invoke-Compact([string]$verb,[string]$tag){
 $args=@($verb,'/F','/Q',$target);$clock=[Diagnostics.Stopwatch]::StartNew();$text=(& $compact @args 2>&1|Out-String);$rc=$LASTEXITCODE;$clock.Stop();$output=Join-Path $reportDir ('compact-'+$tag+'-output.txt');$text|Set-Content -LiteralPath $output -Encoding UTF8
 $r=[pscustomobject]@{Utility=$compact;Arguments=$args;ExitCode=$rc;HostUtilityWallMilliseconds=$clock.Elapsed.TotalMilliseconds;RawOutput=$output;RawOutputSHA256=(Hash $output)};Journal ('native-'+$tag) $r
 if($rc-ne 0){throw ('Native utility error: '+$tag)};return $r
}
if(Test-Path -LiteralPath $reportDir){throw 'Preserve prior trial; no repeat path reuse'}
$before=Admission
if($before.Compressed-or$before.StandardAllocationBytes-ne 14417920-or$before.AllocatedStorageBytes-ne 14417920){throw 'Expected original uncompressed allocation changed'}
$script:originalBytes=[IO.File]::ReadAllBytes($target);$sidecars=SidecarInventory;FullBytesSame
New-Item -ItemType Directory -Path $reportDir|Out-Null
$freeBefore=[long](Get-Volume -DriveLetter C).SizeRemaining
Journal 'admitted-before' @{State=$before;Sidecars=$sidecars;SourcePin=$pin;CFreeBytes=$freeBefore}
$compressed=$null;$restored=$null;$c=$null;$u=$null
try{
 $null=Admission;$c=Invoke-Compact '/C' 'C';$compressed=Admission;FullBytesSame;SidecarsSame $sidecars
 if(-not$compressed.Compressed-or$compressed.AllocatedStorageBytes-ge$before.AllocatedStorageBytes){throw 'Exit0 without verified compressed state/storage reduction'}
 Journal 'compressed-verified' @{State=$compressed;CFreeBytes=[long](Get-Volume -DriveLetter C).SizeRemaining}
 $null=Admission;$u=Invoke-Compact '/U' 'U';$restored=Admission;FullBytesSame;SidecarsSame $sidecars
 if($restored.Compressed-or$restored.StandardAllocationBytes-ne$before.StandardAllocationBytes-or$restored.AllocatedStorageBytes-ne$before.AllocatedStorageBytes){throw 'Uncompressed original allocation not restored'}
 $result=[ordered]@{Schema='ONE_APPROVED_CLOSED_CAPTURE_NTFS_TRIAL_V1';Status='PASS_ROUNDTRIP_ORIGINAL_UNCOMPRESSED';SourcePin=$pin;Target=$target;Before=$before;Compressed=$compressed;Restored=$restored;Commands=@($c,$u);FullOriginalByteSequenceComparedAfterBoth=$true;SidecarFilesVerifiedUnchanged=$sidecars.Count;RunAndBoundReceiptsUnchanged=$true;CFreeBytesBefore=$freeBefore;CFreeBytesAfter=[long](Get-Volume -DriveLetter C).SizeRemaining;PhysicalReductionDuringTrial=($before.AllocatedStorageBytes-$compressed.AllocatedStorageBytes);CompressionStorageRatio=([double]$compressed.AllocatedStorageBytes/[double]$before.AllocatedStorageBytes);FinalExecutableBytesReclaimed=0;OtherCapturesModified=0;BatchAuthorized=$false;Attribution='Host compact.exe wall time only; concurrent free-space changes not attributed. Target left uncompressed. No gameplay/performance claim.'}
 $result|ConvertTo-Json -Depth 12|Set-Content -LiteralPath (Join-Path $reportDir 'result.json') -Encoding UTF8;Journal 'restored-success' $result
 [pscustomobject]@{Status=$result.Status;PhysicalBefore=$before.AllocatedStorageBytes;PhysicalCompressed=$compressed.AllocatedStorageBytes;PhysicalRestored=$restored.AllocatedStorageBytes;Ratio=$result.CompressionStorageRatio;CompressMs=$c.HostUtilityWallMilliseconds;UncompressMs=$u.HostUtilityWallMilliseconds;SidecarsUnchanged=$sidecars.Count;Result=(Join-Path $reportDir 'result.json');FinalSpaceReclaimed=0}|ConvertTo-Json
}catch{
 $failure=$_.Exception.ToString();Journal 'failure-preserve' @{Error=$failure;OriginalBytesRetainedInMemory=$true}
 # Only restore compression if current exact identity/bytes, completion, liveness and sharing still admit it.
 try{$s=Admission;FullBytesSame;if($s.Compressed){$null=Invoke-Compact '/U' 'rollback-U';$s=Admission;FullBytesSame;if($s.Compressed-or$s.AllocatedStorageBytes-ne$before.AllocatedStorageBytes){throw 'Rollback state mismatch'};Journal 'rollback-uncompressed' $s}}catch{Journal 'rollback-refused-preserve' @{Error=$_.Exception.ToString()}}
 throw
}
