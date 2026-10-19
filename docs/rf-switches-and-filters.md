# RF switches and harmonic filters by power level

Parts survey for the PA side of the SDR repeater and the LinHT, 130–175 MHz and 400–480 MHz. Status: **survey, 2026-10-19.** Candidates, not final choices. Referenced from `docs/RF-modules.md` §7.3 and `spec/rf-frontend.md` §8.

Source quality: **[DS]** read from the maker's datasheet; **[DIST]** from a distributor or catalogue listing only, datasheet not checked; **[NEWS]** from a press article.

## Power levels

| Level | Where | dBm | Line voltage / current in 50 Ω |
|---|---|---|---|
| 5 W | LinHT (GRF5604, up to 6 W Psat), standard repeater module | +37 | 22 V peak, 0.32 A rms |
| 20 W | Repeater module, maximum | +43 | 45 V peak, 0.63 A rms |
| 100 W | External amplifier after a module | +50 | 100 V peak, 1.4 A rms |

Inside an LC filter and at SWR 3 (the module's cut-off), voltages and currents can reach about 1.5–2 × these values. Parts rated exactly at the level have no margin; aim for ≥ 2 dB.

---

## 1. 5 W — LinHT and standard modules

### Switches (T/R and band-path after the PA)

| Part | Type | Range | Power | Supply / control | Size | Notes |
|---|---|---|---|---|---|---|
| **Skyworks SKY13330-397LF** | SPDT | 0.1–6 GHz | P0.1dB +38.5 dBm (7 W); abs. max +40 dBm (10 W) **[DS]** | VBATT 2.3–4.8 V; control high 1.65–2.70 V, so **1.8 V GPIO works** **[DS]** | QFN 2 × 2 mm | Already the T/R switch on the LinHT. Insertion loss ≈ 0.3–0.35 dB, isolation ≈ 40–42 dB below 1 GHz. Only 1.5 dB from P0.1dB at 5 W: fine for 5 W, not for 6 W Psat. A second one can be the PA-side band switch |
| **pSemi PE42820** | SOI SPDT | 30 MHz–2.7 GHz | +43 dBm CW (20 W) **[DS]** | VDD 2.3–5.5 V; control high from 1.17 V **[DS]** | QFN 5 × 5 mm | 6 dB margin at 5 W; 0.30 dB loss, 35 dB isolation (30 MHz–1 GHz). Larger than the SKY13330 for a handheld |
| Mini-Circuits VSW2-33-10W+ | SPDT | 50 MHz–3 GHz | 10 W at +5 V control, 7 W at +3 V **[DS]** | Control high **2.8–5.2 V** — not from 1.8 V GPIO without a level shifter | 3 × 2 mm | 0.4 dB loss; isolation 42 dB at 50 MHz, 31 dB at 500 MHz |
| pSemi PE4259 | SOI SPDT | 10 MHz–3 GHz | +34.5 dBm max at 150–450 MHz **[DS]** | 1.8–3.3 V; control high 0.7 × VDD | SC-70-6 | **Low-power side only** (RFIC output, RX path) — not after the PA |

**Not suitable:** the **SKY13351-378LF** (P1dB ≈ +30 dBm, 1 W **[DIST]**), listed as the T/R switch up to `RF-modules.md` r0.4; replaced in r0.4.1.

### Harmonic filters

| Part | Type | Passband | Rejection | Power | Notes |
|---|---|---|---|---|---|
| **Mini-Circuits LFCN-490+** | LTCC low-pass | DC–490 MHz | 20 dB at 800 MHz **[DIST]** | < 8.5 W **[DIST]** | UHF filter already on the LinHT |
| Mini-Circuits LFCN-160+ | LTCC low-pass, 1206 | DC–160 MHz (3 dB at 230 MHz) | Typ. 5.9 dB at 260 MHz, 10.6 at 280, 21.7 at 310; ≥ 20 dB 330–480 MHz **[DS]** | 8 W at 25 °C → 3 W at 100 °C **[DS]** | 2 m 2nd harmonic (288–296 MHz) only ≈ 12–18 dB: **not enough alone**. 175 MHz is outside its passband |
| Mini-Circuits LFCN-180+ | LTCC low-pass, 1206 | DC–180 MHz (3 dB at 270 MHz) | 7.5 dB at 300 MHz; ≥ 20 dB 370–525 MHz **[DS]** | 8 W at 25 °C → 3 W at 100 °C **[DS]** | 2nd harmonic of 2 m barely touched. Not suitable as the only filter |
| Mini-Circuits LFCG-180+ | LTCC low-pass, 0805 | DC–180 MHz | ≥ 20 dB 380–800 MHz **[DS]** | 3.5 W at 25 °C **[DS]** | Too little power for 5 W |
| **Discrete LC (chosen for VHF)** | 7th-order elliptic-type low-pass, 3 traps | 130–175 MHz | ≥ 70 dB from 256 MHz (design below) | Set by the parts | Same values at 5, 20 and 100 W; only the part ratings change. This is what commercial dual-band handhelds do |

Notes for the VHF filter:
- **Full 130–175 MHz coverage (decided):** the 2nd harmonic of 130 MHz is 260 MHz, only 1.49 × the top of the band, so the filter is elliptic with notches — see the design below.
- The LTCC parts can be a second stage after a discrete filter, or be cascaded, but alone they do not reach the regulatory 2nd-harmonic level.

### VHF harmonic filter, 130–175 MHz (decided 2026-10-19)

Full 130–175 MHz coverage (owner decision). A 7th-order elliptic-type ladder with three traps reaches it with only three inductors:

```
IN ──┬── L2 ∥ C2 ──┬── L4 ∥ C4 ──┬── L6 ∥ C6 ──┬── OUT
     C1             C3             C5             C7
     ⏚              ⏚              ⏚              ⏚
```

| Part | C1 | L2 ∥ C2 | C3 | L4 ∥ C4 | C5 | L6 ∥ C6 | C7 |
|---|---|---|---|---|---|---|---|
| Value | 33 pF | 36 nH ∥ 2.7 pF | 75 pF | 22 nH ∥ 12 pF | 68 pF | 24.5 nH ∥ 15 pF | 27 pF |
| Trap frequency | — | 511 MHz | — | 309 MHz | — | 263 MHz | — |

Computed with `tools/vhf_lpf_check.py` (ideal parts plus finite Q; no layout parasitics):

| Item | Result |
|---|---|
| Passband loss, lossless | ≤ 0.10 dB, 130–175 MHz |
| Passband loss, inductor Q 100, capacitor Q 500 | 0.37 dB at 130 MHz, 0.44 at 145, 0.57 at 160, 0.94 at 175 MHz |
| Rejection 256–1200 MHz | ≥ 70.6 dB (2nd harmonic of 130 MHz and up) |
| ±2 % parts, 300-run Monte Carlo | passband ≤ 0.39 dB, rejection ≥ 65.4 dB (99 % of runs) |
| Below 128 MHz | not specified (up to about 3 dB loss near 60 MHz) — the filter is only used inside 130–175 MHz |

Worst-case part stress over 130–175 MHz (from the script; current and voltage scale with √P: × 0.447 at 20 W, × 0.224 at 5 W):

| Part | 100 W matched | 100 W, SWR 3 | 20 W, SWR 3 | 5 W, SWR 3 |
|---|---|---|---|---|
| C3 75 pF / C5 68 pF | 74 V, 5.6 A | 109 V, 8.9 A | 49 V, 4.0 A | 24 V, 2.0 A |
| L4 22 nH | 131 V, 5.4 A | 202 V, 8.4 A | 90 V, 3.7 A | 45 V, 1.9 A |
| L6 24.5 nH | 121 V, 4.5 A | 170 V, 6.3 A | 76 V, 2.8 A | 38 V, 1.4 A |
| L2 36 nH | 116 V, 2.9 A | 184 V, 4.7 A | 82 V, 2.1 A | 41 V, 1.0 A |
| C1 / C7 | 78 V, 2.7 A | 111 V, 3.9 A | 50 V, 1.7 A | 25 V, 0.9 A |
| Trap capacitors | 131 V, 2.0 A | 202 V, 2.8 A | 90 V, 1.3 A | 45 V, 0.6 A |

Part choices by power level:

- **5 W (LinHT, standard module):** high-Q C0G capacitors, 0603 or larger, ≥ 100 V, rated ≥ 2 A RF at 150 MHz; air-core or high-current wire-wound inductors ≥ 2 A. Check each part's RF current rating.
- **20 W:** porcelain capacitors (ATC 100B, 500 WVDC); air-core inductors rated ≥ 4 A. The Coilcraft Maxi Spring series starts at 90 nH, so the 22–36 nH coils are a smaller air-core series or hand-wound.
- **100 W (external amplifier):** voltages are well inside the 100B limit (354 V rms at 500 WVDC; worst case 202 V rms on a trap capacitor). Dissipation, from the 100B datasheet ESR chart at 150 MHz (typical: about 0.03 Ω at 27–33 pF, 0.04 Ω at 12–15 pF and at 56–75 pF, 0.07 Ω at 2.7 pF) **[DS]** and the 3 W limit (65 °C mounting surface, 20 °C/W):

  | Position | 100 W, SWR 3 | 100 W matched | 20 W, SWR 3 |
  |---|---|---|---|
  | C3 75 pF | 8.85 A → **3.0 W (at the limit)** | 5.5 A → 1.1 W | 4.0 A → 0.6 W |
  | C5 68 pF | 8.18 A → **2.5 W (85 % of limit)** | 5.6 A → 1.2 W | 3.7 A → 0.5 W |
  | C1 33 pF, C7 27 pF | ≤ 3.9 A → ≤ 0.44 W | — | ≤ 0.1 W |
  | Traps 12 / 15 / 2.7 pF | ≤ 2.8 A → ≤ 0.31 W | — | ≤ 0.06 W |

  So a single 100B is fine at every position at 5 W and 20 W, and at 100 W everywhere except **C3 and C5: fit two 100B in parallel there** (e.g. 2 × 39 pF and 2 × 33 pF; each then dissipates about 0.75 W at SWR 3), or a 100C. ESR rises somewhat towards 175 MHz, which is why one part at C3 is not enough. Inductors: heavy-wire air-core coils rated ≥ 9 A, or lower the SWR cut-off from 3 to 2 at 100 W.
- **Loss and heat:** at 1 dB loss, a 100 W filter dissipates about 20 W, mostly in the inductors. Inductor Q above 200 at 175 MHz halves that.

### Dual-band LinHT, PA side

GRF5604 → SKY13330 (or PE42820) band switch → VHF discrete LPF or LFCN-490+ → second switch → T/R switch (SKY13330) → antenna. Switches controlled from i.MX93 GPIO at 1.8 V. The LinHT PCB has none of this today; it is UHF only.

---

## 2. 20 W — repeater module maximum

| Part | Type | Range | Power | Supply / control | Notes |
|---|---|---|---|---|---|
| **pSemi PE42820** | SOI SPDT | 30 MHz–2.7 GHz | +43 dBm CW (20 W); abs. max +45.5 dBm **[DS]** | Single 2.3–5.5 V; logic high from 1.17 V **[DS]** | Works from the existing backplane rails and 1.8 V GPIO. **No margin at 20 W** — check dissipation at SWR 3 |
| Skyworks SKY12208-306LF | PIN SPDT | 20 MHz–2.7 GHz | 50 W **[NEWS]** | PIN bias (not checked) | Margin at 20 W |
| Menlo Micro MM5230 | MEMS | — | 25 W CW, 150 W pulsed **[NEWS]** | — | Frequency range not checked |

Filters: discrete LC as in section 3, with ≥ 100 V capacitors and ≥ 2 A inductors (already in `RF-modules.md` §7.3).

---

## 3. 100 W — external amplifier

A 100 W PA does not fit on the Eurocard module: at about 40 % efficiency it draws about 250 W DC (≈ 21 A at 12 V) and dissipates about 150 W, against a slot budget of 72 W and a fan sized for 15 W average. 100 W means a separate amplifier unit after a 5 W or 20 W module, with its own switch or diplexer and filter.

### Switches (≥ +52 dBm wanted for margin)

| Part | Type | Range | Power | Supply / control | Notes |
|---|---|---|---|---|---|
| MACOM MSW2030-203 | PIN SPDT | 20 MHz–1 GHz | 100 W CW (+50 dBm) **[DS]** | 5 V **and 28–125 V**; ≈ 100 mA series / 25 mA shunt forward current; MADR-010574 driver; 4 control lines **[DS]** | 8 × 5 × 2.5 mm. No margin at 100 W |
| **MACOM MSW2040-204** | PIN SPDT, **symmetrical** (either throw takes full power) | 50 MHz–1 GHz | +52 dBm CW (+51 dBm abs. max at 85 °C) **[DS]** | 5 V and 28–125 V; ≈ 150 mA series / 25 mA shunt; MADR-010574 driver at 120 V **[DS]** | **Band-path switch for 100 W.** 0.2 dB loss, ≥ 47 dB isolation, IIP3 +65 dBm; 6 W total dissipation at 85 °C |
| **MACOM MSW2050-205** | PIN SPDT, asymmetrical | 50 MHz–1 GHz | TX/antenna +52 dBm, **RX throw +43 dBm** **[DS]** | 5 V and 28–125 V (up to 200 V reverse) **[DS]** | **T/R switch for 100 W** (RX throw never sees PA power) |
| MACOM MSW2022-202 | PIN SPDT | 50 MHz–1 GHz | +52 dBm **[DIST]** | Not checked | Alternative |
| MACOM MSW3100-310 | PIN SP3T | 50 MHz–1 GHz | +57 dBm **[DIST]** | High-voltage bias | Large margin |
| MACOM MASW-011030 | PIN SP3T | 30 MHz–3 GHz | 100 W CW at +85 °C base plate **[DIST]** | Not stated | 7 mm HQFN-16 |
| Microsemi MPS2R10-606 | SPDT | 100 MHz–1 GHz | 100 W CW **[NEWS]** | Analogue control voltage | 0.2 dB loss, 55 dB isolation at 500 MHz; check availability |
| Frontgrade SSHPS-0.020-0.520-400 | Switch module | 20–520 MHz | 400 W, all VSWR **[DS]** | +28 V at 0.5 A | Connectorised unit; 0.65 dB loss, 38 dB isolation |
| RFuW MSW2T-200501-150 | SPDT | 20–500 MHz | +56 dBm **[DIST]** | — | **Discontinued** |

No SOI or MEMS switch found for 100 W CW at VHF; they stop at about 20–25 W.

**PIN switches need a 28–125 V bias rail and a driver.** The backplane has no such rail, so the amplifier unit needs its own boost converter plus MADR-010574-type drivers.

**Reverse bias at VHF (MSW2040 / MSW2050 datasheets, 125 W CW, 1.5:1 VSWR) [DS]:** 125 V at 20 and 100 MHz, 85 V at 200 MHz, 55 V at 400 MHz, 28 V at 1 GHz. At 130–175 MHz plan for a **125 V** rail (the MADR-010574 application circuit uses 120 V); 70 cm alone would need about 55 V.

**Availability (2026-10-19):** MACOM lists the MSW2040-204 and MSW2050-205 for order and samples; RFMW lists them as "Standard", price on request, no stock shown. No lifecycle notice found. Get a quote before committing.

### Filters

- **LTCC surface-mount filters stop at about 10 W** (Mini-Circuits LFHK-1000+: 10 W at 25 °C, 1.5 W at 125 °C **[DS]**). Not usable at 100 W.
- **Discrete LC:**
  - Capacitors: Kyocera-AVX (ATC) **100B** porcelain, 0.1–1000 pF, mostly 500 WVDC, some to 1500 V **[DS]**; **100E** (0.38" case), 1–5100 pF, mostly 3600 WVDC **[DS]**. 100B current rating basis: 65 °C mounting surface, 20 °C/W, 3 W dissipation → 125 °C case **[DS]**; the A-rms values are only in the datasheet charts. Required ratings for the VHF filter are in the design section above.
  - Inductors: Coilcraft **Maxi Spring 132-xxSM** air-core, 90–538 nH, 2.0–3.5 A rms (15 °C rise), Q ≈ 104–114 at 50 MHz, SRF 490–1140 MHz **[DS]**. Suitable for 2 m; 70 cm needs smaller air-core coils (current not checked).
- **External dual-band diplexer:** example 2 m / 70 cm high-power diplexer, 750 W, 144–148 / 430–450 MHz, 0.04 / 0.07 dB loss, ≥ 75 dB isolation, 1 kg, €249 **[DIST]**. Each band still needs its own harmonic filter before it, because the 70 cm arm passes the 3rd harmonic of 2 m.

---

## Open checks

1. ~~MACOM reverse bias and availability~~ — done: 125 V at VHF; orderable, quote needed.
2. ~~100B ESR~~ — read from the datasheet chart (ATC # 001-807 Rev. S): two 100B in parallel at C3 and C5 for 100 W; single parts everywhere else and at 5–20 W.
3. SKY13330 at 6 W (GRF5604 Psat): only if the LinHT can drive the PA into saturation.
4. ~~VHF filter range~~ — full 130–175 MHz, design above.
5. Build and measure the VHF filter (layout parasitics shift the traps; tune C2, C4, C6).

## Sources

- Skyworks SKY13330-397LF datasheet: https://www.skyworksinc.com/-/media/SkyWorks/Documents/Products/601-700/SKY13330_397LF_201407E.pdf
- SKY13351-378LF listing: https://everythingrf.com/products/switches/skyworks/613-7-sky13351-378lf
- pSemi PE42820 datasheet: https://www.mouser.lt/datasheet/3/76/1/pe42820ds.pdf
- pSemi PE4259 datasheet, DOC-03694-5.01 (07/2026)
- Mini-Circuits VSW2-33-10W+: https://www.minicircuits.com/pdfs/VSW2-33-10W+.pdf
- Mini-Circuits LFCN-160+: https://www.minicircuits.com/pdfs/LFCN-160+.pdf
- Mini-Circuits LFCN-180+: https://www.minicircuits.com/pdfs/LFCN-180+.pdf
- Mini-Circuits LFCG-180+: https://www.minicircuits.com/pdfs/LFCG-180+.pdf
- LFCN-490+ listing: https://everythingrf.com/products/low-pass-filters/mini-circuits/525-12-lfcn-490
- Mini-Circuits LFHK-1000+: https://minicircuits.com/pdfs/LFHK-1000+.pdf
- MACOM MSW2030-203: https://www.macom.com/products/product-detail/MSW2030-203
- MACOM MSW203x datasheet: https://cdn.macom.com/datasheets/MSW203x-203.pdf
- MACOM MSW204x datasheet: https://shop.richardsonrfpd.com/docs/rfpd/msw204x-204.pdf
- MACOM MSW205x datasheet: https://www.mouser.com/datasheet/2/249/MSW205x_205-1921645.pdf
- MACOM MSW2040-204: https://www.macom.com/products/product-detail/MSW2040-204
- RFMW MSW2050-205: https://rfmw.com/products/detail/msw2050205-macom-metelics/403388/
- ATC 100B datasheet (ATC # 001-807 Rev. S, 8/18): https://shop.richardsonrfpd.com/docs/rfpd/100b.pdf
- MACOM MASW-011030: https://www.mouser.in/en/new/macom/macom-masw-011030-switch/
- RFMW high-power switch list: https://www.rfmw.com/userewavepreview.aspx?promo=305
- RFuW MSW2T-200501-150: https://rfmw.com/products/detail/msw2t200501150-rfuw/618057/
- Microsemi MPS2R10-606: https://www.eenewseurope.com/en/surface-mount-sp2t-switch-handles-100-w-of-continuous-power-from-100-mhz-to-1-ghz/
- Surface-mount PIN switches reach 100 W: https://www.electronicdesign.com/analog/surface-mount-pin-diode-switches-reach-100-w
- Frontgrade SSHPS-0.020-0.520-400: https://frontgrade.com/sites/default/files/documents/sshps_0.020-0.520-400.pdf
- Skyworks high-power SPDTs: https://microwavejournal.com/articles/18816-three-high-power-spdts
- Menlo Micro MM5230: https://menlomicro.com/newsroom/embedded-menlo-micro-releases-mm5230-high-power-rf-switch-into-production
- Kyocera-AVX 100B: https://rfs.kyocera-avx.com/product/1/100_b_series_porcelain_multilayer_capacitors_(mlcs)
- Kyocera-AVX 100E: https://rfs.kyocera-avx.com/Product/26/100_E_Series_Porcelain_Multilayer_High_RF_Power_Capacitors_(MLCs)
- Coilcraft Maxi Spring 132-xxSM: https://www.coilcraft.com/en-us/products/rf/air-core-inductors/maxi-spring/132-xxsm/
- 2 m / 70 cm high-power diplexer: https://antennas-amplifiers.com/2m-70cm-high-power-diplexer/
