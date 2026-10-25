"""Run the MMD tests: python3 run_mmd.py (SIM=icarus by default)."""
import os
from pathlib import Path

from cocotb_tools.runner import get_runner


def main():
    here = Path(__file__).resolve().parent
    sim = os.environ.get("SIM", "icarus")
    runner = get_runner(sim)
    build = here / "sim_build" / f"mmd_{sim}"
    runner.build(sources=[here.parent / "mmd.sv"], hdl_toplevel="mmd", build_dir=build, always=True,
                 build_args=["--timing"] if sim == "verilator" else [])
    runner.test(hdl_toplevel="mmd", test_module=os.environ.get("TM","test_mmd"), build_dir=build, test_dir=here)


if __name__ == "__main__":
    os.environ.setdefault("COCOTB_REDUCED_LOG_FMT", "1")
    main()
