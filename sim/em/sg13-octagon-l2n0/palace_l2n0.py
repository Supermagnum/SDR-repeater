# Two-port SG13_Octagon L_2n0 model for Palace.
# Workflow code: gds2palace_ihp_sg13g2 tag v0.8.2.
# The GDS and the stack-up XML are passed on the command line.
# Both solvers use the openEMS v0.5.0 L_2n0 GDS (valid port
# rectangles, substrate ground on layer 210) and the pinned-PDK
# file SG13G2_200um.xml from libs.tech/openems. The Palace workflow
# XML in the same PDK commit is a different stack-up and is not used.

import os
import sys

workflow = os.environ["GDS2PALACE_WORKFLOW"]
sys.path.insert(0, workflow)
from gds2palace import *

gds_filename = sys.argv[1]
XML_filename = sys.argv[2]

preprocess_gds = True
merge_polygon_size = 2

script_path = utilities.get_script_path(__file__)
model_basename = "palace_l2n0"
sim_path = utilities.create_sim_path(script_path, model_basename, dirname="palace_model")
print("Simulation data directory:", sim_path)
os.chdir(os.path.dirname(os.path.abspath(__file__)))

settings = {}
settings["unit"] = 1e-6
settings["margin"] = 150
settings["air_around"] = 50
# Exact samples requested for the regression. Adaptive sweep is off so
# Palace does not insert extra frequencies.
settings["fstart"] = 2.4e9
settings["fstop"] = 3.5e9
settings["fstep"] = 1.1e9
settings["fdump"] = []
settings["adaptive_sweep"] = False
settings["refined_cellsize"] = 5
settings["cells_per_wavelength"] = 10
settings["meshsize_max"] = 70
settings["adaptive_mesh_iterations"] = 0
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
