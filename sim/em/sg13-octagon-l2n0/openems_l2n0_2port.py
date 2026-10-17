# Two-port SG13_Octagon L_2n0 model for openEMS.
# Workflow code: gds2openEMS tag v0.5.0, local modules copy.
# Same GDS file as the Palace run. Stack-up XML is the openEMS
# SG13G2_200um.xml from the pinned PDK, not the XML shipped in v0.5.0.

import os
import sys

import numpy as np
from openEMS import openEMS

modules = os.environ["GDS2OPENEMS_MODULES"]
sys.path.insert(0, os.path.dirname(modules))
from modules import *

gds_filename = sys.argv[1]
XML_filename = sys.argv[2]

settings = {}
settings["preview_only"] = False
settings["preprocess_gds"] = False
settings["merge_polygon_size"] = 1.0

script_path = utilities.get_script_path(__file__)
model_basename = utilities.get_basename(__file__)
sim_path = utilities.create_sim_path(script_path, model_basename)
print("Simulation data directory:", sim_path)
os.chdir(os.path.dirname(os.path.abspath(__file__)))

settings["unit"] = 1e-6
settings["margin"] = 200
# Covers 2.4 GHz and 3.5 GHz. The upstream example uses 30 GHz and
# prints L and Q at 10 GHz. This regression stops at 6 GHz.
settings["fstart"] = 0
settings["fstop"] = 6e9
settings["numfreq"] = 61
settings["refined_cellsize"] = 1.0
settings["Boundaries"] = ["PEC", "PEC", "PEC", "PEC", "PEC", "PEC"]
settings["cells_per_wavelength"] = 20
settings["energy_limit"] = -50

simulation_ports = simulation_setup.all_simulation_ports()
simulation_ports.add_port(simulation_setup.simulation_port(
    portnumber=1, voltage=1, port_Z0=50, source_layernum=201,
    from_layername="SUBGND", to_layername="TopMetal1", direction="z"))
simulation_ports.add_port(simulation_setup.simulation_port(
    portnumber=2, voltage=1, port_Z0=50, source_layernum=202,
    from_layername="SUBGND", to_layername="TopMetal1", direction="z"))

materials_list, dielectrics_list, metals_list = stackup_reader.read_substrate(XML_filename)
layernumbers = metals_list.getlayernumbers()
layernumbers.extend(simulation_ports.portlayers)
allpolygons = gds_reader.read_gds(
    gds_filename, layernumbers, purposelist=[0], metals_list=metals_list,
    preprocess=settings["preprocess_gds"],
    merge_polygon_size=settings["merge_polygon_size"])

settings["simulation_ports"] = simulation_ports
settings["materials_list"] = materials_list
settings["dielectrics_list"] = dielectrics_list
settings["metals_list"] = metals_list
settings["layernumbers"] = layernumbers
settings["allpolygons"] = allpolygons
settings["sim_path"] = sim_path
settings["model_basename"] = model_basename
settings["numThreads"] = 8
settings["no_gui"] = True

# One excitation at a time. no_gui is an argument of runSimulation;
# runOpenEMS() does not forward it, and a missing display aborts the run.
for port in simulation_ports.ports:
    settings["excite_portnumbers"] = [port.portnumber]
    end_criteria = np.exp(settings["energy_limit"] / 10 * np.log(10))
    FDTD = openEMS(EndCriteria=end_criteria)
    FDTD.SetGaussExcite(
        (settings["fstart"] + settings["fstop"]) / 2,
        (settings["fstop"] - settings["fstart"]) / 2)
    FDTD.SetBoundaryCond(settings["Boundaries"])
    simulation_setup.setupSimulation(FDTD=FDTD, settings=settings)
    simulation_setup.runSimulation(
        FDTD=FDTD, settings=settings, no_gui=True, numThreads=8)

f = np.linspace(settings["fstart"], settings["fstop"], settings["numfreq"])
s11 = utilities.calculate_Sij(1, 1, f, sim_path, simulation_ports)
s21 = utilities.calculate_Sij(2, 1, f, sim_path, simulation_ports)
s12 = utilities.calculate_Sij(1, 2, f, sim_path, simulation_ports)
s22 = utilities.calculate_Sij(2, 2, f, sim_path, simulation_ports)
s2p_name = os.path.join(sim_path, model_basename + ".s2p")
utilities.write_snp(
    np.array([[s11, s21], [s12, s22]]), f, s2p_name,
    z0=simulation_ports.get_reference_impedance())
print("S2P", s2p_name)
