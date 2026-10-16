#!/bin/bash
# trace-run.sh <scenario> <secs> <stoptick> (WSL): one trace Flycast run under trace_lock.sh (path quoting kept in a file)
exec bash /root/probe/lanes-20261015/actorplan/port/dreamcast/tools/d367/trace_lock.sh /mnt/c/Windows/System32/cmd.exe /c 'C:\Flycast-Evidence\re4-dreamcast\actorplan-20261015\_tools\run-trace.cmd' "$1" "$2" "$3"
