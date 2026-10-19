set -euo pipefail
# sc19.sh: engine19 bench scenes (1, 2, 4 = actorplan19 scenes unchanged; 3 = r101 bell spot, the engine19 crosss view)
S=/root/work/lanes/engine19-scratch/bench/scenes
mkdir -p $S
A=/root/work/lanes/actorplan19/k/scenes
cp $A/scene1.txt $A/scene2.txt $A/scene4.txt $S/
cat > $S/scene3.txt <<'EOF'
name bench-r101-bellspot
# engine19 wall-check bench, scene 3 = /cd/dc/bench3.txt: the r101 bell-fight start spot facing the square (engine19
# crosss view; walls hide about 0.6 Ganados per picture), alerted at room frame 30, god, no pad input.
# Settle room frames 0..299, measure 300..1199 (30 s).
room 0x101
pos -7914 0 -254
ang 2.9600
find 0x00002000
inv default
god
alert 30
alivelog 150
bench 3 300 1200 R101 BELL
EOF
ls -l $S
