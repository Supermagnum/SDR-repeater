# Prompt 05 — Write the parts list for the repeater RF module

You are working in the SDR multiband repeater repository (https://github.com/Supermagnum/SDR-repeater). It contains the design of **HT13G-M**, an open RFIC on **IHP SG13G2** (130 nm SiGe BiCMOS). The chip is pin-compatible with the Semtech SX1255, covers **130–175 MHz and 400–480 MHz**, and is used in the repeater modules and in the LinHT handheld.

**Your job in this session:** write the parts list (BOM) for the repeater RF module board, from the KiCad schematic and the specs. **Do not touch the KiCad files.**

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

## Parts list

Write **`PCB/BOM.md`** and the same data as **`PCB/BOM.csv`**. These are new files next to the KiCad project; do not touch the KiCad files. Cover the repeater RF module board:
- parts already placed in the schematic;
- parts the specs require but that are not placed yet:
  - the RF switches and filters from `docs/rf-switches-and-filters.md`;
  - the VHF harmonic LPF from `tools/vhf_lpf_check.py`;
  - the GRF5604 PA and 2× PE4312C-Z attenuators;
  - the RX attenuators;
  - the reference oscillator (TCXO/VCTCXO);
  - the RFIC pin decoupling from `spec/rf-frontend.md`;
  - regulators, level shifters, the open-drain IRQ buffer, the temperature sensor on I²C, and connectors.

Columns:

| Ref | Qty | Function | Value / key spec | Manufacturer | MPN | Package / footprint | In schematic? | SnapEDA symbol + footprint? | Library file in `PCB/footprints-symbols/` | Source (spec file / section) | Notes / alternates |
|---|---|---|---|---|---|---|---|---|---|---|---|

Rules:
- **Refs.** Take refs and values from the schematic for placed parts. Use `TBD-n` refs for parts not yet placed.
- **SnapEDA.** Check each MPN on SnapEDA and mark yes / no / not checked. A part with no SnapEDA symbol and footprint gets a "needs alternate" note, with a candidate alternate that has them.
- **Lifecycle.** Mark parts that are obsolete, not recommended for new designs, or single-source, if the maker's page says so. Give the link.
- **No buying.** Do not choose parts for purchase, add prices, or place orders. The list is for the owner's review.
- **No invented part numbers.** If a value is not settled in the specs, write `TBD` and name the spec that will settle it.
- **The RFIC line.** Record U1 as SX1255IWLTRT today, with the note "replace with HT13G-M (drop-in, Option P) when available".
- **Kept in step.** Update the BOM whenever a spec or the schematic changes a part. Put a short change log at the top of `BOM.md`.

If a `reports/pcb-pinout-check-*.md` exists (prompt 04), use its findings. A part it proposes adding gets a `TBD-n` line marked "proposed in the pinout check".

---

## Output

- **`PCB/BOM.md`** and **`PCB/BOM.csv`**, holding the same data.
- In the summary: how many parts are placed and how many are not placed yet, the parts with no SnapEDA symbol and footprint, the parts with a lifecycle warning, and the values still `TBD`.

---

## When you stop

1. Commit the output files named above, with a clear message. Do not push to any repository other than this one.
2. Give the owner a short summary:
   - what you did and what you found;
   - what failed or is uncertain;
   - **what decision or review the owner needs to make next**;
   - "Found, not done": anything outside this job that needs attention, with the prompt number that covers it (see `prompts/00-index.md` if it is in the repo).
