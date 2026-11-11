v {xschem version=3.4.7 file_version=1.2}
G {}
K {}
V {}
S {}
E {}
C {devices/iopin.sym} -200 -40 0 0 {name=tp lab=tp}
C {devices/iopin.sym} -200 -80 0 0 {name=tn lab=tn}
C {devices/iopin.sym} -200 -120 0 0 {name=tail lab=tail}
C {devices/iopin.sym} -200 -160 0 0 {name=ct lab=ct}
C {devices/iopin.sym} -200 -200 0 0 {name=vdd lab=vdd}
C {devices/iopin.sym} -200 -240 0 0 {name=gnd lab=gnd}
C {devices/title.sym} 0 40 0 0 {name=t1 author="HT13G-M P2.7.1"}
C {devices/lab_pin.sym} 200 40 0 0 {name=ttitle lab=vco_core_XC}
C {sg13g2_pr/sg13_lv_nmos.sym} 0 0 0 0 {name=m1
w=32u
l=0.13u
ng=8
m=1
model=sg13_lv_nmos
spiceprefix=X
}
N 20 -30 20 -30 {lab=tp}
C {devices/lab_pin.sym} 20 -30 0 0 {name=p1 sig_type=std_logic lab=tp}
N -20 0 -20 0 {lab=tn}
C {devices/lab_pin.sym} -20 0 0 1 {name=p2 sig_type=std_logic lab=tn}
N 20 30 20 30 {lab=tail}
C {devices/lab_pin.sym} 20 30 0 0 {name=p3 sig_type=std_logic lab=tail}
N 20 0 20 0 {lab=gnd}
C {devices/lab_pin.sym} 20 0 0 0 {name=p4 sig_type=std_logic lab=gnd}
C {sg13g2_pr/sg13_lv_nmos.sym} 220 0 0 0 {name=m2
w=32u
l=0.13u
ng=8
m=1
model=sg13_lv_nmos
spiceprefix=X
}
N 240 -30 240 -30 {lab=tn}
C {devices/lab_pin.sym} 240 -30 0 0 {name=p5 sig_type=std_logic lab=tn}
N 200 0 200 0 {lab=tp}
C {devices/lab_pin.sym} 200 0 0 1 {name=p6 sig_type=std_logic lab=tp}
N 240 30 240 30 {lab=tail}
C {devices/lab_pin.sym} 240 30 0 0 {name=p7 sig_type=std_logic lab=tail}
N 240 0 240 0 {lab=gnd}
C {devices/lab_pin.sym} 240 0 0 0 {name=p8 sig_type=std_logic lab=gnd}
C {sg13g2_pr/cap_rfcmim.sym} 440 0 0 0 {name=xf1
model=cap_rfcmim
lvs_model=rfcmim
w=1.624600e-05
l=1.624600e-05
wfeed=5.0e-6
m=1
mm_ok=1
spiceprefix=X
}
N 440 -30 440 -30 {lab=tp}
C {devices/lab_pin.sym} 440 -30 0 0 {name=p9 sig_type=std_logic lab=tp}
N 440 30 440 30 {lab=fx}
C {devices/lab_pin.sym} 440 30 0 0 {name=p10 sig_type=std_logic lab=fx}
N 410 0 410 0 {lab=gnd}
C {devices/lab_pin.sym} 410 0 0 0 {name=p11 sig_type=std_logic lab=gnd}
C {sg13g2_pr/cap_rfcmim.sym} 660 0 0 0 {name=xf2
model=cap_rfcmim
lvs_model=rfcmim
w=1.624600e-05
l=1.624600e-05
wfeed=5.0e-6
m=1
mm_ok=1
spiceprefix=X
}
N 660 -30 660 -30 {lab=tn}
C {devices/lab_pin.sym} 660 -30 0 0 {name=p12 sig_type=std_logic lab=tn}
N 660 30 660 30 {lab=fx}
C {devices/lab_pin.sym} 660 30 0 0 {name=p13 sig_type=std_logic lab=fx}
N 630 0 630 0 {lab=gnd}
C {devices/lab_pin.sym} 630 0 0 0 {name=p14 sig_type=std_logic lab=gnd}
C {devices/res.sym} 880 0 0 0 {name=rfx
value=200000.0
m=1
footprint=1206
device=resistor
sim_device=resistor
}
N 880 -30 880 -30 {lab=fx}
C {devices/lab_pin.sym} 880 -30 0 0 {name=p15 sig_type=std_logic lab=fx}
N 880 30 880 30 {lab=gnd}
C {devices/lab_pin.sym} 880 30 0 0 {name=p16 sig_type=std_logic lab=gnd}
