# Decisions

Human decisions for the SG13G2 VHF/UHF RFIC. An entry is added only after a person approves it.

## 2026-10-17 — Phase 0 review

Approved:

- Container `hpretl/iic-osic-tools:2026.10`.
- PDK commit `a49358cc0b20635fcb53c0940505e3563763fc7a`, the commit named in that image. It contains the RF MOSFET LVS change (pull request 1246, merge `f7bca326`) and is 26 hours before `dev` `89d42ee`. `89d42ee` is not pinned. The two commits have diverged: 43 commits are only on `dev`, and 48 commits are only in the image, mostly the `sg13g2_stdcell_hv` library.
- KLayout DRC flag `--minimum_drc`.
- EM workflows `gds2palace` `v0.8.2` (`ed063dc9`) and `gds2openEMS` `v0.5.0` (`99d8bd18`). Stack-up XML is taken from the pinned PDK commit.
- CACE `fossi-foundation/cace` 2.13.0.
- cocotb 2.1.0 from the image. No project venv.
- Rejections: `efabless/cace`, `AliSahafi/Analog_OpenSource_ihp`, QUCS-COPEN.
- ngspice 47 experimental PSS is allowed. Phase-noise results stay lower confidence.
- Supply assumption replaced by regulated host rails, with buck ripple and spur tolerance required. See `spec/baseline-decisions.md`.
- PLL references 32 MHz and 36 MHz. Spur map: `spec/integer-boundary-spurs.md`.
- I2S slot width 16 or 32 bits, MSB-justified, 16-bit baseline.
- LinHT facts stay provisional. USB-A part numbers wait.

Recorded after those approvals, not a new topology decision: `SG13_Octagon_L2n0` L and Q at 2.4 GHz and 3.5 GHz are in `reports/phase0-review/em-l2n0.md`. That file is a regression baseline. It is not a pass or fail against a specification.

Not approved at that point: any analog topology, and any push.

## 2026-10-17 — Phase 0 EM review

Approved:

- Stay on PDK `a49358cc`. Do not follow `dev`. Reconsider the PDK pin only at a phase review gate.
- The image commit does contain the RF MOSFET LVS change. `rfmos_extraction.lvs` extracts `rfnmos`. `rfmos_model_mapping.lvs` is not in the image.
- Both EM solvers use the pinned-PDK openEMS stack-up `SG13G2_200um.xml`, sha256 `5d452943`. The Palace workflow XML in the same commit is a different stack and is not used. Hashes are in `reports/phase0-review/em-l2n0.md`.
- Matched mesh, shared port de-embedding, and a comparison to a compact model or IHP measured data are required before Phase 2. They are not a Phase 1 blocker. No compact model and no `L2n0` measured file were found in this PDK commit.
- Provisional tank Q is the openEMS value: 11.8 at 2.4 GHz and 14.9 at 3.5 GHz. See `spec/provisional-tank-q.md`.
- Phase 1 digital back end may start. Analog topology is still not approved.

## 2026-10-17 — Phase 1 review, not approved

The first Phase 1 submission was not approved. The resubmission is on `phase1/digital` and is waiting for review. It is not an approval and it is not a topology decision.

Recorded in `reports/phase1-review/summary.md`:

- SPI frame approved. Register map frozen at this gate, addresses `0x00` through `0x13`.
- I2S master by default, and the b14/b15 direction change, approved as a proposal. 16-bit slots at 500 kHz are the repeater recommendation. The 36 MHz three-clock BCLK cells miss the i.MX93 S12 pulse-width window. The K3 datasheet publishes no slave pulse-width limit.
- Proposed signoff junction temperature is 100 °C. The PDK liberty has no 85 °C or 100 °C corner. The 125 °C slow corner is reported from the post-CTS database.
- The 45 dB alias limit stays provisional pending Phase 3 modulator co-design.
- LinHT IQ stays provisional.
- Placed area is above the 0.25 mm² target. See the review for the measured core and cell area.
- The matched-mesh inductor study may run in parallel. It has not been started. Phase 2 has not been started and still needs approval.


## 2026-10-18 — Hold clock uncertainty
Setup uncertainty stays at CLOCK_UNCERTAINTY_CONSTRAINT (0.25 ns). Hold uncertainty is 0.05 ns
(`set_clock_uncertainty -hold 0.05`), because clocks are propagated after CTS and the
TCXO/VCTCXO reference jitter is in the picosecond range. The previous 0.25 ns on hold, plus
the 0.1 ns resizer margin and 5 % derate, drove 6,449 hold buffers.

## 2026-10-18 — SPI mode 0 and power-up reset
MISO changes on the SCLK falling edge; the host samples on the rising edge (mode 0).
Previously MISO changed on the rising edge, which would have shifted every read by one
bit on a real host. Board requirement: rst_n must be held low at power-up until the
supplies and the reference clock are stable (asynchronous reset, level-sensitive).

## 2026-10-18 — CACE version and maximum IQ rate
CACE: use 2.11.0, the version in hpretl/iic-osic-tools:2026.10 (manifest updated).
Maximum RFIC IQ sample rate: 500 kHz (25/50/100/200/500 kHz). README updated from 1 MHz /
32 MHz BCLK to 500 kHz / about 16 MHz BCLK. Matches the LinHT 500 kHz target, keeps BCLK
within the i.MX93 SAI slave limits, and keeps the Sigma-Delta oversampling ratio at 64/72.

## 2026-10-18 — I2S format: Philips (standard I2S)
Master and slave use Philips I2S: LRCLK low = left (I), high = right (Q), changing one bit
before each MSB; data and LRCLK change on the BCLK falling edge, sampled on the rising edge.
Previously data changed on the rising edge (the host's sampling edge) in both modes.
Reset: clk domain released through a 2-flop synchroniser; SCLK must stay idle >= 1 us after rst_n rises.
Test note: logic on gated clocks updates after clk's rising edge in RTL simulation, so
testbenches drive inputs on clk's falling edge.

## 2026-10-18 — Continuous I2S BCLK
BCLK runs without gaps at every rate: frame = 2 * slot * bit_cell reference clocks.
36 MHz / 500 kHz enabled (BCLK 18 MHz: over the 16 MHz repeater-backplane cap, which applies
to the 32 MHz repeater modules, but within the i.MX93 SAI slave limits for LinHT).
36 MHz / 200 kHz: no 50 % split exists (180 = 2*18*5); 40/60 duty, exactly on the i.MX93 limit.
Accepted and documented; LinHT should prefer 100 kHz or 500 kHz.

## 2026-10-18 — Frequency coverage 130–175 MHz + 400–480 MHz; duplexer confirmed

- **Decision:** the RFIC tunes 130–175 MHz and 400–480 MHz, covering amateur bands, land mobile and PMR446. This replaces the amateur-only baseline (README 11.1).
- **Owner input:** repeater sites share one antenna between RX and TX through a duplexer on 2 m and on 70 cm.
- **Norwegian offsets:** 600 kHz (2 m) and 2 MHz (70 cm), taken from the repeater list.
- **Limits:** derived in `spec/derived-limits.md` and replace the provisional ones.
- **Consequences, Phase 3 analog:**
  - harmonic-reject VHF mixer and/or preselector;
  - LO plan with a VCO at 3.12–4.20 GHz, ÷8 for UHF and ÷24 for VHF (as `band_sel` in the RTL);
  - analog anti-alias of ≥ 40 dB at ±8/9 MHz and ≥ 70 dB at ±32/36 MHz;
  - selectable TX reconstruction filter.
- **Consequences, system:**
  - the host picks the 32 or 36 MHz clock per channel by the harmonic table;
  - 500 kHz TX is for simplex use only.
- **Digital backend:** unchanged.
