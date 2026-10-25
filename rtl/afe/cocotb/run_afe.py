"""Run all AFE/LO RTL tests (P2.5 step 2b-2c): python3 run_afe.py  [ONLY=mmd|sdm|lockdet|bandcal]."""
import os
from pathlib import Path

from cocotb_tools.runner import get_runner

UNITS = {"mmd": "test_mmd", "sdm": "test_sdm", "lockdet": "test_lockdet", "bandcal": "test_bandcal"}


def main():
    here = Path(__file__).resolve().parent
    sim = os.environ.get("SIM", "icarus")
    only = os.environ.get("ONLY")
    for top, test in UNITS.items():
        if only and only != top:
            continue
        runner = get_runner(sim)
        build = here / "sim_build" / f"{top}_{sim}"
        runner.build(sources=[here.parent / f"{top}.sv"], hdl_toplevel=top, build_dir=build, always=True,
                     build_args=["--timing"] if sim == "verilator" else [])
        runner.test(hdl_toplevel=top, test_module=test, build_dir=build, test_dir=here)


if __name__ == "__main__":
    os.environ.setdefault("COCOTB_REDUCED_LOG_FMT", "1")
    main()
