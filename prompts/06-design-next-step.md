# Prompt 06 — Do the next design step (one item only)

You are working in the SDR multiband repeater repository (https://github.com/Supermagnum/SDR-repeater). It contains the design of **HT13G-M**, an open RFIC on **IHP SG13G2** (130 nm SiGe BiCMOS). The chip is pin-compatible with the Semtech SX1255, covers **130–175 MHz and 400–480 MHz**, and is used in the repeater modules and in the LinHT handheld.

**Your job in this session:** do the single next open item of the RFIC design work, then stop for review.

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

## Remaining design work, in order

**Do exactly one item per session: the first one in this list that is not done and whose prerequisites are met.** Where an item has lettered parts (a), (b), (c), do only one lettered part, the first open one. Then stop, even if the next item looks easy.

Before you start:
1. Read `decisions.md`, `spec/phase2-plan.md` §3 and the newest `reports/status-*.md` (from prompt 01).
2. If that report marks a result as failed or unverified, and the result bears on your item, stop. Name the result and ask the owner to run prompt 01 first.
3. Say in one line which item you are doing and why it is the first open one.

When the item is done, update the relevant spec's status line and results section, and `spec/phase2-plan.md` §3.

State on 2026-10-31 (check the files, they win over this line): P2.0–P2.6 are accepted. Open point 2 (start-up bypass) done 2026-10-31. **Next: open point 1 (V_tune monitor), then one UHF LO-floor method attempt.** Check `decisions.md` and `spec/phase2-plan.md` before you start.

1. **P2.6 result review gate.** If `decisions.md` does not record the P2.6 result as accepted, **stop here**. Give the owner a one-page summary of the P2.6 table and these four open points:
   1. V_tune window monitor comparators (D20) are not yet designed.
   2. Start-up bypass switches are needed on all VCO bias resistors (bank plates, varactor bias, tail filter), closed ≥ 0.4 µs at wake (≥ 6–7 time constants). They must go into the VCO schematic and the sequencer (`spec/analog-digital-interface.md` §6).
   3. The UHF LO-chain floor is only an estimate (≈ −150 dBc/Hz, right at the limit) because transient noise does not converge on the UHF chain.
   4. Charge-pump in-band noise: improve it only if an in-band requirement appears.

   Ask which of 1–3 must be done before P2.7.
2. **After acceptance, close the P2.6 open points** (each with a short plan in the spec first):
   - (a) **Start-up bypass:** add the switches to the VCO schematic (all bias resistors) and the wake sequence to the sequencer RTL and `spec/analog-digital-interface.md` §6. Re-run the step-3 closed loop with the bypass from the sequencer, not by hand, plus the 150 µs wake budget. The step-3 note says the bypass opened at 4 τ left a 2 % residue; check ≥ 6–7 τ.
   - (b) **V_tune monitor (D20):** two comparators at ≈ 0.30 / 0.90 V driving `PLL_STATUS`[4:5]. Size them, run corners and offset Monte Carlo, and check hysteresis and current. Check that the RTL flags and the register map agree.
   - (c) **UHF LO floor:** find a method that converges on the UHF ÷2 / Johnson counter at 1.92 GHz. For example, simulate the UHF chain alone, use sampled-edge jitter from a noiseless transient plus per-device noise, or use smaller time steps or a shorter run. Then compare with −150 dBc/Hz. If it is above −150, write a finding with the effect on the UHF total phase noise, and stop.
   - (d) Optional, only if the owner asks: hold-switch margin (2 × 500 Ω divider or SETTLE0 = 96); lower charge-pump in-band noise.
3. **Open P2.3 items:** VCO amplitude calibration (peak detector → `VCO_BIAS`) or a per-corner table; supply pushing and LDO noise budget (D10); HBT core comparison (D1); the real CML buffer load on the VCO (P2.6 step 3 saw the VCO run 0.45 % above the step-2 prediction without it; recheck the band prediction with the load).
4. **P2.7 layout:**
   - VCO, dividers and PLL in KLayout/Magic, DRC/LVS clean (netgen), PEX;
   - the tapped L2n0 inductor re-run in openEMS (the current EM layout has no centre tap);
   - LO routing EM and post-layout pnoise;
   - the integer-boundary coupling budget as a layout target: raw ≤ −35 dBc (VHF) / −15 dBc (UHF) at the VCO before the loop (`spec/pll-topology.md` §13 step 4).

   From here, every schematic is xschem `.sch` with an SVG/PDF export. Layouts are committed as `.gds.gz` with DRC/LVS reports and KLayout-rendered PNG/SVG pictures (repository-contents rule). **Phase 2 review gate.**
5. **Interface item:** expose `rx_on` / `tx_on` from the back end at the next back-end layout run (`phase1m`). Propose only; do not run it without owner approval.
6. **Phases 3–5** (only after the Phase 2 gate): write topology memos, then stop:
   - RX chain: LNA, passive mixer with HR on VHF, TIA/AAF, Σ-Δ ADC;
   - TX chain: Σ-Δ DAC, reconstruction filter, IQ modulator, attenuator, PA driver at −5 dBm;
   - chip top: SX1255 pad map, POR, level shifters, supplies.

   Chip art waits for the owner's choice of graphic (Phase 5).

Out of scope for you: building or measuring the board filter, choosing parts for purchase, anything for 23 cm.

---

## Output

- The design files for that one item: scripts, decks and `out/summary_*.txt`. From P2.7 on, also the xschem `.sch` files with SVG/PDF exports, `.gds.gz` layouts, DRC/LVS reports and rendered pictures.
- The updated spec sections and `spec/phase2-plan.md` §3.
- If the item is a review gate, its output is a one-page summary for the owner, and nothing else.

---

## When you stop

1. Commit the output files named above, with a clear message. Do not push to any repository other than this one.
2. Give the owner a short summary:
   - what you did and what you found;
   - what failed or is uncertain;
   - **what decision or review the owner needs to make next**;
   - "Found, not done": anything outside this job that needs attention, with the prompt number that covers it (see `prompts/00-index.md` if it is in the repo).
