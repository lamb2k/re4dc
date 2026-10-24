$ErrorActionPreference='Stop'
$scanUtc=[DateTime]::UtcNow
$roots=@('C:\Flycast-Evidence\re4-dreamcast\stat-bytes23-20261023','C:\Flycast-Evidence\re4-dreamcast\audits23-takeover','C:\Flycast-Evidence\re4-dreamcast\world-emit23-takeover','C:\Flycast-Evidence\re4-dreamcast\dedup-offline23-20261023')
Add-Type -TypeDefinition @"
using System;using System.ComponentModel;using System.Runtime.InteropServices;using Microsoft.Win32.SafeHandles;
public static class OwnedExeNtfsInventory {
 [StructLayout(LayoutKind.Sequential)] struct FileInfo {public uint Attr;public System.Runtime.InteropServices.ComTypes.FILETIME Create,Access,Write;public uint Volume,SizeHigh,SizeLow,Links,IndexHigh,IndexLow;}
 [StructLayout(LayoutKind.Sequential)] struct StandardInfo {public long AllocationSize,EndOfFile;public uint Links;public byte DeletePending,Directory;}
 [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)] static extern SafeFileHandle CreateFile(string p,uint access,uint share,IntPtr sec,uint create,uint flags,IntPtr template);
 [DllImport("kernel32.dll",SetLastError=true)] static extern bool GetFileInformationByHandle(SafeFileHandle h,out FileInfo f);
 [DllImport("kernel32.dll",SetLastError=true)] static extern bool GetFileInformationByHandleEx(SafeFileHandle h,int infoClass,out StandardInfo f,uint bytes);
 public sealed class Result {public string Identity;public uint HardlinkCount;public long AllocationBytes,LogicalBytes;public uint VolumeSerial;}
 public static Result Read(string path) {using(var h=CreateFile(path,0x80,7,IntPtr.Zero,3,0x80,IntPtr.Zero)){if(h.IsInvalid)throw new Win32Exception(Marshal.GetLastWin32Error());FileInfo f;StandardInfo s;if(!GetFileInformationByHandle(h,out f)||!GetFileInformationByHandleEx(h,1,out s,(uint)Marshal.SizeOf(typeof(StandardInfo))))throw new Win32Exception(Marshal.GetLastWin32Error());return new Result{Identity=f.Volume.ToString("X8")+":"+f.IndexHigh.ToString("X8")+f.IndexLow.ToString("X8"),HardlinkCount=f.Links,AllocationBytes=s.AllocationSize,LogicalBytes=s.EndOfFile,VolumeSerial=f.Volume};}}
}
"@
$processes=@(Get-CimInstance Win32_Process)
$liveIds=@{};foreach($p in $processes){$liveIds[[int]$p.ProcessId]=$true}
$liveFlycast=@($processes | Where-Object {$_.Name -like 'flycast*'} | Select-Object ProcessId,Name,ExecutablePath,CommandLine)
$freeBefore=(Get-Volume -DriveLetter C).SizeRemaining
$rows=@()
foreach($root in $roots){
 $rootPath=[IO.Path]::GetFullPath($root).TrimEnd('\')
 foreach($file in @(Get-ChildItem -LiteralPath $rootPath -Recurse -File -Filter flycast.exe)){
  $full=[IO.Path]::GetFullPath($file.FullName);if(-not $full.StartsWith($rootPath+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Outside root'}
  $reasons=[Collections.Generic.List[string]]::new();$cap=$file.DirectoryName
  $reparse=$false;$cursor=Get-Item -LiteralPath $cap
  while($cursor -and $cursor.FullName.Length -ge $rootPath.Length){if(($cursor.Attributes -band [IO.FileAttributes]::ReparsePoint)-ne 0){$reparse=$true};$cursor=$cursor.Parent}
  if($reparse -or (($file.Attributes -band [IO.FileAttributes]::ReparsePoint)-ne 0)){$reasons.Add('reparse-point path')}
  $runPath=Join-Path $cap 'run-result.json';$boundPath=Join-Path $cap 'bounded-launch.json';$run=$null;$bound=$null
  if(-not(Test-Path -LiteralPath $runPath -PathType Leaf)){$reasons.Add('no adjacent run-result')}else{try{$run=Get-Content -LiteralPath $runPath -Raw | ConvertFrom-Json}catch{$reasons.Add('malformed run-result')}}
  if(-not(Test-Path -LiteralPath $boundPath -PathType Leaf)){$reasons.Add('no adjacent bounded-launch')}else{try{$bound=Get-Content -LiteralPath $boundPath -Raw | ConvertFrom-Json}catch{$reasons.Add('malformed bounded-launch')}}
  if($run){if($run.status -ne 'RUN_COMPLETE'){$reasons.Add('run not RUN_COMPLETE')};if($run.errors.Count -gt 0){$reasons.Add('run errors')};try{$end=[DateTimeOffset]::Parse($run.end_utc).UtcDateTime;if($end -gt $scanUtc.AddMinutes(-5)){$reasons.Add('new completion within five-minute exclusion')}}catch{$reasons.Add('missing/invalid end_utc')}}
  if($bound){if($bound.guest_exited -ne $true){$reasons.Add('guest_exited not true')};if($bound.deadline_fired -ne $false){$reasons.Add('deadline_fired not false')};if(-not $bound.pid){$reasons.Add('missing bound PID')}elseif($liveIds.ContainsKey([int]$bound.pid)){$reasons.Add('bound PID still exists (including reuse)')}}
  $pidPath=Join-Path $cap 'flycast.pid';$recordedPid=$null
  if(Test-Path -LiteralPath $pidPath -PathType Leaf){$text=(Get-Content -LiteralPath $pidPath -Raw).Trim();if($text -match '^\d+$'){$recordedPid=[int]$text;if($liveIds.ContainsKey($recordedPid)){$reasons.Add('recorded flycast.pid still exists (including reuse)')}}else{$reasons.Add('malformed flycast.pid')}}
  foreach($active in $liveFlycast){if($active.ExecutablePath -and ([IO.Path]::GetFullPath($active.ExecutablePath) -eq $full)){$reasons.Add('live executable path')}}
  $before=[OwnedExeNtfsInventory]::Read($full);$hash=(Get-FileHash -LiteralPath $full -Algorithm SHA256).Hash.ToLowerInvariant();$after=[OwnedExeNtfsInventory]::Read($full);$file.Refresh()
  if($before.Identity -ne $after.Identity -or $before.LogicalBytes -ne $after.LogicalBytes -or $before.HardlinkCount -ne $after.HardlinkCount){$reasons.Add('identity/size/link count changed during hash')}
  $rows += [pscustomobject]@{Root=$rootPath;Path=$full;Capture=$cap;Size=$after.LogicalBytes;AllocationBytes=$after.AllocationBytes;Sha256=$hash;FileId=$after.Identity;HardlinkCount=$after.HardlinkCount;Attributes=[string]$file.Attributes;LastWriteUtc=$file.LastWriteTimeUtc.ToString('o');BoundPid=if($bound){$bound.pid}else{$null};RecordedPid=$recordedPid;RunStatus=if($run){$run.status}else{$null};RunEndUtc=if($run){$run.end_utc}else{$null};GuestExited=if($bound){$bound.guest_exited}else{$null};DeadlineFired=if($bound){$bound.deadline_fired}else{$null};RunReceiptSha256=if(Test-Path -LiteralPath $runPath){(Get-FileHash -LiteralPath $runPath -Algorithm SHA256).Hash.ToLowerInvariant()}else{$null};BoundReceiptSha256=if(Test-Path -LiteralPath $boundPath){(Get-FileHash -LiteralPath $boundPath -Algorithm SHA256).Hash.ToLowerInvariant()}else{$null};Eligible=($reasons.Count-eq 0);Exclusions=@($reasons)}
 }
}
# Group by NTFS identity before pricing: logical duplicate paths are not independent allocation.
$identities=@()
foreach($group in @($rows | Group-Object FileId)){
 $first=$group.Group[0];$links=@();if($first.HardlinkCount -gt 1){$links=@(& fsutil.exe hardlink list $first.Path 2>&1);if($LASTEXITCODE -ne 0){throw 'Hardlink enumeration failed'}}else{$links=@($first.Path.Substring(2))}
 $identities += [pscustomobject]@{FileId=$first.FileId;Sha256=$first.Sha256;AllocationBytes=$first.AllocationBytes;HardlinkCount=$first.HardlinkCount;ObservedPaths=$group.Count;AllObservedEligible=(@($group.Group | Where-Object {-not $_.Eligible}).Count-eq 0);AllHardlinksInInventory=($group.Count-eq $first.HardlinkCount);LinkNames=@($links)}
}
$groups=@()
foreach($group in @($rows | Where-Object Eligible | Group-Object Sha256)){
 $ids=@($identities | Where-Object {$_.Sha256 -eq $group.Name -and $_.AllObservedEligible -and $_.AllHardlinksInInventory})
 $allocated=($ids|Measure-Object AllocationBytes -Sum).Sum;if($null-eq $allocated){$allocated=0};$canonicalCost=if($ids.Count-gt 0){[long]($ids|Measure-Object AllocationBytes -Maximum).Maximum}else{0}
 $groups += [pscustomobject]@{Sha256=$group.Name;EligiblePaths=$group.Count;EligibleDistinctIdentities=$ids.Count;ReclaimableSourceAllocationBytes=[long]$allocated;NewCanonicalAllocationBytes=$canonicalCost;NetPotentialBytes=[Math]::Max(0,[long]$allocated-$canonicalCost)}
}
$reasons=@($rows|Where-Object {-not $_.Eligible}|ForEach-Object {$_.Exclusions}|Group-Object|Select-Object Name,Count)
$result=[ordered]@{Schema='OWNED_COMPLETED_FLYCAST_EXE_DEDUPE_INVENTORY_V1';ScanUtc=$scanUtc.ToString('o');ReadOnlyInventory=$true;CleanupMutation=$false;CFreeBytesBefore=[long]$freeBefore;CFreeBytesAfter=[long](Get-Volume -DriveLetter C).SizeRemaining;AllowedRoots=$roots;MinimumCompletionAgeMinutes=5;ActiveFlycastProcesses=$liveFlycast;TotalPaths=$rows.Count;EligiblePaths=@($rows|Where-Object Eligible).Count;UniqueFileIds=$identities.Count;LogicalBytes=[long]($rows|Measure-Object Size -Sum).Sum;NetPotentialBytes=[long]($groups|Measure-Object NetPotentialBytes -Sum).Sum;ExclusionSummary=$reasons;ShaGroups=$groups;FileIdentities=$identities;Files=$rows;Attribution='Potential is allocation-level upper bound after subtracting one NEW canonical per SHA. No space reclaimed. All existing links must be eligible/in inventory; any additional outside link prevents that old allocation being priced.'}
$out='C:\Game Dev\Emulators\codex-lanes\world-emit23\DISK-EXE-DEDUPE-INVENTORY-20261024-v1.json'
if(Test-Path -LiteralPath $out){throw 'Preserve existing inventory'}
$result|ConvertTo-Json -Depth 12|Set-Content -LiteralPath $out -Encoding UTF8
[pscustomobject]@{Inventory=$out;InventorySha256=(Get-FileHash -LiteralPath $out -Algorithm SHA256).Hash.ToLowerInvariant();TotalPaths=$result.TotalPaths;EligiblePaths=$result.EligiblePaths;UniqueFileIds=$result.UniqueFileIds;PotentialGiB=([double]$result.NetPotentialBytes/1GB);FreeGiB=([double]$result.CFreeBytesAfter/1GB);Exclusions=$reasons;ShaGroups=$groups}|ConvertTo-Json -Depth 5
