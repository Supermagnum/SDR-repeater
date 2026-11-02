"""Wake / bias-bypass / D22 amp-cal timing shared by AFE sequencer RTL and P2.6 decks.

Keep equal to parameters in `rtl/afe/afe_seq.sv` and `rtl/afe/bandcal.sv`.
Counts are in reference-clock cycles (32 or 36 MHz). Absolute times use 36 MHz.
"""

F_REF_NOM = 36e6

# ≥ 6–7 τ of the tail bias RC when bypassed; spec minimum 0.4 µs.
# 36 cycles = 1.00 µs at 36 MHz (1.12 µs at 32 MHz).
BYPASS_CYCLES = 36
T_BYPASS = BYPASS_CYCLES / F_REF_NOM

# D15: en_lodiv after the bias bypass has opened.
LODIV_DELAY_CYCLES = 48
T_LODIV = LODIV_DELAY_CYCLES / F_REF_NOM

# D22 amplitude SAR settle per bit (bypass closed); matches bandcal.AMP_SETTLE.
AMP_SETTLE_CYCLES = 36
AMP_BITS = 5
AMP_PHASES = 2  # pre-band + touch-up
AMP_CAL_CYCLES = AMP_PHASES * AMP_BITS * AMP_SETTLE_CYCLES  # 360
T_AMP_CAL = AMP_CAL_CYCLES / F_REF_NOM  # 10.00 µs at 36 MHz

# D20 band calibration (nearest-code): 1398 cycles = 38.83 µs at 36 MHz
BAND_CAL_CYCLES = 1398
T_BAND_CAL = BAND_CAL_CYCLES / F_REF_NOM

# Combined band+amp calibration while hold/bypass asserted
T_CAL_TOTAL = T_BAND_CAL + T_AMP_CAL  # ≈ 48.83 µs

# Prior wake (D20 only): 99–120 µs. Extra amp cal ≈ +10 µs → 109–130 µs ≤ 150 µs.
T_WAKE_MIN = 99e-6 + T_AMP_CAL
T_WAKE_MAX = 120e-6 + T_AMP_CAL
T_WAKE_LIMIT = 150e-6
