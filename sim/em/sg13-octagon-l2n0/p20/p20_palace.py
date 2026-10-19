# P2.0 mesh-convergence variant of the L_2n0 Palace model (spec/phase2-plan.md).
# Same GDS, stack-up, ports, margins and polygon handling as ../palace_l2n0.py
# (Phase 0 baseline); only the mesh, FEM order, AMR and the frequency sweep change.
#
#   P20_TAG    name of the variant (output directory name)
#   P20_CELL   refined_cellsize in um        (baseline 5)
#   P20_ORDER  FEM order 1..3                (baseline default 2)
#   P20_AMR    adaptive mesh iterations      (baseline 0)
#   P20_FILLED 1 = conductors as filled volumes (settings['filled_metals']); baseline 0 = surface
#              impedance sheets. Upstream L6n2 vs measurement: the surface model reads Q high.
#   P20_FFC    1 = fill-factor correction for merged via arrays (settings['fill_factor_correction']);
#              baseline 0 under-estimates via resistance.
#
# Sweep: 2.0-4.5 GHz, 0.1 GHz steps, Palace adaptive frequency sweep. Covers the VCO
# range 3.12-4.20 GHz and the Phase 0 points 2.4 / 3.5 GHz.

import os
import sys

workflow = os.environ["GDS2PALACE_WORKFLOW"]
sys.path.insert(0, workflow)
from gds2palace import *

gds_filename = sys.argv[1]
XML_filename = sys.argv[2]

tag = os.environ["P20_TAG"]
cell = float(os.environ["P20_CELL"])
order = int(os.environ.get("P20_ORDER", "2"))
amr = int(os.environ.get("P20_AMR", "0"))
filled = os.environ.get("P20_FILLED", "0") == "1"
ffc = os.environ.get("P20_FFC", "0") == "1"

preprocess_gds = True
merge_polygon_size = 2

script_path = utilities.get_script_path(__file__)
model_basename = "p20_palace_" + tag
sim_path = utilities.create_sim_path(script_path, model_basename, dirname="palace_model")
print("Simulation data directory:", sim_path)
os.chdir(os.path.dirname(os.path.abspath(__file__)))

settings = {}
settings["unit"] = 1e-6
settings["margin"] = 150
settings["air_around"] = 50
settings["fstart"] = 2.0e9
settings["fstop"] = 4.5e9
settings["fstep"] = 0.1e9
settings["fdump"] = []
settings["adaptive_sweep"] = True
settings["refined_cellsize"] = cell
settings["cells_per_wavelength"] = 10
settings["meshsize_max"] = 70
settings["order"] = order
settings["adaptive_mesh_iterations"] = amr
settings["filled_metals"] = filled
settings["fill_factor_correction"] = ffc
settings["no_gui"] = True

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
    preprocess=preprocess_gds, merge_polygon_size=merge_polygon_size)

settings["simulation_ports"] = simulation_ports
settings["materials_list"] = materials_list
settings["dielectrics_list"] = dielectrics_list
settings["metals_list"] = metals_list
settings["layernumbers"] = layernumbers
settings["allpolygons"] = allpolygons
settings["sim_path"] = sim_path
settings["model_basename"] = model_basename

excite_ports = simulation_ports.all_active_excitations()
config_name, data_dir = simulation_setup.create_palace(excite_ports, settings)
print("CONFIG", config_name)
print("DATA_DIR", data_dir)
