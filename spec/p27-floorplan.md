# P2.7 synthesizer floorplan memo

Status: **D23 accepted (Option A), 2026-11-11** (`decisions.md`). Companion plan: `spec/p27-layout-notes.md` § Plan. Die context: SX1255-compatible MLPQ-W 5 × 5 mm, 32 leads (`spec/rf-frontend.md` §2); digital back end `phase1l` **339 617 µm²** of 340 000 (`decisions.md` 2026-10-19). Pin 3 = **VR_ANA1** (D21).

---

## 1. Constraints that drive placement

| Constraint | Number / rule | Source |
|---|---|---|
| Digital already placed | 339 617 µm²; no area left in back end | `[SCH]` phase1l |
| AFE/LO control (D3) | Separate small digital island next to PLL (MMD, Σ-Δ, bandcal, lockdet, afe_seq) | D3 |
| VR_ANA1 | Pin 3; LDO → 10 Ω → pad → 100 nF; VCO+LO+CP from **pad** side | D21 |
| Loop-filter MOS | C1 30.8 + C2 465 pF ≈ **0.062 mm²** | D19 `[HAND]` |
| LDO Cg | 100 pF ≈ **0.0125 mm²** MOS preferred | D21 / `p27-layout-notes` |
| Tank inductor | Tapped L2n0; keep clear of digital and CP switching | `[EM]` tapped |
| LO RF path | Short VCO → buffer → CML ÷N; retimed CMOS toward mixer (Phase 3) | P2.4 |
| Coupling target | Raw ≤ **−35 dBc** VHF / **−15 dBc** UHF at VCO before the loop | `pll-topology` §13 |
| Local GHz bypass | MIM/MOS at VCO CT and each CML/TSPC supply tap | D21 layout note |

Die aspect for this memo: assume a ~**1.6 × 1.6 mm** active core inside the 5 × 5 package (typical for this class) `[HAND]`; exact die size is Phase 5. Coordinates below are relative: N = pin-1/3 edge (VR_ANA1 / VR_PA), S = RF_IN / RF_OP edge (pins 27–30), E/W = remaining pad sides.

---

## 2. Area sketch for the synthesizer island `[HAND]`

| Block | Area | Notes |
|---|---|---|
| Tapped L2n0 + keep-out | ≈ 0.05–0.06 mm² | Octagon + metal exclusion; tank not redesigned |
| VCO core / bank / var / amp-cal / bypass | ≈ 0.16–0.22 mm² | P2.7.2a compact [HAND]; was 0.10–0.14 |
| **VCO island (L2n0 + VCO analogue)** | **≤ 0.30 mm²** | **D23 amended 2026-11-12** (was 0.15–0.20); compact 0.22–0.28 |
| LO buffer + CML + converter + TSPC | ≈ 0.05–0.08 mm² | Dual chains, one powered |
| PFD + CP + replica + bias + I_cp DAC | ≈ 0.03–0.05 mm² | |
| Loop filter (D19) | ≈ 0.062 mm² | MOS C1/C2 + MIM C3 |
| V_tune hold + window delay + monitors | ≈ 0.01–0.02 mm² | |
| VR_ANA1 LDO + 10 Ω + Cg | ≈ 0.02–0.03 mm² | Cg 0.0125 mm² |
| AFE/LO digital (D3) | ≈ 0.01–0.02 mm² | Outside phase1l budget |
| **Synth analog + AFE digital** | **≈ 0.40–0.52 mm²** | Excludes phase1l; VCO island raised |
| Routing / guard / fill | ≈ 0.08–0.12 mm² | |
| **Synth island total** | **≈ 0.50–0.62 mm²** | Aspect ~1:1 to 1.5:1 |

---

## 3. Option A — “Inductor NW, quiet; digital SE; RF south”

**Placement:** L2n0 in the **NW** corner (near pin 3 / VR_ANA1). VCO core and bank immediately east of the inductor (short CT and tank leads). LO buffer on the south face of the VCO; CML ÷2/÷3 and converter continue south toward the future mixer / RF edge. PFD / CP / bias and the D19 loop filter in a **NE** strip, east of the bank, with V_tune running east–west ≤ ~150 µm. VR_ANA1 LDO sits next to pin 3 (west of inductor or between pad and 10 Ω). **phase1l digital** stays **SE / S** (away from inductor). AFE/LO control abuts the PLL east side.

| Metric | Estimate `[HAND]` |
|---|---|
| Synth island area / aspect | ≈ 0.50 mm²; ~700 × 700 µm |
| VCO→buffer→CML path | ≈ 80–150 µm differential |
| V_tune line (CP/LF → varactor) | ≈ 100–200 µm |
| Inductor ↔ digital (phase1l) | ≈ 500–800 µm edge-to-edge |
| Inductor ↔ charge pump | ≈ 250–400 µm |
| Guard / DNW | Deep-n-well under VCO+LO; guard ring around inductor; substrate ties dense at VCO/CP boundary; digital on its own ring |
| Supply split | VR_ANA1 pad metal feeds VCO CT, LO, CP star from pad node; LDO output before 10 Ω stays local; VR_DIG only into AFE/phase1l; analog gnd star under VCO |
| Coupling target | Best of the three: max inductor–digital distance; CP switching east of bank shield; LO CMOS edges south, not under coil |
| Post-layout noise | Short tank–buffer helps Amp and kick-back; local CT/CML caps easy; LF large MOS away from coil reduces C2 modulation from digital |

**Pros:** Best isolation for −35/−15 dBc coupling; natural VR_ANA1 adjacency; RF path points to RF pads.  
**Cons:** Synth island spans NW–NE; V_tune crosses bank–LF gap; die may need a tall N strip.

---

## 4. Option B — “Inductor north-centre; synth east of digital”

**Placement:** L2n0 **north-centre**. VCO south of the coil. LO chain continues south-west toward RF. PLL / LF / LDO form a **column on the east**, between phase1l (SE) and the VCO. Pin 3 VR_ANA1 routes north then east into LDO → 10 Ω → pad spur into the east column and west into VCO CT.

| Metric | Estimate `[HAND]` |
|---|---|
| Synth island area / aspect | ≈ 0.48 mm²; ~600 × 800 µm |
| VCO→buffer→CML path | ≈ 100–180 µm |
| V_tune line | ≈ 80–150 µm (LF next to VCO east face) |
| Inductor ↔ digital | ≈ 400–600 µm |
| Inductor ↔ charge pump | ≈ 200–350 µm |
| Guard / DNW | Same idea; CP closer to coil than Option A |
| Supply split | Longer VR_ANA1 spine N→E; more IR and bond-return sharing risk at GHz unless local caps are dense |
| Coupling target | Weaker than A: CP nearer coil; digital still south but closer |
| Post-layout noise | Shorter V_tune helps hold/monitor; LO path slightly longer |

**Pros:** Compact; short V_tune; clear east “PLL street”.  
**Cons:** Worse inductor–CP spacing; VR_ANA1 routing longer; coupling margin tighter.

---

## 5. Option C — “Compact cluster at pin 3 (rejected as primary)”

**Placement:** Entire synth (inductor + VCO + LO + PLL + LF + LDO) packed in the **NW** within ~500 × 500 µm; digital SE.

| Metric | Estimate `[HAND]` |
|---|---|
| Synth island area / aspect | ≈ 0.45 mm²; ~500 × 500 µm |
| VCO→buffer→CML | ≈ 50–100 µm (best) |
| V_tune | ≈ 50–100 µm (best) |
| Inductor ↔ digital | ≈ 600–900 µm (good) |
| Inductor ↔ charge pump | ≈ 100–200 µm (**poor**) |
| Coupling / noise | Fails the spirit of the −35 dBc VHF layout target: CP and Σ-Δ edges sit under or beside the coil |

**Pros:** Shortest RF and V_tune; smallest bounding box.  
**Cons:** Couples CP / digital edges into the tank; hard to meet integer-boundary isolation without exotic shielding. **Not proposed.**

---

## 6. Proposal — **D23: Option A**

Adopt **Option A** (inductor NW near VR_ANA1; VCO east of coil; LO south; PLL/LF NE; phase1l SE; AFE digital on PLL east face).

**Reasons:**
1. Maximises inductor–digital distance while keeping pin-3 adjacency for D21.
2. Keeps the charge pump and large C2 MOS off the coil — needed for the VHF raw ≤ −35 dBc coupling budget (`pll-topology` §13).
3. LO path points toward RF pads for Phase 3 mixer without crossing the digital core.
4. Area (~0.50 mm²) and routing lengths are acceptable `[HAND]`; Option B saves little area and spends isolation.

**Not decided here:** exact die outline, pad-ring abuts, or Phase 3 RX/TX placement (they follow the Phase 2 gate).

---

## 7. Owner decision

**D23 = Option A** recorded in `decisions.md` (2026-11-11). Layout proceeds under P2.7.1+.

---

## 8. Whole-die area tally vs package `[HAND]`

Rough Phase-5 squeeze check against the SX1255-compatible **MLPQ-W 5 × 5 mm** package (`spec/rf-frontend.md` §2). Package outline = **25 mm²**; usable silicon is smaller. Two die-core assumptions: the memo’s ~**1.6 × 1.6 mm** (2.56 mm²) sketch, and a more typical **~2.5 × 2.5 mm** (6.25 mm²) die inside a 5 × 5 MLPQ.

| Block | Area (mm²) | Basis |
|---|---|---|
| VCO island (L2n0 + VCO analogue) | **≤ 0.30** | D23 amended 2026-11-12; compact 0.22–0.28 `[HAND]` / P2.7.2a |
| Rest of synthesizer (LO+PLL+LF+LDO+AFE dig) | **≈ 0.28–0.32** | §2 remainder `[HAND]` |
| Synthesizer island total (D23 Option A) | **≈ 0.55–0.62** | was ≈ 0.50; VCO raise `[HAND]` |
| Digital back end (`phase1l`) | **0.340** | 339 617 µm² `[SCH]` |
| RX (LNA + mixer + TIA/AAF + Σ-Δ ADC) | **0.90** | rf-frontend §7 first-cut; SX1255-class `[HAND]` |
| TX (Σ-Δ DAC + recon filter + IQ mod + PA driver) | **0.65** | same `[HAND]` |
| LDOs (VR_PA, VR_ANA1, VR_ANA2, VR_DIG) + local C | **0.10** | VR_ANA1 alone ≈ 0.02–0.03; four rails `[HAND]` |
| Pad ring / ESD / seal (32 leads) | **0.55** | typical MLPQ pad + ESD strip `[HAND]` |
| **Sum (no routing slack)** | **≈ 3.16–3.23** | |
| Routing / guard / fill / DNW slack (~15 %) | **≈ 0.47** | `[HAND]` |
| **Total estimate** | **≈ 3.6–3.7** | |

| Against | Available | Fit? |
|---|---|---|
| Memo core 1.6 × 1.6 mm = 2.56 mm² | 2.56 | **NO — short ≈ 1.1 mm²** `[HAND]` |
| Typical die 2.5 × 2.5 mm = 6.25 mm² | 6.25 | **YES — ~2.5–2.6 mm² slack** `[HAND]` |
| Package outline 5 × 5 mm = 25 mm² | (die ≪ package) | Package is not the limit; die outline is |

**P2.7.2a2 check:** VCO island ≤ 0.30 mm² (D23 amended) still fits inside ≈ 2.5 × 2.5 mm with pad ring. Die-size squeeze remains RX+TX+pads, not the VCO raise. Exact die size remains a Phase 5 decision.

**Flag:** the §1 sketch of a **1.6 × 1.6 mm** active core **does not fit** the Phase 3/4 RX+TX + synth + digital + pads tally. Before Phase 5, plan on a die closer to **≥ ~2.2 × 2.2 mm** (≈ 4.8 mm²) or tighten RX/TX area after topology.
