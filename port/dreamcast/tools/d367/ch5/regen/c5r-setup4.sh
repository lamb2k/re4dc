set -euo pipefail
L=/root/probe/lanes-20261018/ch5regen
rm -rf "${L:?}/venv"
python3 -m venv --without-pip $L/venv
curl -fsSL -o $L/get-pip.py https://bootstrap.pypa.io/get-pip.py
$L/venv/bin/python $L/get-pip.py -q 2>&1 | tail -2
$L/venv/bin/python -m pip -q install numpy==2.5.3 Pillow==12.3.0 2>&1 | tail -3
$L/venv/bin/python -c "import numpy,PIL;print(numpy.__version__,PIL.__version__)"
