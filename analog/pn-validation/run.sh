#!/bin/bash
# Phase-noise validation. Run inside the iic-osic-tools container from this folder:
#   ./run.sh               level 1 pnoise (seconds)
#   ./run.sh l2            + level 2 SG13G2 pnoise
#   ./run.sh tran          + transient-noise references for levels 1 and 2 (slow, minutes each)
#   ./run.sh flicker       flicker region: level 3 (exact, + pss_minpts check) and level 4 pnoise
#   ./run.sh flicker-tran  + level 4 transient-noise reference (impractical: 22-37 h, ~140 GB)
#   ./run.sh inject        level 4b: deterministic tone injection vs pnoise (about 20-40 min)
set -e
cd "$(dirname "$0")"
export PDK_ROOT=/foss/pdks PDK=ihp-sg13g2          # VACASK paths must not double the PDK root
export PYTHONPATH=/foss/tools/vacask/lib/vacask/python:$PYTHONPATH
mkdir -p out && cd out
cp ../params.py .
run() { echo "== vacask $1"; vacask "$2${1}" > "${1%.sim}.log" 2>&1 || { echo "FAILED, see out/${1%.sim}.log"; tail -20 "${1%.sim}.log"; exit 1; }; }
case "$1" in
  flicker|flicker-tran)
    run level3_flicker_fm.sim ../
    # Same circuit with 4x the PSS points: the low offsets are the most sensitive to it
    sed -e 's/pss_minpts=16000/pss_minpts=64000/' -e 's/analysis pn3 /analysis pn3h /' \
        ../level3_flicker_fm.sim > level3_flicker_fm_hi.sim
    run level3_flicker_fm_hi.sim ""
    run level4_sg13_tail.sim ../
    if [ "$1" = "flicker-tran" ]; then run level4_tran.sim ../; fi
    python3 ../compare_flicker.py | tee compare_flicker.txt
    ;;
  inject)
    # Level 4b: deterministic injection at the tail bias (replaces the level 4 transient-noise
    # reference, which averages a 14 fs step: 22-37 h). About 20-40 min. Results: out/inject/
    python3 ../level4_inject.py | tee inject.txt
    ;;
  *)
    run level1_ideal.sim ../
    if [ "$1" = "l2" ] || [ "$1" = "tran" ]; then run level2_sg13.sim ../; fi
    if [ "$1" = "tran" ]; then run level1_tran.sim ../; run level2_tran.sim ../; fi
    python3 ../compare.py | tee compare.txt
    ;;
esac
