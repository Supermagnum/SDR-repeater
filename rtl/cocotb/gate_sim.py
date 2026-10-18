import os
from pathlib import Path

from cocotb_tools.runner import get_runner

# Port-level tests only: a gate netlist has no internal RTL signal names.
GATE_TESTS = "spi_reset_and_registers|master_frame_lengths|rx_chain_ports|i2s_slave_philips|spi_aborted_frame"


def main():
    root = Path(__file__).resolve().parents[1] / "digital"
    run = os.environ.get("RUN", "phase1i")
    nl = Path(os.environ["NETLIST"]) if os.environ.get("NETLIST") else \
        root / "runs" / run / "final" / "nl" / "digital_backend.nl.v"
    assert nl.exists(), f"netlist not found: {nl}"
    pdk = Path("/foss/pdks/ihp-sg13g2/libs.ref")
    cells = pdk / "sg13g2_stdcell" / "verilog"
    sram = pdk / "sg13g2_sram" / "verilog"
    ts = root / "runs" / run / "timescale.v"
    ts.write_text("`timescale 1ns/1ps\n")
    sources = [
        ts,
        cells / "sg13g2_udp.v",
        cells / "sg13g2_stdcell.v",
        sram / "RM_IHPSG13_1P_core_behavioral.v",
        sram / "RM_IHPSG13_1P_64x16_c2.v",
        nl,
    ]
    test_module = os.environ.get("TEST_MODULE", "test_backend")
    waves = False
    mode = os.environ.get("PWR_MODE")
    if mode:
        test_module = "test_power"
        os.environ["COCOTB_TEST_FILTER"] = "power_mode"
        waves = True
    else:
        os.environ["COCOTB_TEST_FILTER"] = os.environ.get("ONLY", GATE_TESTS)
    runner = get_runner("icarus")
    build = Path(__file__).resolve().parent / "sim_build" / "gate"
    runner.build(
        sources=sources,
        hdl_toplevel="digital_backend",
        build_dir=build,
        always=True,
        waves=waves,
    )
    runner.test(
        hdl_toplevel="digital_backend",
        test_module=test_module,
        build_dir=build,
        waves=waves,
    )


if __name__ == "__main__":
    os.environ.setdefault("COCOTB_REDUCED_LOG_FMT", "1")
    main()
