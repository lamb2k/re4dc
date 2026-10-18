set -uo pipefail
cd /root/probe/lanes-20261018/ch5regen
for k in ac9a763b-01fab0d7 6f5596fa-bcdd36eb 844699db-67c782fb 9bcea162-37b9364f 0ea42407-77c3d299 39a44f1b-b2fb1c41; do
  echo "$k: $(find tools/.assets fixtures -name "$k.re4tex" | head -3 | xargs -r stat -c '%s %n' | tr '\n' ' ')"
done
grep -n "^def \|vq\.\|import" tools/port/dreamcast/tools/fit_ps2_world_textures.py | head -40
