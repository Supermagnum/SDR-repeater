#!/bin/bash
# Phase-noise validation. Run inside the iic-osic-tools container from this folder:
#   ./run.sh          level 1 pnoise (seconds)
#   ./run.sh l2       + level 2 SG13G2 pnoise
#   ./run.sh tran     + transient-noise references for both levels (slow, minutes each)
set -e
cd "$(dirname "$0")"
export PDK_ROOT=/foss/pdks PDK=ihp-sg13g2          # VACASK paths must not double the PDK root
export PYTHONPATH=/foss/tools/vacask/lib/vacask/python:$PYTHONPATH
mkdir -p out && cd out
cp ../params.py .
run() { echo "== vacask $1"; vacask "../$1" > "${1%.sim}.log" 2>&1 || { echo "FAILED, see out/${1%.sim}.log"; tail -20 "${1%.sim}.log"; exit 1; }; }
run level1_ideal.sim
if [ "$1" = "l2" ] || [ "$1" = "tran" ]; then run level2_sg13.sim; fi
if [ "$1" = "tran" ]; then run level1_tran.sim; run level2_tran.sim; fi
python3 ../compare.py | tee compare.txt
