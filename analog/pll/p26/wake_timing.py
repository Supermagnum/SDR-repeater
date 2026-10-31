"""Wake / bias-bypass timing shared by the AFE sequencer RTL and the P2.6 step-3 VACASK deck.

Keep these numbers equal to the parameters in `rtl/afe/afe_seq.sv`.
Counts are in reference-clock cycles (32 or 36 MHz). Absolute times below use 36 MHz.
"""

F_REF_NOM = 36e6

# ≥ 6–7 τ of the tail bias RC when bypassed with ~1 kΩ (1 kΩ × 50 pF = 50 ns → 0.35 µs);
# bank / varactor paths are faster. Spec minimum 0.4 µs. 36 cycles = 1.00 µs at 36 MHz
# (1.12 µs at 32 MHz) — margin after MOS Ron and for ≥ 6–7 τ on the tail node.
BYPASS_CYCLES = 36
T_BYPASS = BYPASS_CYCLES / F_REF_NOM

# D15: en_lodiv after the bias bypass has opened (spec/analog-digital-interface.md §6).
# 48 cycles = 1.33 µs at 36 MHz (≥ 1 µs after en_vco, and after T_BYPASS).
LODIV_DELAY_CYCLES = 48
T_LODIV = LODIV_DELAY_CYCLES / F_REF_NOM
