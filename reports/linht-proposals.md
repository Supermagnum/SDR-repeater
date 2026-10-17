# LinHT notes for the human maintainer contact

Read-only check on 2026-10-17. Nothing in the LinHT or M17 repositories was cloned, forked, or modified. This file is a proposal for this project only.

## Hardware revision

- Public page https://linux-radio.eu/ : a test batch of Rev C boards is being tested. Rev C is the development revision on `main` and is not yet tagged as validated. Rev B was manufactured and tested.
- GitHub `M17-Project/LinHT-hw` release tag `revC` was published 2026-09-17. `main` commit `72336d64` is 2026-10-16, "Update README.md".
- An M17 project post dated 2026-10-16 says Rev C boards are ready for tests and that results are still pending. That agrees with the README statement that Rev C is not yet validated.
- SoM: CompuLab `MCM-iMX93-C1700D-D2-N32`.
- RF front-end: Semtech `SX1255IWLTRT`. PA: Guerrilla RF `GRF5604` (README: 100-600 MHz, about 4.5 W CW measured on Rev B). RX attenuators: two `PE4312C-Z`. T/R switch: `SKY13330-397LF`.
- Donor radio: Retevis C62 enclosure, battery, keypad, display, SMA, and audio jacks.
- VHF: the project states that current hardware is UHF only and that VHF is not a current priority. It also says VHF is not ruled out later.

## Supplies

- README: `BQ25792RQMR` is the USB-C charger for a 2S battery. `TPS565242DRLR` is the main 5 V, 5 A step-down converter. `ATtiny826-MU` sequences rails.
- Decision of 2026-10-17: the RFIC is specified against regulated host rails, not a raw cell. On LinHT that rail is the 5 V buck. The chip must tolerate buck ripple and regulator spurs. No ripple amplitude has been measured. Rev C is not validated, so this description stays provisional.
- Repeater side, from `docs/RF-modules.md` r0.3: backplane rails named +12 V (external PA), +5 V, +3.3 V, and +1.8 V.

## SX1255 interface

Source: Semtech SX1255 datasheet Rev 3.0, Digi-Key PDF, read 2026-10-17.

- Operating supply 2.7 V to 3.6 V on VBAT1, VBAT2, and VBAT3. VR_PA, VR_ANA1, VR_ANA2, and VR_DIG are regulated outputs.
- Reference used for the electrical tables: 36 MHz. CLK_OUT is a 36 MHz clock. Product frequency coverage on the Semtech page is 400-510 MHz.
- Control: SPI (SCK, MISO, MOSI, NSS).
- IQ: mode A is a 1-bit stream. Mode B is an I2S-like interface after on-chip decimation or interpolation. Mode B uses CLK_OUT and DIO2 as word select. The datasheet shows internal 32-bit I and Q buses before serialisation.
- The published schematic index names I2S0 as "RF baseband" and SPI0 as "SX1255 RF front-end". That is consistent with mode B, and it was not confirmed pin by pin from KiCad.
- Repeater baseline to reconcile later: 32 MHz reference, 16-bit I and Q, sample rate up to 500 kHz. The 500 kHz bandwidth matches the LinHT README. The word width and the 36 MHz versus 32 MHz clock do not match the SX1255 datasheet.

## USB-A security-dongle slot

Not designed. The current LinHT board, as described publicly, was not checked for a recessed right-angle USB-A receptacle. When this project draws a handheld reference schematic, that sheet must include a right-angle USB-A receptacle and a recessed slot for a Nitrokey-style token, with two or three connector part numbers taken from current manufacturer datasheets. USB data and the connector stay away from the RF section. No part number is listed here, because none has been checked against a datasheet yet.
