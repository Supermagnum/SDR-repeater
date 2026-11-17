#!/bin/bash
set -e
cd "$(dirname "$0")"
for mode in local east vert full; do
  echo "======== D9_MODE=$mode ========"
  FILTER_PART=d9 FILTER_D9_MODE=$mode python3 build_cells.py --stage g --nets power,tail,filter > /tmp/b_$mode.txt
  python3 -c "
import os, sys
sys.path.insert(0, '.')
from run_drc_lvs import run, OUT, PDK_LVS
cell = 'tail_block'
lvs_dir = os.path.join(OUT, 'lvs_' + cell)
os.makedirs(lvs_dir, exist_ok=True)
run(['python3', PDK_LVS,
     f'--layout={OUT}/{cell}.gds', f'--netlist={OUT}/{cell}.spice',
     f'--topcell={cell}', f'--run_dir={lvs_dir}',
     '--disable_tap_extraction', '--ignore_top_ports_mismatch',
     '--combine_devices', '--top_lvl_pins'],
    f'{OUT}/lvs_klayout_{cell}.log', timeout=600)
"
  python3 check_join_ports.py || true
done
