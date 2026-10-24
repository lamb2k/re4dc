#!/usr/bin/env bash
set -euo pipefail
sed -n '1,180p' /root/rr/bin/rr.sh
crontab -l
ps -eo pid,ppid,etimes,stat,args | rg 'rr-watch|rr-cycle|d367-buildslot' | head -20 || true