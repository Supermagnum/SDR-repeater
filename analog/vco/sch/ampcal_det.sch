v {xschem version=3.4.7 file_version=1.2}
G {}
K {}
V {}
S {}
E {}
C {devices/iopin.sym} -200 -40 0 0 {name=tp lab=tp}
C {devices/iopin.sym} -200 -80 0 0 {name=tn lab=tn}
C {devices/iopin.sym} -200 -120 0 0 {name=ct lab=ct}
C {devices/iopin.sym} -200 -160 0 0 {name=vdd lab=vdd}
C {devices/iopin.sym} -200 -200 0 0 {name=gnd lab=gnd}
C {devices/iopin.sym} -200 -240 0 0 {name=cmp lab=cmp}
C {devices/iopin.sym} -200 -280 0 0 {name=hold lab=hold}
C {devices/iopin.sym} -200 -320 0 0 {name=rep lab=rep}
C {devices/title.sym} 0 40 0 0 {name=t1 author="HT13G-M P2.7.1"}
C {devices/lab_pin.sym} 200 40 0 0 {name=ttitle lab=ampcal_det_cmp_D22}
C {sg13g2_pr/sg13_lv_nmos.sym} 0 0 0 0 {name=mdtp
w=0.5u
l=0.13u
ng=1
m=1
model=sg13_lv_nmos
spiceprefix=X
}
N 20 -30 20 -30 {lab=vdd}
C {devices/lab_pin.sym} 20 -30 0 0 {name=p1 sig_type=std_logic lab=vdd}
N -20 0 -20 0 {lab=tp}
C {devices/lab_pin.sym} -20 0 0 1 {name=p2 sig_type=std_logic lab=tp}
N 20 30 20 30 {lab=hold}
C {devices/lab_pin.sym} 20 30 0 0 {name=p3 sig_type=std_logic lab=hold}
N 20 0 20 0 {lab=gnd}
C {devices/lab_pin.sym} 20 0 0 0 {name=p4 sig_type=std_logic lab=gnd}
C {sg13g2_pr/sg13_lv_nmos.sym} 220 0 0 0 {name=mdtn
w=0.5u
l=0.13u
ng=1
m=1
model=sg13_lv_nmos
spiceprefix=X
}
N 240 -30 240 -30 {lab=vdd}
C {devices/lab_pin.sym} 240 -30 0 0 {name=p5 sig_type=std_logic lab=vdd}
N 200 0 200 0 {lab=tn}
C {devices/lab_pin.sym} 200 0 0 1 {name=p6 sig_type=std_logic lab=tn}
N 240 30 240 30 {lab=hold}
C {devices/lab_pin.sym} 240 30 0 0 {name=p7 sig_type=std_logic lab=hold}
N 240 0 240 0 {lab=gnd}
C {devices/lab_pin.sym} 240 0 0 0 {name=p8 sig_type=std_logic lab=gnd}
C {devices/isource.sym} 440 0 0 0 {name=idet value=4e-06}
N 440 -30 440 -30 {lab=hold}
C {devices/lab_pin.sym} 440 -30 0 0 {name=p9 sig_type=std_logic lab=hold}
N 440 30 440 30 {lab=gnd}
C {devices/lab_pin.sym} 440 30 0 0 {name=p10 sig_type=std_logic lab=gnd}
C {devices/capa.sym} 660 0 0 0 {name=chold
value=4e-13
m=1
footprint=1206
device=capacitor
sim_device=capacitor
}
N 660 -30 660 -30 {lab=hold}
C {devices/lab_pin.sym} 660 -30 0 0 {name=p11 sig_type=std_logic lab=hold}
N 660 30 660 30 {lab=gnd}
C {devices/lab_pin.sym} 660 30 0 0 {name=p12 sig_type=std_logic lab=gnd}
C {sg13g2_pr/sg13_lv_nmos.sym} 880 0 0 0 {name=mrtp
w=0.5u
l=0.13u
ng=1
m=1
model=sg13_lv_nmos
spiceprefix=X
}
N 900 -30 900 -30 {lab=vdd}
C {devices/lab_pin.sym} 900 -30 0 0 {name=p13 sig_type=std_logic lab=vdd}
N 860 0 860 0 {lab=ct}
C {devices/lab_pin.sym} 860 0 0 1 {name=p14 sig_type=std_logic lab=ct}
N 900 30 900 30 {lab=rep}
C {devices/lab_pin.sym} 900 30 0 0 {name=p15 sig_type=std_logic lab=rep}
N 900 0 900 0 {lab=gnd}
C {devices/lab_pin.sym} 900 0 0 0 {name=p16 sig_type=std_logic lab=gnd}
C {sg13g2_pr/sg13_lv_nmos.sym} 1100 0 0 0 {name=mrtn
w=0.5u
l=0.13u
ng=1
m=1
model=sg13_lv_nmos
spiceprefix=X
}
N 1120 -30 1120 -30 {lab=vdd}
C {devices/lab_pin.sym} 1120 -30 0 0 {name=p17 sig_type=std_logic lab=vdd}
N 1080 0 1080 0 {lab=ct}
C {devices/lab_pin.sym} 1080 0 0 1 {name=p18 sig_type=std_logic lab=ct}
N 1120 30 1120 30 {lab=rep}
C {devices/lab_pin.sym} 1120 30 0 0 {name=p19 sig_type=std_logic lab=rep}
N 1120 0 1120 0 {lab=gnd}
C {devices/lab_pin.sym} 1120 0 0 0 {name=p20 sig_type=std_logic lab=gnd}
C {devices/isource.sym} 0 120 0 0 {name=irep value=4e-06}
N 0 90 0 90 {lab=rep}
C {devices/lab_pin.sym} 0 90 0 0 {name=p21 sig_type=std_logic lab=rep}
N 0 150 0 150 {lab=gnd}
C {devices/lab_pin.sym} 0 150 0 0 {name=p22 sig_type=std_logic lab=gnd}
C {devices/capa.sym} 220 120 0 0 {name=crep
value=4e-13
m=1
footprint=1206
device=capacitor
sim_device=capacitor
}
N 220 90 220 90 {lab=rep}
C {devices/lab_pin.sym} 220 90 0 0 {name=p23 sig_type=std_logic lab=rep}
N 220 150 220 150 {lab=gnd}
C {devices/lab_pin.sym} 220 150 0 0 {name=p24 sig_type=std_logic lab=gnd}
C {devices/vsource.sym} 440 120 0 0 {name=vth value=0.405}
N 440 90 440 90 {lab=vthn}
C {devices/lab_pin.sym} 440 90 0 0 {name=p25 sig_type=std_logic lab=vthn}
N 440 150 440 150 {lab=rep}
C {devices/lab_pin.sym} 440 150 0 0 {name=p26 sig_type=std_logic lab=rep}
C {sg13g2_pr/sg13_lv_nmos.sym} 660 120 0 0 {name=mc1
w=4u
l=0.5u
ng=2
m=1
model=sg13_lv_nmos
spiceprefix=X
}
N 680 90 680 90 {lab=co}
C {devices/lab_pin.sym} 680 90 0 0 {name=p27 sig_type=std_logic lab=co}
N 640 120 640 120 {lab=hold}
C {devices/lab_pin.sym} 640 120 0 1 {name=p28 sig_type=std_logic lab=hold}
N 680 150 680 150 {lab=ttail}
C {devices/lab_pin.sym} 680 150 0 0 {name=p29 sig_type=std_logic lab=ttail}
N 680 120 680 120 {lab=gnd}
C {devices/lab_pin.sym} 680 120 0 0 {name=p30 sig_type=std_logic lab=gnd}
C {sg13g2_pr/sg13_lv_nmos.sym} 880 120 0 0 {name=mc2
w=4u
l=0.5u
ng=2
m=1
model=sg13_lv_nmos
spiceprefix=X
}
N 900 90 900 90 {lab=co2}
C {devices/lab_pin.sym} 900 90 0 0 {name=p31 sig_type=std_logic lab=co2}
N 860 120 860 120 {lab=vthn}
C {devices/lab_pin.sym} 860 120 0 1 {name=p32 sig_type=std_logic lab=vthn}
N 900 150 900 150 {lab=ttail}
C {devices/lab_pin.sym} 900 150 0 0 {name=p33 sig_type=std_logic lab=ttail}
N 900 120 900 120 {lab=gnd}
C {devices/lab_pin.sym} 900 120 0 0 {name=p34 sig_type=std_logic lab=gnd}
C {devices/isource.sym} 1100 120 0 0 {name=itt value=2e-05}
N 1100 90 1100 90 {lab=ttail}
C {devices/lab_pin.sym} 1100 90 0 0 {name=p35 sig_type=std_logic lab=ttail}
N 1100 150 1100 150 {lab=gnd}
C {devices/lab_pin.sym} 1100 150 0 0 {name=p36 sig_type=std_logic lab=gnd}
C {devices/res.sym} 0 240 0 0 {name=rc1
value=20000.0
m=1
footprint=1206
device=resistor
sim_device=resistor
}
N 0 210 0 210 {lab=vdd}
C {devices/lab_pin.sym} 0 210 0 0 {name=p37 sig_type=std_logic lab=vdd}
N 0 270 0 270 {lab=co}
C {devices/lab_pin.sym} 0 270 0 0 {name=p38 sig_type=std_logic lab=co}
C {devices/res.sym} 220 240 0 0 {name=rc2
value=20000.0
m=1
footprint=1206
device=resistor
sim_device=resistor
}
N 220 210 220 210 {lab=vdd}
C {devices/lab_pin.sym} 220 210 0 0 {name=p39 sig_type=std_logic lab=vdd}
N 220 270 220 270 {lab=co2}
C {devices/lab_pin.sym} 220 270 0 0 {name=p40 sig_type=std_logic lab=co2}
C {sg13g2_pr/sg13_lv_nmos.sym} 440 240 0 0 {name=mcs1
w=4u
l=0.5u
ng=2
m=1
model=sg13_lv_nmos
spiceprefix=X
}
N 460 210 460 210 {lab=n1}
C {devices/lab_pin.sym} 460 210 0 0 {name=p41 sig_type=std_logic lab=n1}
N 420 240 420 240 {lab=co2}
C {devices/lab_pin.sym} 420 240 0 1 {name=p42 sig_type=std_logic lab=co2}
N 460 270 460 270 {lab=ss2}
C {devices/lab_pin.sym} 460 270 0 0 {name=p43 sig_type=std_logic lab=ss2}
N 460 240 460 240 {lab=gnd}
C {devices/lab_pin.sym} 460 240 0 0 {name=p44 sig_type=std_logic lab=gnd}
C {sg13g2_pr/sg13_lv_nmos.sym} 660 240 0 0 {name=mcs2
w=4u
l=0.5u
ng=2
m=1
model=sg13_lv_nmos
spiceprefix=X
}
N 680 210 680 210 {lab=cmp}
C {devices/lab_pin.sym} 680 210 0 0 {name=p45 sig_type=std_logic lab=cmp}
N 640 240 640 240 {lab=co}
C {devices/lab_pin.sym} 640 240 0 1 {name=p46 sig_type=std_logic lab=co}
N 680 270 680 270 {lab=ss2}
C {devices/lab_pin.sym} 680 270 0 0 {name=p47 sig_type=std_logic lab=ss2}
N 680 240 680 240 {lab=gnd}
C {devices/lab_pin.sym} 680 240 0 0 {name=p48 sig_type=std_logic lab=gnd}
C {devices/isource.sym} 880 240 0 0 {name=iss2 value=2e-05}
N 880 210 880 210 {lab=ss2}
C {devices/lab_pin.sym} 880 210 0 0 {name=p49 sig_type=std_logic lab=ss2}
N 880 270 880 270 {lab=gnd}
C {devices/lab_pin.sym} 880 270 0 0 {name=p50 sig_type=std_logic lab=gnd}
C {sg13g2_pr/sg13_lv_pmos.sym} 1100 240 0 0 {name=mpl1
w=4u
l=0.5u
ng=2
m=1
model=sg13_lv_pmos
spiceprefix=X
}
N 1120 270 1120 270 {lab=n1}
C {devices/lab_pin.sym} 1120 270 0 0 {name=p51 sig_type=std_logic lab=n1}
N 1080 240 1080 240 {lab=n1}
C {devices/lab_pin.sym} 1080 240 0 1 {name=p52 sig_type=std_logic lab=n1}
N 1120 210 1120 210 {lab=vdd}
C {devices/lab_pin.sym} 1120 210 0 0 {name=p53 sig_type=std_logic lab=vdd}
N 1120 240 1120 240 {lab=vdd}
C {devices/lab_pin.sym} 1120 240 0 0 {name=p54 sig_type=std_logic lab=vdd}
C {sg13g2_pr/sg13_lv_pmos.sym} 0 360 0 0 {name=mpl2
w=4u
l=0.5u
ng=2
m=1
model=sg13_lv_pmos
spiceprefix=X
}
N 20 390 20 390 {lab=cmp}
C {devices/lab_pin.sym} 20 390 0 0 {name=p55 sig_type=std_logic lab=cmp}
N -20 360 -20 360 {lab=n1}
C {devices/lab_pin.sym} -20 360 0 1 {name=p56 sig_type=std_logic lab=n1}
N 20 330 20 330 {lab=vdd}
C {devices/lab_pin.sym} 20 330 0 0 {name=p57 sig_type=std_logic lab=vdd}
N 20 360 20 360 {lab=vdd}
C {devices/lab_pin.sym} 20 360 0 0 {name=p58 sig_type=std_logic lab=vdd}
C {devices/capa.sym} 220 360 0 0 {name=cl_cmp
value=5e-14
m=1
footprint=1206
device=capacitor
sim_device=capacitor
}
N 220 330 220 330 {lab=cmp}
C {devices/lab_pin.sym} 220 330 0 0 {name=p59 sig_type=std_logic lab=cmp}
N 220 390 220 390 {lab=gnd}
C {devices/lab_pin.sym} 220 390 0 0 {name=p60 sig_type=std_logic lab=gnd}
