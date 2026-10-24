#!/usr/bin/env bash
set -euo pipefail
T=/root/work/lanes/audits23-target-on
rg -n -l 're4dc_work_at_em' "$T/port" "$T/src" "$T/include"