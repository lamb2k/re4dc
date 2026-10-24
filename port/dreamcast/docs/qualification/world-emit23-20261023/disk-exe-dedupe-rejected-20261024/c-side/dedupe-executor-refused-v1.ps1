# Abort-only guard: no capture mutation executor is admitted or implemented.
param([string]$ControlReceipt = 'C:\Game Dev\Emulators\codex-lanes\world-emit23\DISK-EXE-DEDUPE-CONTROLS-REJECTED-20261024-v1.json')
$ErrorActionPreference='Stop'
$required='FAIL_ABANDONED_NO_CAPTURE_MUTATION'
$receipt=Get-Content -LiteralPath $ControlReceipt -Raw|ConvertFrom-Json
if($receipt.Status -eq $required){throw 'ABANDONED: mandatory readonly atomic-replace primitive failed; no capture operations allowed.'}
throw 'REFUSED: no reviewed passing primitive or admitted executor exists. This guard never mutates captures.'
