#!/bin/bash
# Short transient-noise trials, run inside the container from this folder.
#
#   ./tran_diag.sh         three 0.5 us trials of level4_tran.sim: zoh (as committed), sde,
#                          zoh with noisefmax 20 GHz. Prints average step, run time, and the
#                          projected run time and file size for the full 80 us. Each trial
#                          stops after 45 min (timeout) and its rawfile is deleted afterwards.
#   ./tran_diag.sh cause   level 4 with noise off, level 4 with flicker from 50 kHz, and level 2,
#                          0.5 us each: which part forces the 14 fs step.
#   ./tran_diag.sh l1sde   level 1 transient (10.5 us) in sde mode, checked against the exact
#                          closed form (<= 1 dB, as zoh was). Needed before sde is used for level 4.
#
# Background (2026-10-20): the 80 us level 4 run in zoh mode averaged a 17 fs time step
# (1.38e9 points in 23.9 us), projecting 29 h and 111 GB. zoh noise changes in steps every
# 10 ps, which the VACASK documentation notes can force extra LTE step reductions; sde noise
# is continuous. Results go to out/diag/.
set -e
cd "$(dirname "$0")"
export PDK_ROOT=/foss/pdks PDK=ihp-sg13g2
export PYTHONPATH=/foss/tools/vacask/lib/vacask/python:$PYTHONPATH
HERE=$PWD
mkdir -p out/diag && cd out/diag
cp "$HERE/params.py" "$HERE/compare.py" .

trial() {   # trial <name> <source .sim> <target stop time, s> <sed expressions...>
  local name=$1 src=$2 target=$3; shift 3
  sed -e "s/analysis tn\([0-9]\) tran/analysis $name tran/" "$@" "$HERE/$src" > "$name.sim"
  echo "== $name"
  local t0 rc=0; t0=$(date +%s)
  timeout 45m vacask "$name.sim" > "$name.log" 2>&1 || rc=$?
  local wall=$(( $(date +%s) - t0 ))
  [ $rc -eq 124 ] && echo "  stopped after 45 min (timeout); projection from the partial file"
  [ $rc -ne 0 ] && [ $rc -ne 124 ] && { echo "  vacask failed (exit $rc):"; tail -5 "$name.log"; }
  [ -s "$name.raw" ] && python3 "$HERE/rawprogress.py" "$name.raw" --target "$target" --wall "$wall"
  return 0
}

if [ "$1" = "l1sde" ]; then
  trial l1sde level1_tran.sim 10.5e-6 -e 's/noisemode="zoh"/noisemode="sde"/'
  python3 - <<'EOF'
import math
import numpy as np
from vacask.rawfile import rawread
import params as P
from compare import tran_fit_at_1mhz
d = rawread("l1sde.raw").get()
t, v = np.real(d["time"]), np.real(d["t"])
# Amplitude of the fundamental from the analytic signal of the band 0.75-1.25 f0
dt = 5e-12
tu = np.arange(t[0] + 0.5e-6, t[-1], dt); vu = np.interp(tu, t, v)
sp = np.fft.fft(vu); f = np.fft.fftfreq(len(vu), dt)
f0 = f[f > 0][np.argmax(np.abs(sp[f > 0]))]
band = (f >= 0.75 * f0) & (f <= 1.25 * f0)
amp = float(np.mean(np.abs(np.fft.ifft(np.where(band, 2 * sp, 0)))[len(vu)//20:-len(vu)//20]))
lfit, nb = tran_fit_at_1mhz(t, v)
lcf = P.lc_closed_form_dbc(1e6, amp)
ok = abs(lfit - lcf) <= 1
print(f"level 1, sde: f0 {f0/1e9:.4f} GHz, A1 {amp:.4f} V; 1/df^2 fit at 1 MHz {lfit:.2f} dBc/Hz "
      f"({nb} bins) vs closed form {lcf:.2f}: {lfit - lcf:+.2f} dB  {'PASS' if ok else 'FAIL'} (<= 1 dB; zoh gave +0.96)")
EOF
  exit 0
fi

if [ "$1" = "cause" ]; then
  # First trials (2026-10-20): zoh 14 fs average step at 50 GHz and at 20 GHz noise bandwidth
  # (so not the bandwidth); sde aborted (timestep too small). Which part forces the step?
  trial n0   level4_tran.sim 80.5e-6 -e 's/stop=80.5u/stop=0.5u/' -e 's/ noisemode="zoh" noisefmax=50G noisefmin=10k oversample=1//'
  rm -f n0.raw     # level 4 with noise off: is it the circuit?
  trial f50  level4_tran.sim 80.5e-6 -e 's/stop=80.5u/stop=0.5u/' -e 's/noisefmin=10k/noisefmin=50k/'
  rm -f f50.raw    # flicker only down to 50 kHz, as level 2
  trial l2   level2_tran.sim 80.5e-6 -e 's/stop=10.5u/stop=0.5u/'
  rm -f l2.raw     # the validated level 2 transient (ideal tail), same settings
  echo "Send this output back."
  exit 0
fi

trial z    level4_tran.sim 80.5e-6 -e 's/stop=80.5u/stop=0.5u/'
rm -f z.raw
trial s    level4_tran.sim 80.5e-6 -e 's/stop=80.5u/stop=0.5u/' -e 's/noisemode="zoh"/noisemode="sde"/'
rm -f s.raw
trial z20  level4_tran.sim 80.5e-6 -e 's/stop=80.5u/stop=0.5u/' -e 's/noisefmax=50G/noisefmax=20G/'
rm -f z20.raw
echo "Send this output back. If sde has a much larger average step, run ./tran_diag.sh l1sde next."
