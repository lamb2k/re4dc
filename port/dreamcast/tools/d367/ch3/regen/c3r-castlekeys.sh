set -euo pipefail
L=/root/probe/lanes-20261018/ch3regen
S=/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch3regen
V=$L/trees/origin/lane/castle-1015/port/dreamcast/tools/d367/vram
{ grep -v '^#' "$V/vq16-c31.txt" | cut -d' ' -f1; grep -v '^#' "$V/vq16-c32.txt" | cut -d' ' -f1
  printf '%s\n' 1f706b85-a3a5a27c 45780136-ce6cd0af 5498155d-18d309bd 5faee1db-099f72b1 8ae599ab-81faeb23 8fb3f08f-aa8205df ae7dbfdd-0de5a07d e5209b2b-f15e113b ef071711-6dbe99cb 328a61a7-e4983cff 67a581c9-a3339122 97b79a1a-2c730f73 \
    18f8a477-36daa0ed bff20ed7-81bf193e cba25b9f-85b58969 d6480ddc-76810580 2270bb80-7e974480 119ec0e0-ea7b99d5 091dc6a0-641ccd27 f8e76302-b983fc64 e80798e0-772ec609 2ba66557-6649a502 2e49209c-cb3151cc
} | grep . | sort -u > "$S/castlekeys.txt"
wc -l < "$S/castlekeys.txt"
