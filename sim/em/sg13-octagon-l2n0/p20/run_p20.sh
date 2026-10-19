#!/bin/bash
# P2.0 matched-mesh study of SG13_Octagon_L2n0 (spec/phase2-plan.md).
# Run inside hpretl/iic-osic-tools:2026.10 after the Phase 0 setup in ../ (the
# vendor/ checkouts of gds2palace v0.8.2 and gds2openEMS v0.5.0 must exist there).
#
#   ./run_p20.sh stage1          cheap steps: Palace 5/3/2 um, openEMS 2/1 um
#   ./run_p20.sh stage2          filled-metal Palace ladder (3/2/1 um, via fill-factor correction)
#                                and openEMS 0.7 um
#   ./run_p20.sh stage3          optional, heavy: openEMS 0.5 um; surface-model Palace 1 um, order 3, AMR
#   ./run_p20.sh pal2 oem1 ...   any listed steps
#   ./run_p20.sh summary         tables and verdict from what has finished
#
# Steps run one after another (never in parallel). Each writes out/p20/<step>.json and
# out/p20/<step>.log. A finished step is skipped on a re-run; delete its json to redo it.
set -u
cd "$(dirname "$0")"
HERE="$PWD"
L2N0="$(cd .. && pwd)"
PDK_ROOT="${PDK_ROOT:-/foss/pdks}"
GDS="$L2N0/vendor/gds2openEMS/workflow/L_2n0_twoport.gds"
STACK_XML="$PDK_ROOT/ihp-sg13g2/libs.tech/openems/openems_ihp_sg13g2/workflow/SG13G2_200um.xml"
export GDS2PALACE_WORKFLOW="$L2N0/vendor/gds2palace/workflow"
export GDS2OPENEMS_MODULES="$L2N0/vendor/gds2openEMS/workflow/modules"
COMBINE="$L2N0/vendor/gds2palace/scripts/combine_extend_snp.py"
export MPLBACKEND=Agg
NPROC="${EM_NPROC:-8}"
export EM_NPROC="$NPROC"
mkdir -p out/p20

# step: solver cell order amr
declare -A STEP=(
  [pal5]="palace 5 2 0"   [pal3]="palace 3 2 0"   [pal2]="palace 2 2 0"   [pal1]="palace 1 2 0"
  [pal2o3]="palace 2 3 0" [palamr]="palace 5 2 2"
  [palF3]="palace 3 2 0 F" [palF2]="palace 2 2 0 F" [palF1]="palace 1 2 0 F"
  [oem2]="openems 2.0 - -" [oem1]="openems 1.0 - -" [oem07]="openems 0.7 - -" [oem05]="openems 0.5 - -"
)
STAGE1="pal5 pal3 pal2 oem2 oem1"
STAGE2="palF3 palF2 palF1 oem07"
STAGE3="oem05 pal1 pal2o3 palamr"

check_inputs() {
  for f in "$GDS" "$STACK_XML" "$GDS2PALACE_WORKFLOW/gds2palace/__init__.py" "$GDS2OPENEMS_MODULES"; do
    [ -e "$f" ] || { echo "MISSING $f (run the Phase 0 setup in $L2N0 first)"; exit 1; }
  done
  echo "PDK_COMMIT $(cat "$PDK_ROOT/ihp-sg13g2/COMMIT" 2>/dev/null || echo unknown)"
  sha256sum "$GDS" "$STACK_XML"
}

run_palace() {  # tag cell order amr [F = filled metals + via fill-factor correction]
  local tag=$1 cell=$2 order=$3 amr=$4 filled=0 log="out/p20/$1.log" t0 cfg simdir csv deemb
  [ "${5:-}" = F ] && filled=1
  t0=$(date +%s)
  P20_TAG=$tag P20_CELL=$cell P20_ORDER=$order P20_AMR=$amr P20_FILLED=$filled P20_FFC=$filled \
    python3 -u p20_palace.py "$GDS" "$STACK_XML" >"$log" 2>&1 || { echo "  model generation failed, see $log"; return 1; }
  cfg=$(awk '/^CONFIG /{print $2}' "$log" | tail -1)
  [ -f "$cfg" ] || { echo "  no config.json reported, see $log"; return 1; }
  simdir=$(cd "$(dirname "$cfg")" && pwd)
  echo "  solving in $simdir (nproc $NPROC)"
  ( cd "$simdir" && mpirun --bind-to none -n "$NPROC" /foss/tools/palace/bin/palace-x86_64.bin "$(basename "$cfg")" ) >>"$log" 2>&1 \
    || { echo "  Palace failed, see $log"; return 1; }
  # final port-S.csv (with AMR: the top-level one is the last iteration)
  csv=$(find "$simdir" -path '*iteration*' -prune -o -name port-S.csv -print | head -1)
  [ -n "$csv" ] || csv=$(find "$simdir" -name port-S.csv | sort | tail -1)
  ( cd "$simdir" && python3 "$COMBINE" ) >>"$log" 2>&1 || echo "  combine_extend_snp failed (no de-embedded file), see $log"
  deemb=$(find "$simdir" -path '*iteration*' -prune -o -name '*_deembedded.s2p' -print | grep -v '_dc_' | head -1)
  P20_CELL=$cell P20_ORDER=$order P20_AMR=$amr P20_FILLED=$filled P20_SECONDS=$(( $(date +%s) - t0 )) \
    python3 p20_extract.py "$tag" palace palace "$csv" "${deemb:-}" | tee -a "$log"
  python3 "$L2N0/vendor/gds2palace/scripts/palace_summary.py" "$simdir" >>"$log" 2>&1 || true
}

run_openems() {  # tag cell
  local tag=$1 cell=$2 log="out/p20/$1.log" t0 s2p
  t0=$(date +%s)
  P20_TAG=$tag P20_CELL=$cell python3 -u p20_openems.py "$GDS" "$STACK_XML" >"$log" 2>&1 \
    || { echo "  openEMS failed, see $log"; return 1; }
  s2p=$(awk '/^S2P /{print $2}' "$log" | tail -1)
  [ -f "$s2p" ] || { echo "  no .s2p reported, see $log"; return 1; }
  grep -iE "cells|mesh" "$log" | head -3
  P20_CELL=$cell P20_SECONDS=$(( $(date +%s) - t0 )) \
    python3 p20_extract.py "$tag" openems s2p "$s2p" | tee -a "$log"
}

[ $# -ge 1 ] || { sed -n 2,13p "$0"; exit 1; }
if [ "$1" = summary ]; then python3 p20_summary.py; exit; fi
check_inputs
steps=()
for a in "$@"; do
  case "$a" in
    stage1) steps+=($STAGE1) ;;
    stage2) steps+=($STAGE2) ;;
    stage3) steps+=($STAGE3) ;;
    *) [ -n "${STEP[$a]:-}" ] || { echo "unknown step $a"; exit 1; }; steps+=("$a") ;;
  esac
done
for s in "${steps[@]}"; do
  if [ -f "out/p20/$s.json" ]; then echo "== $s: done earlier, skipped"; continue; fi
  read -r solver cell order amr model <<<"${STEP[$s]}"
  [ "$order" = "-" ] && order=""; [ "$amr" = "-" ] && amr=""
  echo "== $s: $solver, cell $cell um${order:+, order $order}${amr:+, AMR $amr}${model:+, filled metals + via correction}  ($(date '+%F %T'))"
  if [ "$solver" = palace ]; then run_palace "$s" "$cell" "$order" "$amr" "${model:-}"; else run_openems "$s" "$cell"; fi
done
python3 p20_summary.py
