#!/bin/bash
# build_c16.sh (WSL): trace / check / play ELFs for the C16 landing (landA), labels w16crT, w16cmW, w16crP.
cd /root/probe/worldtest16-20261016/landA
for a in ${ARMS:-rT mW rP}; do
  T=/root/probe/worldtest16-20261016/landA K=/root/probe/worldtest16-20261016/k LP=w16c bash port/dreamcast/tools/d367/test15/t15-build.sh $a 2>&1 | tail -2 | cut -c1-140
done
