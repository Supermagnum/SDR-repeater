# Integer-boundary spur map

Source: [HAND], 2026-10-17. No circuit was simulated. LinHT facts in the surrounding baseline are provisional because Rev C is not validated.

## LO arithmetic used

Baseline LO from the design prompt, not from `docs/RF-modules.md` r0.3 (that document still describes direct VCOs at the RF frequency).

- UHF 430-440 MHz is the VCO divided by 8, so the VCO is 3440-3520 MHz.
- VHF 144-146 MHz is the VCO divided by 24, so the VCO is 3456-3504 MHz.
- An integer-boundary spur sits at offset `|f_VCO - k * f_ref|` from the carrier. Division does not change that offset in hertz. A carrier `delta` away from the RF frequency that corresponds to `k * f_ref` sees the spur at offset `N * delta`, with `N = 8` on 70 cm and `N = 24` on 2 m.

## 32 MHz reference

`k * 32 MHz` inside 3440-3520 MHz:

| k | VCO (MHz) | 70 cm (MHz) | 2 m (MHz) |
|---|---|---|---|
| 108 | 3456 | 432.000 | 144.000 |
| 109 | 3488 | 436.000 | 145.333333 |
| 110 | 3520 | 440.000 | 146.666667, outside 144-146 |

At the top of 2 m the VCO is 3504 MHz, 16 MHz below k = 110. The spur offset there is 16 MHz.

## 36 MHz reference

`k * 36 MHz` inside 3440-3520 MHz:

| k | VCO (MHz) | 70 cm (MHz) | 2 m (MHz) |
|---|---|---|---|
| 96 | 3456 | 432.000 | 144.000 |
| 97 | 3492 | 436.500 | 145.500 |

3456 MHz is an integer multiple of both 32 MHz and 36 MHz. 432.000 MHz and 144.000 MHz are integer-boundary channels for both references.

## What this does not say

Spur level is not estimated here. Whether a fractional-N modulator, a reference doubler, or an integer-N PLL is used changes the level and is not chosen yet.
