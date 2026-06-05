# ADR 001: IQ transport — I2S on VITA 46, ZeroMQ on K3

**Status:** Accepted  
**Date:** May 2026  

## Context

The system overview mentions **PCIe Gen 3** on the module data bus. The RF module specification defines **I2S** IQ streams on the VITA 46 J0 utility plane at 500 kSa/s per band. Implementers need one clear production path.

## Decision

1. **Production IQ path:** RFIC -> **I2S** (per module SAI on K3) -> kernel DMA ring buffer -> **`ht-module-daemon`** (Rust) -> **ZeroMQ** `ipc:///run/ht-module/iq_*` and `tx_*`.
2. **J1 PCIe / GbE** on the module edgecard is **reserved** for future wideband variants; it is **not** used for the baseline 500 kHz repeater IQ plane.
3. **Backplane "data fabric"** PCIe/Ethernet between slots serves **chassis management, expansion, or switching** — not replacement of per-module I2S IQ into the compute slot.
4. **Consumers** (GNU Radio, SDRangel, recorders) attach only to ZMQ endpoints documented in [zeromq-messages.md](../zeromq-messages.md).

## Consequences

- Driver work focuses on **SAI/DMA**, not PCIe endpoint drivers for IQ.
- README module interface text should be read together with this ADR when planning firmware.
- Remote IQ monitoring uses ZMQ `tcp://` binding with **unchanged** frame layout (see zeromq-messages Section 2.2).
- Bench testing may use ALSA `hw:N` mapping per RF-modules Section 9.1; production bypasses ALSA for IQ.

## Alternatives considered

| Alternative | Rejected because |
|-------------|------------------|
| PCIe DMA IQ from each module | Overkill for 500 kHz x 3 bands; PCB and driver complexity |
| Raw Ethernet IQ per module | Same; reserved for J1 future profile |
| ALSA only in production | Extra latency and format ambiguity vs framed ZMQ |

## References

- [RF-modules.md](../RF-modules.md) Sections 9.1, 10
- [zeromq-messages.md](../zeromq-messages.md) Sections 2–3
