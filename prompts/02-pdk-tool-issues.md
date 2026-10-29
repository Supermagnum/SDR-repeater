# Prompt 02 — Check the design against known PDK and tool issues

You are working in the SDR multiband repeater repository (https://github.com/Supermagnum/SDR-repeater). It contains the design of **HT13G-M**, an open RFIC on **IHP SG13G2** (130 nm SiGe BiCMOS). The chip is pin-compatible with the Semtech SX1255, covers **130–175 MHz and 400–480 MHz**, and is used in the repeater modules and in the LinHT handheld.

**Your job in this session:** find every known bug in the IHP SG13G2 open PDK and in the tools the flow uses that can affect this design, and record whether it is fixed, worked around, or still open. **Do not change the design, the PDK pin or the container pin.**

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

## Known issues in the PDK and tools

Check whether the design is affected by known bugs in the PDK and the tools, and whether it has been fixed or worked around.

**Where to look:**
- IHP-Open-PDK issues, open and closed: https://github.com/IHP-GmbH/IHP-Open-PDK/issues
- The issue trackers of every tool the flow uses, at the pinned versions in `hpretl/iic-osic-tools:2026.10`:
  - VACASK, including the OpenVAF / Verilog-A model compilation it uses
  - ngspice
  - openEMS
  - KLayout, including the SG13G2 DRC and LVS decks
  - Magic
  - netgen
  - LibreLane / OpenROAD (digital back end)
  - IIC-OSIC-TOOLS: https://github.com/iic-jku/IIC-OSIC-TOOLS/issues
- The PDK and tool changelogs or commit logs between the pinned versions and the current ones.
- Any other tool the repo actually uses: read the scripts and Makefiles to find them, do not rely on this list alone.

**What to check:**

1. **Relevant issues.** List every issue that touches a device, model, rule or tool feature this design uses. At least these:
   - the LV and HV MOS PSP models;
   - `sg13_hv_svaricap`;
   - `cap_rfcmim` and the MIM capacitors;
   - the inductor and EM layer stack and openEMS setup files;
   - `npn13G2`;
   - resistors;
   - the stdcell and IO libraries;
   - corner and Monte Carlo mismatch files;
   - the DRC, LVS and PEX decks;
   - seal ring and filler.

   Search the issues by device and keyword, not only by title.
2. **Status of each issue.** Classify each one:
   - **affects us, not handled:** finding, with the affected results named;
   - **affects us, worked around:** say where in the repo the workaround is and whether it is documented;
   - **fixed upstream after `a49358cc`:** say which commit or release fixed it and which of our results would change;
   - **does not affect us:** one line saying why.
3. **Known local workarounds.** Confirm they are documented and reported upstream. One is the patched `sg13_hv_svaricap` VACASK model (`v(2,4)` term in the well resistance). If it has not been reported, draft the issue text in `reports/upstream-issues/`. **Do not post it yourself**; the owner submits it.
4. **Method limits that may be tool bugs.** Check whether these match a known tool issue:
   - the unusable pss/pnoise result on TSPC logic (P2.4 step 3);
   - the non-convergence at reltol 1e-7 on the full VCO;
   - the noisy transient that fails on the UHF ÷2 / Johnson counter at 50 / 20 / 10 GHz noise bandwidth, while the VHF chain converges (P2.6 step 2);
   - the earlier first-trial failures ("timestep too small", DC operating point with supplies).

   A known fix or workaround here can close P2.6 open point 3.
5. **Updating the pin.** If an upstream fix changes models or rules this design depends on, **do not update the PDK or container pin yourself**. Write what would change, which simulations must be rerun, and the expected effect, and propose the update to the owner.

Write the result to **`reports/pdk-tool-issues-YYYY-MM-DD.md`**:

| Source | Issue (link) | Affects | Status | Our handling | Results to re-check |
|---|---|---|---|---|---|

Any result listed under "Results to re-check" counts as unverified until prompt 01 has re-run it.

---

## Output

- **`reports/pdk-tool-issues-YYYY-MM-DD.md`**: the issue table, plus a list of the results to re-check.
- **`reports/upstream-issues/*.md`**: drafted issue texts, if any are needed. Do not post them.

---

## When you stop

1. Commit the output files named above, with a clear message. Do not push to any repository other than this one.
2. Give the owner a short summary:
   - what you did and what you found;
   - what failed or is uncertain;
   - **what decision or review the owner needs to make next**;
   - "Found, not done": anything outside this job that needs attention, with the prompt number that covers it (see `prompts/00-index.md` if it is in the repo).
