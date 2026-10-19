@echo off
rem run-trace.cmd <scenario> <seconds> <stop tick>: one logic-trace Flycast run (called under WSL trace_lock.sh by t-run.sh TRACE=1)
cd /d "C:\Game Dev\Emulators\re4-assets-private\world-agent-20260926\continuation-20260927\playability-r11-r1"
set RE4DC_LOG_STOP_TICK=%3
python run-emulator-novsync-i26.py %1 --seconds %2 --period 30 > scenarios\%1-run-stdout.txt 2>&1
