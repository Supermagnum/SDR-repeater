import os
from pathlib import Path

from cocotb_tools.runner import get_runner


def main():
    root = Path(__file__).resolve().parents[1] / "digital"
    sources = [
        root / "spi_regs.sv",
        root / "rate_table.sv",
        root / "cic4.sv",
        root / "fir_mac.sv",
        root / "decim_chain.sv",
        root / "dc_offset.sv",
        root / "iq_cal.sv",
        root / "power_ctrl.sv",
        root / "i2s_master.sv",
        root / "sample_fifo.sv",
        root / "i2s_slave.sv",
        root / "digital_backend.sv",
    ]
    runner = get_runner("icarus")
    runner.build(
        sources=sources,
        hdl_toplevel="digital_backend",
        build_dir=Path(__file__).resolve().parent / "sim_build",
        always=True,
    )
    if os.environ.get("ONLY"):
        os.environ["COCOTB_TEST_FILTER"] = os.environ["ONLY"]
    runner.test(
        hdl_toplevel="digital_backend",
        test_module="test_backend",
        build_dir=Path(__file__).resolve().parent / "sim_build",
    )


if __name__ == "__main__":
    os.environ.setdefault("COCOTB_REDUCED_LOG_FMT", "1")
    main()
