// Lumped differential model of SG13_Octagon_L2n0, fitted to the de-embedded EM data of P2.0
// (Palace, filled metals, 1 um; analog/vco/step1/run_step1.py). Valid 2.0-4.5 GHz, differential
// mode. The centre tap is the electrical midpoint of a symmetric split; the L2n0 GDS is a
// two-port without a tap, so the tap is an assumption until a tapped layout is EM-simulated.
// Needs models resistor, inductor, capacitor in the including netlist.
subckt l2n0(p n ct)
  r1p (p p1) resistor r=0.814837
  l1p (p1 p2) inductor l=8.05663e-10
  r2p (p2 ct) resistor r=0.827877
  l2p (p2 ct) inductor l=3.196e-11
  r1n (n n1) resistor r=0.814837
  l1n (n1 n2) inductor l=8.05663e-10
  r2n (n2 ct) resistor r=0.827877
  l2n (n2 ct) inductor l=3.196e-11
  cp (p n) capacitor c=2.98589e-14
ends
