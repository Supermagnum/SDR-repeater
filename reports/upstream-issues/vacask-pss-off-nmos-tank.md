# Draft upstream issue — do not post without owner review

**Target:** codeberg.org/arpadbuermen/VACASK (optionally note in iic-jku/IIC-OSIC-TOOLS if they ship the pin).

**Suggested title:** PSS fails to converge with an off LV NMOS across a bias resistor on an LC-tank bottom plate

## Body (paste-ready)

### Describe the bug

Periodic steady-state (PSS) analysis of a cross-coupled LC oscillator aborts when an **off** `sg13_lv_nmos` (V_GS = 0) is placed across a high-value bias resistor tied to a switched MIM bottom plate on the tank. The same netlist without that MOSFET converges. Other off NMOS devices on the same design (tail bias filter, AC-coupled varactor bias) do **not** break PSS.

VACASK reports:

```
PSS failed to converge in 50 iterations.
PSS analysis failed.
Analysis 'pn' aborted.
```

A warm transient (`tran` → `store="ss"`) completes; the failure is in the subsequent `pnoise` / PSS shooting step.

### To Reproduce

Environment: IHP SG13G2 PDK commit `a49358cc`, container `hpretl/iic-osic-tools:2026.10`, VACASK `fb8cc20`.

Smallest case found (full P2.3 VCO, tt 27 °C, ~4.20 GHz, code 20):

1. Cross-coupled LC VCO as usual (L2n0 lumped tank, LV NMOS pair, MOS tail, 8-bit bank, varactor, stand-in buffer).
2. Off bypass under test: `sg13_lv_nmos w=5u l=0.13u ng=2`, V_GS=0, across the 2 MΩ bank-plate bias R.
3. **k=1** (one bit, two fingers): PSS **OK**. **k=2** (bits 0–1, four fingers): PSS **FAIL**.
4. `tran` 60 ns → `store="ss"` → `pnoise oscillator=1`, `tper≈238 ps`, `reltol=1e-6`, `pss_tolscale=1e-3`, `pss_minpts=8000`.

VACASK text at k=2:

```
PSS failed to converge in 50 iterations.
PSS analysis failed.
Analysis 'pn' aborted.
```

Scripts / archives in this repo (attach when posting):

- `analog/vco/step3/repro_pss_bank_bypass.py`
- `analog/vco/step3/out/summary_repro_pss_bank_bypass.txt`
- `analog/vco/step3/out/repro_pss/repro_{nobypass,bypass,k2}.{sim,log}`
- Full-VCO isolation: bank-group only fails; tail/varactor bypass groups pass (`summary_pss_bypass_parts.txt`).

### Expected behavior

PSS should converge for an off MOSFET whose terminals sit on a weakly biased tank-side node (or document a modelling / analysis limitation and a recommended workaround). Linear R/C stand-ins for the off device also failed PSS in our trials, so this may not be only a PSP off-state artefact.

### Environment

- VACASK: `fb8cc20`
- Container: `hpretl/iic-osic-tools:2026.10`
- PDK: IHP-Open-PDK `a49358cc0b20635fcb53c0940505e3563763fc7a`
- Device: `sg13_lv_nmos` (PSP), `w=5u l=0.13u ng=2`

### Workarounds used locally

- Omit bank bypass devices from schematic PSS / pnoise (keep tail and varactor bypasses).
- Bound off-switch shot noise vs bank bias resistor thermal noise from a separate DC I_leak extract (`[SCH]+[HAND]`).
- Post-layout VCO PN uses the bank-omitted extracted netlist plus that bound until PSS is fixed.

### Additional context

We are not posting this from an automated agent; the project owner will submit if accepted.

---

## Notes for the owner

- Prefer filing against **VACASK** (shooting / PSS). Mention IHP only if they ask for a device-model check.
- Attach `out/repro_pss/repro_bypass.sim` + `.log` and the nobypass pair when posting.
- Do not close local workarounds until a fixed VACASK is in an accepted container pin.
