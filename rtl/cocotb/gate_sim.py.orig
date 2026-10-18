import os
from pathlib import Path

from cocotb_tools.runner import get_runner


def main():
    root = Path(__file__).resolve().parents[1] / "digital"
    nl = root / "runs" / "phase1c" / "06-yosys-synthesis" / "digital_backend.nl.v"
    pdk = Path("/foss/pdks/ihp-sg13g2/libs.ref/sg13g2_stdcell/verilog")
    ts = root / "runs" / "phase1c" / "timescale.v"
    ts.write_text("`timescale 1ns/1ps\n")
    sources = [ts, pdk / "sg13g2_udp.v", pdk / "sg13g2_stdcell.v", nl]
    test_module = "test_backend"
    waves = False
    mode = os.environ.get("PWR_MODE")
    if mode:
        test_module = "test_power"
        os.environ["COCOTB_TEST_FILTER"] = "power_mode"
        waves = True
    runner = get_runner("icarus")
    build = Path(__file__).resolve().parent / "sim_build" / "gate"
    runner.build(
        sources=sources,
        hdl_toplevel="digital_backend",
        build_dir=build,
        always=True,
        waves=waves,
    )
    if os.environ.get("ONLY"):
        os.environ["COCOTB_TEST_FILTER"] = os.environ["ONLY"]
    runner.test(
        hdl_toplevel="digital_backend",
        test_module=test_module,
        build_dir=build,
        waves=waves,
    )


if __name__ == "__main__":
    os.environ.setdefault("COCOTB_REDUCED_LOG_FMT", "1")
    main()
