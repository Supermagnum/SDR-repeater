v {xschem version=3.4.7 file_version=1.2}
G {}
K {}
V {}
S {}
E {}
C {devices/iopin.sym} -200 -40 0 0 {name=p lab=p}
C {devices/iopin.sym} -200 -80 0 0 {name=n lab=n}
C {devices/iopin.sym} -200 -120 0 0 {name=ct lab=ct}
C {devices/title.sym} 0 40 0 0 {name=t1 author="HT13G-M P2.7.1"}
C {devices/lab_pin.sym} 200 40 0 0 {name=ttitle lab=l2n0_EM_lumped}
C {devices/res.sym} 0 0 0 0 {name=r1p
value=0.814837
m=1
footprint=1206
device=resistor
sim_device=resistor
}
N 0 -30 0 -30 {lab=p}
C {devices/lab_pin.sym} 0 -30 0 0 {name=p1 sig_type=std_logic lab=p}
N 0 30 0 30 {lab=p1}
C {devices/lab_pin.sym} 0 30 0 0 {name=p2 sig_type=std_logic lab=p1}
C {devices/ind.sym} 220 0 0 0 {name=l1p
value=8.05663e-10
m=1
footprint=1206
device=inductor
sim_device=inductor
}
N 220 -30 220 -30 {lab=p1}
C {devices/lab_pin.sym} 220 -30 0 0 {name=p3 sig_type=std_logic lab=p1}
N 220 30 220 30 {lab=p2}
C {devices/lab_pin.sym} 220 30 0 0 {name=p4 sig_type=std_logic lab=p2}
C {devices/res.sym} 440 0 0 0 {name=r2p
value=0.827877
m=1
footprint=1206
device=resistor
sim_device=resistor
}
N 440 -30 440 -30 {lab=p2}
C {devices/lab_pin.sym} 440 -30 0 0 {name=p5 sig_type=std_logic lab=p2}
N 440 30 440 30 {lab=ct}
C {devices/lab_pin.sym} 440 30 0 0 {name=p6 sig_type=std_logic lab=ct}
C {devices/ind.sym} 660 0 0 0 {name=l2p
value=3.196e-11
m=1
footprint=1206
device=inductor
sim_device=inductor
}
N 660 -30 660 -30 {lab=p2}
C {devices/lab_pin.sym} 660 -30 0 0 {name=p7 sig_type=std_logic lab=p2}
N 660 30 660 30 {lab=ct}
C {devices/lab_pin.sym} 660 30 0 0 {name=p8 sig_type=std_logic lab=ct}
C {devices/res.sym} 880 0 0 0 {name=r1n
value=0.814837
m=1
footprint=1206
device=resistor
sim_device=resistor
}
N 880 -30 880 -30 {lab=n}
C {devices/lab_pin.sym} 880 -30 0 0 {name=p9 sig_type=std_logic lab=n}
N 880 30 880 30 {lab=n1}
C {devices/lab_pin.sym} 880 30 0 0 {name=p10 sig_type=std_logic lab=n1}
C {devices/ind.sym} 1100 0 0 0 {name=l1n
value=8.05663e-10
m=1
footprint=1206
device=inductor
sim_device=inductor
}
N 1100 -30 1100 -30 {lab=n1}
C {devices/lab_pin.sym} 1100 -30 0 0 {name=p11 sig_type=std_logic lab=n1}
N 1100 30 1100 30 {lab=n2}
C {devices/lab_pin.sym} 1100 30 0 0 {name=p12 sig_type=std_logic lab=n2}
C {devices/res.sym} 0 120 0 0 {name=r2n
value=0.827877
m=1
footprint=1206
device=resistor
sim_device=resistor
}
N 0 90 0 90 {lab=n2}
C {devices/lab_pin.sym} 0 90 0 0 {name=p13 sig_type=std_logic lab=n2}
N 0 150 0 150 {lab=ct}
C {devices/lab_pin.sym} 0 150 0 0 {name=p14 sig_type=std_logic lab=ct}
C {devices/ind.sym} 220 120 0 0 {name=l2n
value=3.196e-11
m=1
footprint=1206
device=inductor
sim_device=inductor
}
N 220 90 220 90 {lab=n2}
C {devices/lab_pin.sym} 220 90 0 0 {name=p15 sig_type=std_logic lab=n2}
N 220 150 220 150 {lab=ct}
C {devices/lab_pin.sym} 220 150 0 0 {name=p16 sig_type=std_logic lab=ct}
C {devices/capa.sym} 440 120 0 0 {name=cp
value=2.98589e-14
m=1
footprint=1206
device=capacitor
sim_device=capacitor
}
N 440 90 440 90 {lab=p}
C {devices/lab_pin.sym} 440 90 0 0 {name=p17 sig_type=std_logic lab=p}
N 440 150 440 150 {lab=n}
C {devices/lab_pin.sym} 440 150 0 0 {name=p18 sig_type=std_logic lab=n}
