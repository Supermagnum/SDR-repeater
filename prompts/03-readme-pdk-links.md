# Prompt 03 — Add the IHP SG13G2 links to the main README

You are working in the SDR multiband repeater repository (https://github.com/Supermagnum/SDR-repeater). It contains the design of **HT13G-M**, an open RFIC on **IHP SG13G2** (130 nm SiGe BiCMOS). The chip is pin-compatible with the Semtech SX1255, covers **130–175 MHz and 400–480 MHz**, and is used in the repeater modules and in the LinHT handheld.

**Your job in this session:** add or fix the section in the main `README.md` that links to the IHP SG13G2 PDK files and documentation. Change nothing else in the README.

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

## README: IHP SG13G2 links

Make sure the main `README.md` has a section like the one below (add it if missing, fix broken links, keep the project's own content). As of 2026-10-26 the README has no such section yet. Verify each link resolves before committing it, and record the pinned PDK commit.

```markdown
## Process and PDK: IHP SG13G2

This design targets IHP's SG13G2 130 nm SiGe BiCMOS process through the open-source PDK.
The open PDK is an experimental preview from IHP, not yet tagged for production.

- PDK repository: https://github.com/IHP-GmbH/IHP-Open-PDK
  - Pinned commit used here: `a49358cc`
  - SG13G2 tree: https://github.com/IHP-GmbH/IHP-Open-PDK/tree/main/ihp-sg13g2
  - Process specification and layout rules: `ihp-sg13g2/libs.doc/doc/` in the PDK repository
- PDK documentation: https://ihp-open-pdk-docs.readthedocs.io/en/latest/
- IHP open IP: https://ihp-open-ip.readthedocs.io/en/latest/
- IHP Analog Academy (tutorials): https://github.com/IHP-GmbH/IHP-AnalogAcademy
- AMS chip template and flow for SG13G2 (IIC-JKU): https://github.com/iic-jku/ihp-sg13g2-ams-chip-template
- Tool container: IIC-OSIC-TOOLS, https://github.com/iic-jku/IIC-OSIC-TOOLS (pinned `hpretl/iic-osic-tools:2026.10`)
- PDK contact: openpdk@ihp-microelectronics.com
```

Check the exact path of the process specification and layout-rule documents inside the PDK at the pinned commit and link to that path rather than to a guess. Also mention the known local workaround: the VACASK conversion of `sg13_hv_svaricap` does not elaborate (`v(2,4)` in its well resistance); the repo uses a patched local copy, to be reported upstream.

---

## Output

- The updated **`README.md`**. Only the PDK section is new or changed.
- In the summary: each link with "resolves / does not resolve", and the exact path of the process-specification and layout-rule documents at commit `a49358cc`.

---

## When you stop

1. Commit the output files named above, with a clear message. Do not push to any repository other than this one.
2. Give the owner a short summary:
   - what you did and what you found;
   - what failed or is uncertain;
   - **what decision or review the owner needs to make next**;
   - "Found, not done": anything outside this job that needs attention, with the prompt number that covers it (see `prompts/00-index.md` if it is in the repo).
