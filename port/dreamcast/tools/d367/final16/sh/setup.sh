set -e
R=/root/work/re4-dreamcast
L=/root/probe/lanes-20261016/final16
mkdir -p $L
cd $R
git ls-remote origin 'refs/heads/lane/final16*' || true
if [ ! -d $L/tree ]; then
  git worktree add -b lane/final16 $L/tree origin/lane/ch5found16
fi
cd $L/tree
git config user.name lamb2k; git config user.email nansenlamb1@gmail.com
git log --oneline -1
git merge --no-edit -m "final16: merge lane/stress16b 44c2bdf4 (Saddler em31 stress tooling) into lane/ch5found16 8627a5df" origin/lane/stress16b 2>&1 | tail -20 || true
git status --short | head -30
