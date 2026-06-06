# ADR 001: IQ transport — I2S on DIN 41612, ZeroMQ on K3

**Status:** Accepted  
**Date:** June 2026  
**Supersedes:** May 2026 revision (VITA 46 / OpenVPX context)

## Context

The system overview (README v1.5) and RF module specification define **I2S** IQ streams over the **DIN 41612** Eurocard backplane connector, with a maximum of **1 MHz IQ bandwidth** per band (25 / 50 / 100 / 200 / 500 kHz / 1 MHz selectable via SPI). At 1 MHz IQ, the I2S bit clock is 32 MHz (1 MHz × 2 channels × 16 bits) — well within DIN 41612 signal contact capability. Implementers need one clear production path.

Earlier drafts referenced VITA 46 J0/J1 utility and data planes and optional backplane PCIe/GbE. The architecture now uses a single **96-pin DIN 41612 Type C** signal connector plus **har-bus 64** power contacts per slot. No separate high-speed data-plane connector is populated or planned.

## Decision

1. **Production IQ path:** RFIC -> **I2S** (per module SAI on K3) -> kernel DMA ring buffer -> **`ht-module-daemon`** (Rust) -> **ZeroMQ** `ipc:///run/ht-module/iq_*` and `tx_*`.
2. **Backplane interconnect:** All module IQ, SPI configuration, I²C management, and GPIO control signals are carried on **DIN 41612 signal contacts**. The +12 V PA rail uses **har-bus 64** high-current contacts. No backplane PCIe, GbE, or high-speed differential fabric is used for module IQ.
3. **Bandwidth headroom:** The DIN 41612 connector is sized for the actual signal requirements of this repeater (I2S up to 32 MHz bit clock, SPI at 10 MHz, I²C at 100 kHz). A separate data-plane connector is not required.
4. **Consumers** (GNU Radio, SDRangel, recorders) attach only to ZMQ endpoints documented in [zeromq-messages.md](../zeromq-messages.md).

## Consequences

- Driver work focuses on **SAI/DMA**, not PCIe endpoint drivers for IQ.
- README module interface text should be read together with this ADR when planning firmware.
- Remote IQ monitoring uses ZMQ `tcp://` binding with **unchanged** frame layout (see zeromq-messages Section 2.2).
- Bench testing may use ALSA `hw:N` mapping per RF-modules Section 9.2; production bypasses ALSA for IQ.
- Module PCB layout must follow mandatory via-fence and thermal ground-pour rules in RF-modules Sections 8.3 and 8.5.

## Alternatives considered

| Alternative | Rejected because |
|-------------|------------------|
| PCIe DMA IQ from each module | Overkill for up to 1 MHz × 4 bands; PCB and driver complexity; no PCIe on module backplane |
| Raw Ethernet IQ per module | Same; not planned on DIN 41612 architecture |
| Backplane GbE / PCIe fabric between slots | Not required for repeater IQ; compute module uses on-board GbE/PCIe for storage and network only |
| ALSA only in production | Extra latency and format ambiguity vs framed ZMQ |
| VITA 46 / OpenVPX backplane | Higher chassis cost; multi-gigabit connector capability unused at these signal rates |

## References

- [RF-modules.md](../RF-modules.md) Sections 9.2, 10
- [zeromq-messages.md](../zeromq-messages.md) Sections 2–3
- [README.md](../../README.md) Sections 2, 3, 7.5 (revision 1.5)
