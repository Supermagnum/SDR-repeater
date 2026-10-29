# Prompt 01 — Audit the RFIC work and verify the recorded results

You are working in the SDR multiband repeater repository (https://github.com/Supermagnum/SDR-repeater). It contains the design of **HT13G-M**, an open RFIC on **IHP SG13G2** (130 nm SiGe BiCMOS). The chip is pin-compatible with the Semtech SX1255, covers **130–175 MHz and 400–480 MHz**, and is used in the repeater modules and in the LinHT handheld.

**Your job in this session:** find out from the files what is done, re-run the scripts that produce the key results, and check them against their limits. **Do no new design work.**

---

## Hard rules (read before doing anything)

- **No fabrication.** The chain stops before any tape-out submission, order, or shuttle registration (`docs/HANDOFF.md`). Produce reviewed schematics, layouts, simulations and reports only.
- **Topologies and architecture choices are made by the human owner.** You write a topology memo with options and a proposal, then stop. Do not start a schematic for a block whose topology is not recorded as accepted in `decisions.md` or the block's memo.
- **Do not reverse an accepted decision** (D1–D20 and any later ones; D19 = loop filter 60 kHz / 55°, D20 = 8-bit VCO bank with nearest-code calibration and V_tune monitor). If a result shows a decision is wrong, write it up as a finding with numbers and a proposal, and stop.
- **Never clone, fork, or push to the LinHT repository.**
- **Do not write host-side calibration code** (`host/gr4/`) until the owner says so.
- **The `PCB/` folder belongs to the owner.** Do not edit, re-save, re-annotate or reformat `PCB/sdr-repeater/sdr-repeater.kicad_sch`, `.kicad_pcb` or `.kicad_pro`. KiCad backups (`*-backups/`), `fp-info-cache` and `*.kicad_prl` are git-ignored since 2026-10-25; never commit them or force-add them. Do not change the library files in `PCB/footprints-symbols/`. Proposed schematic or layout changes go in a report (`reports/pcb-pinout-check-*.md`).
- **Every PCB part must be on SnapEDA** (CAD symbol and footprint available). New symbols and footprints come from SnapEDA in the same format as the ones already in `PCB/footprints-symbols/`. Only propose them; the owner adds them.
- **Everything needed to build the RFIC must be in the GitHub repo** (owner rule 2026-10-25 in `decisions.md`, "Repository contents"). If something is only on your machine or in a container, it is not done. That means:
  - xschem `.sch` schematics with an SVG/PDF export of each, from P2.7;
  - netlists, simulation decks, and the run summaries `out/summary_*.txt`;
  - layouts as `.gds.gz`;
  - DRC/LVS reports;
  - rendered chip pictures (PNG/SVG from the GDS with KLayout).

  Regenerable bulk output stays out: waveforms, raw data, build directories. Follow `.gitignore`. A full-chip GDS too large for a normal commit goes to a GitHub Release. **Chip art on the die is deferred to Phase 5** until the owner has chosen the graphic; do not design or pick one.
- **Do not invent results.** Every number in a report carries its source tag: `[DS]` datasheet / PDK documentation, `[HAND]` hand estimate, `[MODEL]` Python system model, `[SCH]` schematic simulation, `[EM]` EM simulation, `[PEX-RC]` post-layout extraction. If a simulation did not run or did not converge, say so; do not replace it with an estimate without saying so.
- Use the pinned tools: container `hpretl/iic-osic-tools:2026.10`, PDK commit **`a49358cc`** (check it is what the scripts actually load). Simulator settings and the validated phase-noise method: `analog/pn-validation/README.md`. Do not upgrade the PDK or container without asking.
- Keep the existing writing style of the specs: short sentences, tables, plain English, numbers with units and tags.
- **Do only the job in this prompt.** If you find other work that needs doing, list it under "Found, not done" in your summary and leave it.

---

## Step 1 — Audit: what exists

Read, at least:

- `README.md`, `docs/HANDOFF.md`, `decisions.md`, `docs/RF-modules.md`
- `spec/rf-frontend.md`, `spec/derived-limits.md`, `spec/phase2-plan.md`
- `spec/vco-topology.md`, `spec/lo-divider-topology.md`, `spec/pll-topology.md`
- `spec/analog-digital-interface.md`, `spec/provisional-tank-q.md`
- `docs/rf-switches-and-filters.md` (or wherever the RF switch/filter survey lives)
- `reports/phase2-review/` (all files)
- `analog/` — `pn-validation/`, `pll-model/`, `vco/` (step1–3), `lo/` (step1–3), `pll/` (step1–4), `pll/p26/` (step1–4), and anything newer
- `rtl/afe/` — `mmd.sv`, `bandcal.sv`, `lockdet.sv`, the Σ-Δ, and the cocotb tests
- `rtl/digital/` and the back-end layout run (`phase1l`, area 339 617 of 340 000 µm²)
- `tools/` (e.g. `vhf_lpf_check.py`)
- `PCB/` — the KiCad project `PCB/sdr-repeater/` and the libraries in `PCB/footprints-symbols/` (read only)
- `spec/i2s-clocking.md`, `spec/baseline-decisions.md`, `docs/repo-map.md`, and the README sections on the backplane and the compute host

Then write **`reports/status-YYYY-MM-DD.md`** with one table per phase:

| Step | Status in the spec | Files that prove it | Re-run OK? | Open points |
|---|---|---|---|---|

Flag every mismatch between what a spec says is done and what the files show (missing script, missing output, result not reproducible, spec text out of date).

---

## Step 2 — Verify: expected results

Re-run the scripts that produce the key numbers (they are meant to be re-runnable). Compare against the table below. A result passes if it meets the limit; small differences from the recorded value (≤ 0.5 dB, ≤ 2 %) are fine, larger ones must be explained.

### Phase 2 — LO and synthesizer (current phase)

| Item | Limit | Recorded result | Where |
|---|---|---|---|
| Tank (L2n0) Q | — | 14.2 / 15.3 / 16.9 at 3.12 / 3.5 / 4.2 GHz; lumped model within 0.71 % of EM | `spec/provisional-tank-q.md`, `analog/vco/step1/` |
| VCO range, 8-bit trimmed bank (D20), all 15 corner × temperature cases | covers 3.12–4.20 GHz with margin for ±3 % L (≈ ±47 MHz) | 2.914–4.414 GHz typ; all cases cover; bottom 2.77–3.05 GHz (least margin 66 MHz, MIM best case), top 4.35–4.55 GHz | `analog/vco/step2/out/summary_8bit.txt`, `analog/vco/step3/out/summary_8bit*.txt`, `spec/vco-topology.md` §9 |
| VCO band steps (D20) | even, so V_tune lands inside its window | every carry 0.94–1.07 × its neighbours; 0.24–0.29 V of V_tune per step; per-bit trim 0.971…0.933 | `analog/vco/step2/out/summary_steps.txt` |
| VCO phase noise at 1 MHz | VHF ≤ −116, UHF ≤ −115 dBc/Hz | 8-bit typ: −124.4 … −119.9 dBc/Hz, worst margin +3.9 dB at 4.20 GHz; 7-bit with 4 mA cap (D12): +3.6 dB at ss 85 °C | `analog/vco/step3/out/summary_8bit.txt`, `summary_4ma.txt` |
| VCO K_VCO | 14–47 MHz/V (D8) | 13.1–38.8 MHz/V | same |
| Peak V_GS / V_GD | ≤ 1.5 V (1.65 V process limit) | ≤ 1.48 V | same |
| VCO tail current | ≤ 4 mA (D12) | 3.4–4.0 mA per band | same |
| LO dividers, all corners | divide correctly | all pass except ss −40 °C with the pessimistic 0.27 V swing (passes with the real VCO swing) | `analog/lo/step3/` |
| LO divider Monte Carlo | all samples divide | 100 / 100 | same |
| UHF I/Q phase | raw image ≥ 35 dB at 3σ (≥ 40 dB after host cal) | σ 0.47° tt, 0.77° ss | same |
| VHF 8-phase error | input to Phase 3 HR budget | σ 0.17° tt, 0.28° ss | same |
| UHF 25 % duty | ≈ 25 % | 22.6–25.8 % | same |
| Divider chain noise floor | ≤ −150 dBc/Hz at the LO output | VHF −154.9 / −154.0 / −155.5 dBc/Hz at 1–3 / 3–10 / 10–30 MHz `[SCH]` (transient noise, 200 fs rms). **UHF does not converge** (÷2 / Johnson counter at 1.92 GHz); taken as ≈ −150 `[HAND]`, right at the limit | `analog/pll/p26/step2/out/summary_lo1.txt`, `spec/pll-topology.md` §13 |
| LO current | ≤ 10 mA typical (D7) | ≈ 9.65 mA VHF typ; PLL now ≈ 1.0 mA (0.43 mA `[SCH]`, rest `[HAND]`) of the 1.8 mA allowance | `spec/lo-divider-topology.md` §9, `analog/pll/step3/out/summary_cur.txt` |
| Loop (D19) | 60 kHz / 55° actual | C1 30.8 pF, C2 465 pF, R1 22.9 kΩ, R3 108 kΩ, C3 3.1 pF. The P2.2 2π sizing error is fixed in `pll_model.py` | `analog/pll-model/`, `analog/pll/p26/step1/` |
| Total phase noise at the duplex offset `[MODEL]` | ≤ −136 dBc/Hz at RF (25 W); VHF at 600 kHz, UHF at 2 MHz | VHF 130 / 175 MHz: −141.7 / **−138.8 (+2.8 dB, worst)**; UHF 400 / 480 MHz: −145.2 / −143.7 (32 MHz reference) | `analog/pll/p26/step2/out/summary_total.txt` |
| Wake (calibration + settling) | ≤ 150 µs | 83–120 µs `[MODEL]`; band calibration 38.8 µs (nearest code) | `spec/pll-topology.md` §13 |
| V_tune after calibration (D20) | inside 0.25–0.95 V with drift margin | 0.34–0.82 V at all corners `[MODEL]` | same |
| PFD / charge pump | no dead zone; up/down match | no dead zone; INL ≤ 3.6 ps (step 2a); Monte Carlo INL ≤ 3.9 ps, lock point ±0.09 ns, loop-gain spread ≤ 0.6 % (step 3); with the real bias INL ≤ 2.1 ps (step 4) | `analog/pll/step2/`–`step4/` |
| Charge-pump noise | — (P2.2 assumed FoM −218 dBc/Hz) | FoM −203.8 … −205.6 dBc/Hz, 1/f corner 79–141 kHz `[SCH]`. **Accepted by the owner as it is** | `analog/pll/p26/step2/out/summary_cp.txt` |
| Bias generator | I_cp within a few % | within 2 % of V_REF / R_B over corners and ±10 % supply; start-up ≤ 0.6 µs, and the start-up circuit turns off | `analog/pll/step4/` |
| Lock-detector window delay | 5–12 ns | 5.5–10.0 ns over corners, MIM, R_B ±20 %, supply; lock detector two-sided | same |
| V_tune hold switch (D19 filter) | mean error over first count ≤ 10 mV | τ 0.65–0.70 µs, ≤ 7.6 mV, leakage ≤ 7.6 nA | `analog/pll/step4/out/summary_hold_d19.txt` |
| MMD, Σ-Δ, band cal, lock detector (RTL) | all cocotb tests pass; Σ-Δ bit-exact against Python | pulse-swallow MMD, every ratio 16–127; `run` input (in-phase start); 8-bit nearest-code band cal | `rtl/afe/` (re-run the cocotb tests) |
| MMD first 2/3 cell | ≥ 1.3 × 2.2 GHz at ss | 2.9 GHz (1.32×), 10/10 mismatch samples | `analog/pll/step1/` |
| Transistor-level closed loop (P2.6 step 3) | locks from power-on | locks, filter scaled 5×: within 7 ppm from 16 µs; UP 3.50 / DN 0.29 ns; VCO 0.97 V diff. Needs start-up bypass on **all** VCO bias resistors, closed ≥ 0.4 µs | `analog/pll/p26/step3/out/summary_s5.txt`, `summary_2u.txt` |
| Reference spur (D19 loop) `[MODEL]` | ≤ −67 dBc (TX), ≤ −84 dBc (RX) | −109.3 dBc at RF, worst case (5 µA leakage) | `analog/pll/p26/step4/` (writes `out/summary.txt`) |
| Fractional boundary spur `[MODEL]` | ≤ −95 dBc | −123.0 dBc VHF, −126.0 dBc UHF (INL 3.9 ps); −116.5 dBc at 10 ps | same |

### Other existing results

| Item | Limit | Recorded result | Where |
|---|---|---|---|
| Digital back end | signed off | `phase1l`, 339 617 / 340 000 µm² | `rtl/digital/` |
| VHF harmonic LPF (board) | ≤ ~0.5 dB loss 130–175 MHz (Q 100/500), ≥ 70 dB from 256 MHz | 0.37–0.94 dB, ≥ 70.6 dB; MC ±2 % ≥ 65.4 dB | `tools/vhf_lpf_check.py` |

If a re-run differs from the recorded result by more than the tolerance, or fails its limit: record it in the status report, find the cause (script change, PDK change, wrong corner, method problem), and **stop for review** before building on it.

If a `reports/pdk-tool-issues-*.md` exists (prompt 02), every result it lists under "Results to re-check" must be re-run here. A result counts as passed only if you re-ran it in this session; otherwise mark it "not re-run" and give the reason (tool missing, run time, no convergence).

---

## Output

- **`reports/status-YYYY-MM-DD.md`** with:
  - the audit table, one per phase;
  - a pass / fail / not-re-run table for every row in Step 2;
  - the list of mismatches between the specs and the files.
- Do not change the specs or the design files. Write any correction they need as a finding in the report.

---

## When you stop

1. Commit the output files named above, with a clear message. Do not push to any repository other than this one.
2. Give the owner a short summary:
   - what you did and what you found;
   - what failed or is uncertain;
   - **what decision or review the owner needs to make next**;
   - "Found, not done": anything outside this job that needs attention, with the prompt number that covers it (see `prompts/00-index.md` if it is in the repo).
