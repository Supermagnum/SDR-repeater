import os
from pathlib import Path

from cocotb_tools.runner import get_runner


def main():
    root = Path(__file__).resolve().parents[1] / "digital"
    sources = [
        root / "spi_regs.sv",
        root / "decim_iq.sv",
        root / "dc_offset.sv",
        root / "iq_cal.sv",
        root / "power_ctrl.sv",
        root / "i2s_port.sv",
        root / "digital_backend.sv",
    ]
    runner = get_runner("icarus")
    runner.build(
        sources=sources,
        hdl_toplevel="digital_backend",
        build_dir=Path(__file__).resolve().parent / "sim_build",
        always=True,
    )
    runner.test(
        hdl_toplevel="digital_backend",
        test_module="test_backend",
        build_dir=Path(__file__).resolve().parent / "sim_build",
    )


if __name__ == "__main__":
    os.environ.setdefault("COCOTB_REDUCED_LOG_FMT", "1")
    main()
