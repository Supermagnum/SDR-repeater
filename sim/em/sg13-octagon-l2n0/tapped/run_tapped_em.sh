#!/bin/bash
# Pre-EM checks, then Palace 3-port on the tapped L2n0 GDS.
# Run inside hpretl/iic-osic-tools from sim/em/sg13-octagon-l2n0:
#   EM_NPROC=8 ./tapped/run_tapped_em.sh
set -eu
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PDK_ROOT="${PDK_ROOT:-/foss/pdks}"
GDS="$ROOT/tapped/L_2n0_tapped.gds"
STACK_XML="$PDK_ROOT/ihp-sg13g2/libs.tech/openems/openems_ihp_sg13g2/workflow/SG13G2_200um.xml"
test -f "$GDS"
test -f "$STACK_XML"

echo "=== pre-EM net / R check ==="
python3 tapped/check_tapped_nets.py

export GDS2PALACE_WORKFLOW="$ROOT/vendor/gds2palace/workflow"
export MPLBACKEND=Agg
mkdir -p tapped/out
NPROC="${EM_NPROC:-8}"
CELL="${TAPPED_CELL:-2}"

echo "=== palace model (filled, cell=${CELL} µm) ==="
TAPPED_CELL="$CELL" python3 tapped/palace_l2n0_tapped.py "$GDS" "$STACK_XML"
CFG=$(find "$ROOT" /tmp /headless -name 'config.json' -path '*palace_l2n0_tapped*' 2>/dev/null | head -1 || true)
echo "PALACE_CONFIG ${CFG}"
test -n "$CFG"
SIMDIR=$(cd "$(dirname "$CFG")" && pwd)
CFG=$(basename "$CFG")
echo "=== palace solve nproc=${NPROC} dir=${SIMDIR} ==="
(
  cd "$SIMDIR"
  mpirun --bind-to none -n "$NPROC" /foss/tools/palace/bin/palace-x86_64.bin "$CFG"
)
CSV=$(find "$SIMDIR" -name 'port-S.csv' | head -1)
echo "PALACE_CSV ${CSV}"
cp "$CSV" tapped/out/port-S.csv
python3 tapped/extract_tapped.py "$CSV" tapped/out/summary.json | tee tapped/out/summary.md
