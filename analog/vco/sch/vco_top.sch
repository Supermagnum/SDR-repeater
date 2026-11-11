v {xschem version=3.4.7 file_version=1.2}
G {}
K {}
V {}
S {}
E {}
C {devices/iopin.sym} -200 -40 0 0 {name=tp lab=tp}
C {devices/iopin.sym} -200 -80 0 0 {name=tn lab=tn}
C {devices/iopin.sym} -200 -120 0 0 {name=ct lab=ct}
C {devices/iopin.sym} -200 -160 0 0 {name=vt lab=vt}
C {devices/iopin.sym} -200 -200 0 0 {name=vdd lab=vdd}
C {devices/iopin.sym} -200 -240 0 0 {name=gnd lab=gnd}
C {devices/iopin.sym} -200 -280 0 0 {name=vbp lab=vbp}
C {devices/iopin.sym} -200 -320 0 0 {name=vbp_tail lab=vbp_tail}
C {devices/iopin.sym} -200 -360 0 0 {name=cmp lab=cmp}
C {devices/iopin.sym} -200 -400 0 0 {name=tail lab=tail}
C {devices/title.sym} 0 40 0 0 {name=t1 author="HT13G-M P2.7.1"}
C {devices/lab_pin.sym} 200 40 0 0 {name=ttitle lab=vco_top_P271}
C {l2n0.sym} 0 -200 0 0 {name=xl
p=tp
n=tn
ct=ct
}
N -80 -230 -80 -230 {lab=tp}
C {devices/lab_pin.sym} -80 -230 0 0 {name=p1 sig_type=std_logic lab=tp}
N -80 -170 -80 -170 {lab=tn}
C {devices/lab_pin.sym} -80 -170 0 0 {name=p2 sig_type=std_logic lab=tn}
N 0 -200 0 -200 {lab=ct}
C {devices/lab_pin.sym} 0 -200 0 0 {name=p3 sig_type=std_logic lab=ct}
