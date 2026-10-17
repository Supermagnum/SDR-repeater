#!/bin/bash
# Run inside hpretl/iic-osic-tools:2026.10 with this directory mounted
# as the working directory. Writes solver output under out/, which is
# gitignored. Prints L and Q JSON on stdout.
set -eu
cd "$(dirname "$0")"
PDK_ROOT="${PDK_ROOT:-/foss/pdks}"
GDS="$PWD/vendor/gds2openEMS/workflow/L_2n0_twoport.gds"
STACK_XML="$PDK_ROOT/ihp-sg13g2/libs.tech/openems/openems_ihp_sg13g2/workflow/SG13G2_200um.xml"
PALACE_ONLY_XML="$PDK_ROOT/ihp-sg13g2/libs.tech/palace/workflow/SG13G2_200um.xml"
test -f "$GDS"
test -f "$STACK_XML"
echo "PDK_COMMIT $(cat "$PDK_ROOT/ihp-sg13g2/COMMIT")"
echo "SHARED_STACK $STACK_XML"
sha256sum "$GDS" "$STACK_XML"
if [ -f "$PALACE_ONLY_XML" ]; then
  echo "UNUSED_PALACE_WORKFLOW_XML $PALACE_ONLY_XML"
  sha256sum "$PALACE_ONLY_XML"
fi
echo "openEMS $(openEMS --help 2>&1 | awk '/version/{print; exit}')"
palace --version 2>&1 | awk '/Palace version/{print}'
python3 -c 'import gds2palace_check' 2>/dev/null || true
export GDS2PALACE_WORKFLOW="$PWD/vendor/gds2palace/workflow"
export GDS2OPENEMS_MODULES="$PWD/vendor/gds2openEMS/workflow/modules"
export MPLBACKEND=Agg
mkdir -p out
echo "=== palace model ==="
python3 palace_l2n0.py "$GDS" "$STACK_XML"
CFG=$(find out palace_model "$HOME" /tmp -name config.json -path '*palace_l2n0*' 2>/dev/null | head -1 || true)
# create_sim_path may place the model under /tmp when the script path is used
if [ -z "${CFG}" ]; then
  CFG=$(find /tmp /headless "$PWD" -name 'config.json' -path '*palace_l2n0*' 2>/dev/null | head -1 || true)
fi
echo "PALACE_CONFIG ${CFG}"
test -n "$CFG"
SIMDIR=$(cd "$(dirname "$CFG")" && pwd)
CFG=$(basename "$CFG")
NPROC="${EM_NPROC:-8}"
echo "=== palace solve nproc=${NPROC} dir=${SIMDIR} ==="
(
  cd "$SIMDIR"
  mpirun --bind-to none -n "$NPROC" /foss/tools/palace/bin/palace-x86_64.bin "$CFG"
)
CSV=$(find "$SIMDIR" -name 'port-S.csv' | head -1)
echo "PALACE_CSV ${CSV}"
python3 extract_lq.py palace "$CSV" | tee out/palace_lq.json
echo "=== openems solve ==="
python3 openems_l2n0_2port.py "$GDS" "$STACK_XML"
S2P=$(find "$PWD" /tmp -name 'openems_l2n0_2port.s2p' | head -1)
echo "OPENEMS_S2P ${S2P}"
python3 extract_lq.py s2p "$S2P" | tee out/openems_lq.json
