# Prompt 04 — Check the module PCB against the RFIC, backplane and K3 Pico-ITX pinouts

You are working in the SDR multiband repeater repository (https://github.com/Supermagnum/SDR-repeater). It contains the design of **HT13G-M**, an open RFIC on **IHP SG13G2** (130 nm SiGe BiCMOS). The chip is pin-compatible with the Semtech SX1255, covers **130–175 MHz and 400–480 MHz**, and is used in the repeater modules and in the LinHT handheld.

**Your job in this session:** check the KiCad project in `PCB/` against the HT13G-M pin map, the backplane signal list and the K3 Pico-ITX connector pinouts. **Read only:** propose changes, do not make them.

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

## Module PCB and host pinouts

### F1. What is in `PCB/` (check it is still so)

A KiCad 9 project (`PCB/sdr-repeater/`, schematic format 20250114), early stage. Placed so far:

| Ref | Part | Maker | What it is | Library files in `PCB/footprints-symbols/` |
|---|---|---|---|---|
| U1 | SX1255IWLTRT | Semtech | Current RFIC; HT13G-M is to be a drop-in in the same package (Option P) | `2026-10-25_02-12-57.kicad_sym`, `MLPQW-32_SEM*.kicad_mod`, `.stl` |
| J1 | 86093967113755ELF | Amphenol FCI | DIN 41612 Style C, 96 pos, right-angle header (module side) | `86093967113755ELF.*` |
| — | 86093968114755V1LF | Amphenol FCI | DIN 41612 96-contact straight, rack/backplane side | `86093968114755V1LF.*` (in library, check if placed) |
| J2 | 1773455 | Phoenix Contact | 5-pos Combicon pluggable power header, 7.62 mm, 16 A | `1773455.kicad_sym`, `PHOENIX_1773455.kicad_mod` |
| J3 | 92_N-50-0-6/111_NY | Huber+Suhner | N connector, PCB mount (antenna port) | `92_N-50-0-6_111_NY.*` |

Re-read the folder; if it has changed, use what is there, not this table.

### F2. Checks (read only; use `kicad-cli` in a scratch copy if you need ERC/DRC or a netlist)

1. **RFIC footprint and pin map.** Compare the SX1255 symbol pins (33 pins incl. exposed pad) and the MLPQW-32 footprint with the HT13G-M pin map in `spec/rf-frontend.md`. Every pin must line up (number, name, direction, supply). This includes the Option P changes: DIO1 = IRQ out, DIO3 = PTT gate in, I2S master by default (`spec/i2s-clocking.md`). List every pin where the drop-in would change what the board must do.
2. **Backplane connector.** Compare J1's pins with the backplane signal summary in the README and `docs/RF-modules.md`:
   - I2S, including the proposed b14/b15 direction change;
   - SPI at 10 MHz;
   - I²C;
   - c1 IRQ and c2 PTT;
   - the +12 V PA, +5 V, +3.3 V and +1.8 V rails;
   - ground.

   Flag any signal that has no pin or no net yet, and any contact over its current rating.
3. **Antenna connector.** The README says RP-SMA on the front panel, optional Type-N. The PCB has an N connector. Record which one the board uses, and make sure the specs say the same thing. Do not pick for the owner.
4. **Power header J2.** Check the 5 poles against the rails the module needs and the PA current.
5. **ERC/DRC.** If ERC or DRC can run, report the results. Do not fix anything in the owner's files.

### F3. K3 Pico-ITX host pinouts (secondary compute platform)

The README (rev 1.8) names the Milk-V Megrez as the primary host and the SpacemiT K3 Pico-ITX as the secondary. On both, the backplane signals go through the ECP5-25F PCIe interface card. The K3 Pico-ITX user guide (V1.3, 2026-09-17) publishes usable connector pinouts. Source: https://www.spacemit.com/community/document/info?nodepath=hardware/eco/k3_pico/pico_user_guide.md&lang=en (PDF: https://cdn-resource.spacemit.com/file/product/K3/k3_pico_ug_en.pdf). If the owner has committed a copy to `docs/`, use that. Use the pinouts as data; check them against the guide before relying on them.

**26-pin FPC, 0.5 mm, 3.3 V IO**

| Pins | Signals |
|---|---|
| 1, 2 | 3.3 V |
| 3, 4 | `R_I2C1_SCL`, `R_I2C1_SDA` |
| 6, 7 | `R_UART0_TX`, `R_UART0_RX` |
| 9, 10 | `UART5_TX`, `UART5_RX` |
| 11, 12 | `RX_PWM1`, `RX_PWM2` |
| 13–16 | `UART10_TX`, `UART10_RX`, `UART10_CTS`, `UART10_RTS` |
| 18, 19 | `R_CAN4_TX`, `R_CAN4_RX` |
| 21, 22 | `R_CAN3_TX`, `R_CAN3_RX` |
| 24, 25 | `R_CAN2_TX`, `R_CAN2_RX` |
| 5, 8, 17, 20, 23, 26 | GND |

**36-pin FPC, 0.5 mm, 1.8 V IO**

| Pins | Signals |
|---|---|
| 1, 2 | 1.8 V |
| 3, 4 | `CAN1_RX`, `CAN1_TX` |
| 6–28 | GMAC-MII (`R_TX_CLK`, `R_TX_D0..3`, `R_RX_CLK`, `R_RX_D0..3`, `R_TX_EN`, `R_CLK_25M`, `R_RX_DV`, `R_PWDN/INTn`, `R_RESETn`, MDIO, `R_CRS`, `R_COL`) |
| 30–33 | `SPI0_MOSI`, `SPI0_MISO`, `SPI0_SCLK`, `SPI0_CS` (one chip select) |
| 35, 36 | `R_CAN0_TX`, `R_CAN0_RX` |
| others | GND |

**Other connectors**

| Connector | What it offers |
|---|---|
| EC header, 3.3 V | `EC_I2C0` CLK/DAT, GND, and two pins that are serial TX/RX or GPIO B2/C0 |
| M.2 B-Key | 2242/3042 cards, PCIe 3.0 ×2 and USB 2.0. A card here drops M-Key to ×2. |
| M.2 M-Key | 2280 NVMe, PCIe 3.0 ×4 |
| UART debug header, RJ45 1G, SFP+ 10G | — |
| Power | ATX 2-pin 12 V up to 7 A, or USB-C PD 20 V |

Points for you to check and write up, not to decide:

- **No I2S on the FPC.** Neither FPC connector carries I2S/SAI, and there is no list of free GPIOs. On the K3 Pico, the IQ path must therefore go through the ECP5 card. The card would sit on PCIe, most likely the M.2 B-Key (an M.2 form factor, or an adapter). Check that the ECP5 card design or spec allows this, and what PCIe ×2 means for 5 slots of IQ.
- **IO levels.** SPI0 is at 1.8 V and the I²C/UART/CAN pins are at 3.3 V. Compare with the RFIC IO voltage and the backplane levels, and say where level shifters are needed.
- **SPI chip selects.** There is only one SPI0 chip select, but five slots. Check how slot select is done (ECP5, or GPIO), if anyone ever wires the K3 FPC to the backplane directly.
- **Other buses.** The CAN-FD and UART lines could serve the chassis manager or PA/PSU monitoring. Note this as an option only.
- **FPC power.** Do not draw module power from the FPC 3.3 V / 1.8 V pins. The guide gives no current rating for them.

Write the result to **`reports/pcb-pinout-check-YYYY-MM-DD.md`**:
- one table per connector: pin, net in the schematic, expected signal, OK / mismatch / missing;
- a list of proposed schematic changes for the owner.

---

## Output

- **`reports/pcb-pinout-check-YYYY-MM-DD.md`**: one table per connector, the K3 points, and the list of proposed schematic changes.
- Leave the KiCad files and libraries unchanged.

---

## When you stop

1. Commit the output files named above, with a clear message. Do not push to any repository other than this one.
2. Give the owner a short summary:
   - what you did and what you found;
   - what failed or is uncertain;
   - **what decision or review the owner needs to make next**;
   - "Found, not done": anything outside this job that needs attention, with the prompt number that covers it (see `prompts/00-index.md` if it is in the repo).
