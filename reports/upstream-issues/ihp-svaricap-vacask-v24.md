# Draft upstream issue — do not post without owner review

**Target:** IHP-GmbH/IHP-Open-PDK (and optionally iic-jku/IIC-OSIC-TOOLS / VACASK converter).

**Suggested title:** `sg13_hv_svaricap` well resistance uses `v(2,4)` with zero coefficients; VACASK conversion does not elaborate

## Body (paste-ready)

### Describe the bug

The ngspice wrapper for `sg13_hv_svaricap` (`ihp-sg13g2/libs.tech/ngspice/models/sg13g2_svaricaphv_mod.lib`) defines the well resistor as:

```spice
rww   W  W0 r = '((((rwell0+(rwellvw*(v(2, 4))))+((rwellw+(rwellwvw*(v(2, 4))))*w))+(((rwellnx+(rwellnxvw*(v(2, 4))))*w)/(Nx*Ny)))*Nx)*Ny'
```

with

```spice
.params rwellvw    = 0
.params rwellwvw   = 0
.params rwellnxvw  = 0
```

The VACASK conversion shipped in `hpretl/iic-osic-tools` (header: “Converted from IHP SG13G2 PDK for Ngspice”, via `vacask.sg13g2tovc`) keeps the same expression as `v(2,4)`. VACASK does not elaborate that form, so any circuit that instantiates `sg13_hv_svaricap` fails to build under VACASK unless the zero-coefficient `v(2,4)` terms are removed locally.

Because the voltage coefficients are already 0, dropping those terms does not change the intended model value. A local workaround replaces `(rwellvw*(v(2,4)))` (and the two siblings) with `0` and renames the subckt.

### To Reproduce

1. Use IHP SG13G2 PDK commit `a49358cc` (or the same models in current `dev` ngspice tree) inside `hpretl/iic-osic-tools:2026.10`.
2. Convert / load `libs.tech/vacask/models/sg13g2_svaricaphv_mod.lib`.
3. Instantiate `sg13_hv_svaricap` in a VACASK netlist and run any analysis.
4. Observe that elaboration fails on the well-resistance expression containing `v(2,4)`.

### Expected behavior

Either:

- the ngspice wrapper omits the dead `v(2,*)` terms when the coefficients are 0, so the VACASK converter emits a legal expression; or
- the VACASK / IIC converter drops zero-coefficient `v(...)` products; or
- VACASK documents and supports this `v(node1,node2)` form in resistor expressions.

### Environment

- PDK: IHP-Open-PDK `a49358cc0b20635fcb53c0940505e3563763fc7a`
- Container: `hpretl/iic-osic-tools:2026.10`
- VACASK: `fb8cc20`
- OpenVAF-Reloaded: OSDI 0.5 (`osdi_0.5_20260820-26-gdd05b5e-dirty`)

### Additional context

Related closed issue [#1098](https://github.com/IHP-GmbH/IHP-Open-PDK/issues/1098) fixed the `dsubw` `vj` for high-temperature ngspice transients (PR #1102). That fix is present in `a49358cc` (`vj=0.3357`). This report is only about the VACASK elaboration of the well resistor expression, not about `dsubw`.

We are not posting this from an automated agent; the project owner will submit if accepted.

---

## Notes for the owner

- File against **IHP-Open-PDK** first (source model). Optionally CC or file a second issue on **IIC-OSIC-TOOLS** pointing at `vacask/sg13g2tovc.py` if IHP asks for a converter-side fix.
- Do not change the local `_fx` workaround until an upstream fix is in a PDK/container pin you accept.
