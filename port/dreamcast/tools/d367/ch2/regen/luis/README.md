# r11c Luis + merchant13 registry replay (dc/native/r11c/registry.re4nmr aa417c6c, 245,088 B: byte-exact)
Codex rollouts 2026-10-13 (rollx.py/show.py extract the calls). Order:
1. luis_a.py inputs (pl14 PS2 4949d656 / GC 2b5b554d); luis_a.py gun (tree 4837f203, key 779fa0ca); luis_a.py actor2 (tree e0fc9745, coverage 75c2655e)
2. lu2.sh: ps2_cast_native gun + ps2_luis_native v2 (header 6fc18144); luis_b.py gun (finish + regcast-luis-gun); luis_b.py mask; lu3.sh (pvrtex + vq_export, d9de79c8 b43a0f27)
3. luis_b.py cand (candidate-v2 = v1 cast layout + v2 overrides)
4. m13n.sh + m13.py inputs/convert/native/finish/masks/regcast (tree f9d5b8c5)
5. r11cm.sh r11c (ps2cast m13.sh rooms r104 + cast16 r11c room add, merge_cast, cast16 r11cm.sh at 8d401351 --pool)
