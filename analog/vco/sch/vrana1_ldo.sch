v {xschem version=3.4.7 file_version=1.2}
G {}
K {}
V {}
S {}
E {}
C {devices/iopin.sym} -200 -40 0 0 {name=vin lab=vin}
C {devices/iopin.sym} -200 -80 0 0 {name=vout lab=vout}
C {devices/iopin.sym} -200 -120 0 0 {name=vref lab=vref}
C {devices/iopin.sym} -200 -160 0 0 {name=gnd lab=gnd}
C {devices/title.sym} 0 40 0 0 {name=t1 author="HT13G-M P2.7.1"}
C {devices/lab_pin.sym} 200 40 0 0 {name=ttitle lab=vrana1_ldo_D21}
C {sg13g2_pr/sg13_lv_pmos.sym} 0 0 0 0 {name=mp
w=400u
l=0.13u
ng=80
m=1
model=sg13_lv_pmos
spiceprefix=X
}
N 20 30 20 30 {lab=vout}
C {devices/lab_pin.sym} 20 30 0 0 {name=p1 sig_type=std_logic lab=vout}
N -20 0 -20 0 {lab=vg}
C {devices/lab_pin.sym} -20 0 0 1 {name=p2 sig_type=std_logic lab=vg}
N 20 -30 20 -30 {lab=vin}
C {devices/lab_pin.sym} 20 -30 0 0 {name=p3 sig_type=std_logic lab=vin}
N 20 0 20 0 {lab=vin}
C {devices/lab_pin.sym} 20 0 0 0 {name=p4 sig_type=std_logic lab=vin}
C {devices/res.sym} 220 0 0 0 {name=rf1
value=200000.0
m=1
footprint=1206
device=resistor
sim_device=resistor
}
N 220 -30 220 -30 {lab=vout}
C {devices/lab_pin.sym} 220 -30 0 0 {name=p5 sig_type=std_logic lab=vout}
N 220 30 220 30 {lab=mid}
C {devices/lab_pin.sym} 220 30 0 0 {name=p6 sig_type=std_logic lab=mid}
C {devices/res.sym} 440 0 0 0 {name=rf2
value=200000.0
m=1
footprint=1206
device=resistor
sim_device=resistor
}
N 440 -30 440 -30 {lab=mid}
C {devices/lab_pin.sym} 440 -30 0 0 {name=p7 sig_type=std_logic lab=mid}
N 440 30 440 30 {lab=gnd}
C {devices/lab_pin.sym} 440 30 0 0 {name=p8 sig_type=std_logic lab=gnd}
C {devices/isource.sym} 660 0 0 0 {name=ib value=4e-05}
N 660 -30 660 -30 {lab=vin}
C {devices/lab_pin.sym} 660 -30 0 0 {name=p9 sig_type=std_logic lab=vin}
N 660 30 660 30 {lab=nb}
C {devices/lab_pin.sym} 660 30 0 0 {name=p10 sig_type=std_logic lab=nb}
C {sg13g2_pr/sg13_lv_nmos.sym} 880 0 0 0 {name=mb
w=4u
l=2u
ng=2
m=1
model=sg13_lv_nmos
spiceprefix=X
}
N 900 -30 900 -30 {lab=nb}
C {devices/lab_pin.sym} 900 -30 0 0 {name=p11 sig_type=std_logic lab=nb}
N 860 0 860 0 {lab=nb}
C {devices/lab_pin.sym} 860 0 0 1 {name=p12 sig_type=std_logic lab=nb}
N 900 30 900 30 {lab=gnd}
C {devices/lab_pin.sym} 900 30 0 0 {name=p13 sig_type=std_logic lab=gnd}
N 900 0 900 0 {lab=gnd}
C {devices/lab_pin.sym} 900 0 0 0 {name=p14 sig_type=std_logic lab=gnd}
C {sg13g2_pr/sg13_lv_nmos.sym} 1100 0 0 0 {name=mt
w=8u
l=2u
ng=2
m=1
model=sg13_lv_nmos
spiceprefix=X
}
N 1120 -30 1120 -30 {lab=t}
C {devices/lab_pin.sym} 1120 -30 0 0 {name=p15 sig_type=std_logic lab=t}
N 1080 0 1080 0 {lab=nb}
C {devices/lab_pin.sym} 1080 0 0 1 {name=p16 sig_type=std_logic lab=nb}
N 1120 30 1120 30 {lab=gnd}
C {devices/lab_pin.sym} 1120 30 0 0 {name=p17 sig_type=std_logic lab=gnd}
N 1120 0 1120 0 {lab=gnd}
C {devices/lab_pin.sym} 1120 0 0 0 {name=p18 sig_type=std_logic lab=gnd}
C {sg13g2_pr/sg13_lv_nmos.sym} 0 120 0 0 {name=m1
w=16u
l=2u
ng=4
m=1
model=sg13_lv_nmos
spiceprefix=X
}
N 20 90 20 90 {lab=d1}
C {devices/lab_pin.sym} 20 90 0 0 {name=p19 sig_type=std_logic lab=d1}
N -20 120 -20 120 {lab=mid}
C {devices/lab_pin.sym} -20 120 0 1 {name=p20 sig_type=std_logic lab=mid}
N 20 150 20 150 {lab=t}
C {devices/lab_pin.sym} 20 150 0 0 {name=p21 sig_type=std_logic lab=t}
N 20 120 20 120 {lab=gnd}
C {devices/lab_pin.sym} 20 120 0 0 {name=p22 sig_type=std_logic lab=gnd}
C {sg13g2_pr/sg13_lv_nmos.sym} 220 120 0 0 {name=m2
w=16u
l=2u
ng=4
m=1
model=sg13_lv_nmos
spiceprefix=X
}
N 240 90 240 90 {lab=vg}
C {devices/lab_pin.sym} 240 90 0 0 {name=p23 sig_type=std_logic lab=vg}
N 200 120 200 120 {lab=vref}
C {devices/lab_pin.sym} 200 120 0 1 {name=p24 sig_type=std_logic lab=vref}
N 240 150 240 150 {lab=t}
C {devices/lab_pin.sym} 240 150 0 0 {name=p25 sig_type=std_logic lab=t}
N 240 120 240 120 {lab=gnd}
C {devices/lab_pin.sym} 240 120 0 0 {name=p26 sig_type=std_logic lab=gnd}
C {sg13g2_pr/sg13_lv_pmos.sym} 440 120 0 0 {name=m3
w=32u
l=2u
ng=4
m=1
model=sg13_lv_pmos
spiceprefix=X
}
N 460 150 460 150 {lab=d1}
C {devices/lab_pin.sym} 460 150 0 0 {name=p27 sig_type=std_logic lab=d1}
N 420 120 420 120 {lab=d1}
C {devices/lab_pin.sym} 420 120 0 1 {name=p28 sig_type=std_logic lab=d1}
N 460 90 460 90 {lab=vin}
C {devices/lab_pin.sym} 460 90 0 0 {name=p29 sig_type=std_logic lab=vin}
N 460 120 460 120 {lab=vin}
C {devices/lab_pin.sym} 460 120 0 0 {name=p30 sig_type=std_logic lab=vin}
C {sg13g2_pr/sg13_lv_pmos.sym} 660 120 0 0 {name=m4
w=32u
l=2u
ng=4
m=1
model=sg13_lv_pmos
spiceprefix=X
}
N 680 150 680 150 {lab=vg}
C {devices/lab_pin.sym} 680 150 0 0 {name=p31 sig_type=std_logic lab=vg}
N 640 120 640 120 {lab=d1}
C {devices/lab_pin.sym} 640 120 0 1 {name=p32 sig_type=std_logic lab=d1}
N 680 90 680 90 {lab=vin}
C {devices/lab_pin.sym} 680 90 0 0 {name=p33 sig_type=std_logic lab=vin}
N 680 120 680 120 {lab=vin}
C {devices/lab_pin.sym} 680 120 0 0 {name=p34 sig_type=std_logic lab=vin}
C {devices/res.sym} 880 120 0 0 {name=rz
value=500
m=1
footprint=1206
device=resistor
sim_device=resistor
}
N 880 90 880 90 {lab=vg}
C {devices/lab_pin.sym} 880 90 0 0 {name=p35 sig_type=std_logic lab=vg}
N 880 150 880 150 {lab=ncg}
C {devices/lab_pin.sym} 880 150 0 0 {name=p36 sig_type=std_logic lab=ncg}
C {devices/capa.sym} 1100 120 0 0 {name=cg
value=1e-10
m=1
footprint=1206
device=capacitor
sim_device=capacitor
}
N 1100 90 1100 90 {lab=ncg}
C {devices/lab_pin.sym} 1100 90 0 0 {name=p37 sig_type=std_logic lab=ncg}
N 1100 150 1100 150 {lab=gnd}
C {devices/lab_pin.sym} 1100 150 0 0 {name=p38 sig_type=std_logic lab=gnd}
C {sg13g2_pr/cap_rfcmim.sym} 0 240 0 0 {name=xout
model=cap_rfcmim
lvs_model=rfcmim
w=2.581990e-04
l=2.581990e-04
wfeed=5.0e-6
m=1
mm_ok=1
spiceprefix=X
}
N 0 210 0 210 {lab=vout}
C {devices/lab_pin.sym} 0 210 0 0 {name=p39 sig_type=std_logic lab=vout}
N 0 270 0 270 {lab=gnd}
C {devices/lab_pin.sym} 0 270 0 0 {name=p40 sig_type=std_logic lab=gnd}
N -30 240 -30 240 {lab=gnd}
C {devices/lab_pin.sym} -30 240 0 0 {name=p41 sig_type=std_logic lab=gnd}
