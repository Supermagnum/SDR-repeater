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
C {devices/title.sym} 0 40 0 0 {name=t1 author="HT13G-M P2.7.1"}
C {devices/lab_pin.sym} 200 40 0 0 {name=ttitle lab=vco_sim_flat_step2}
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
C {sg13g2_pr/sg13_lv_nmos.sym} 660 120 0 0 {name=m1
w=32u
l=0.13u
ng=8
m=1
model=sg13_lv_nmos
spiceprefix=X
}
N 680 90 680 90 {lab=tp}
C {devices/lab_pin.sym} 680 90 0 0 {name=p19 sig_type=std_logic lab=tp}
N 640 120 640 120 {lab=tn}
C {devices/lab_pin.sym} 640 120 0 1 {name=p20 sig_type=std_logic lab=tn}
N 680 150 680 150 {lab=tail}
C {devices/lab_pin.sym} 680 150 0 0 {name=p21 sig_type=std_logic lab=tail}
N 680 120 680 120 {lab=gnd}
C {devices/lab_pin.sym} 680 120 0 0 {name=p22 sig_type=std_logic lab=gnd}
C {sg13g2_pr/sg13_lv_nmos.sym} 880 120 0 0 {name=m2
w=32u
l=0.13u
ng=8
m=1
model=sg13_lv_nmos
spiceprefix=X
}
N 900 90 900 90 {lab=tn}
C {devices/lab_pin.sym} 900 90 0 0 {name=p23 sig_type=std_logic lab=tn}
N 860 120 860 120 {lab=tp}
C {devices/lab_pin.sym} 860 120 0 1 {name=p24 sig_type=std_logic lab=tp}
N 900 150 900 150 {lab=tail}
C {devices/lab_pin.sym} 900 150 0 0 {name=p25 sig_type=std_logic lab=tail}
N 900 120 900 120 {lab=gnd}
C {devices/lab_pin.sym} 900 120 0 0 {name=p26 sig_type=std_logic lab=gnd}
C {sg13g2_pr/cap_rfcmim.sym} 1100 120 0 0 {name=xf1
model=cap_rfcmim
lvs_model=rfcmim
w=1.640200e-05
l=1.640200e-05
wfeed=5.0e-6
m=1
mm_ok=1
spiceprefix=X
}
N 1100 90 1100 90 {lab=tp}
C {devices/lab_pin.sym} 1100 90 0 0 {name=p27 sig_type=std_logic lab=tp}
N 1100 150 1100 150 {lab=fx}
C {devices/lab_pin.sym} 1100 150 0 0 {name=p28 sig_type=std_logic lab=fx}
N 1070 120 1070 120 {lab=gnd}
C {devices/lab_pin.sym} 1070 120 0 0 {name=p29 sig_type=std_logic lab=gnd}
C {sg13g2_pr/cap_rfcmim.sym} 0 240 0 0 {name=xf2
model=cap_rfcmim
lvs_model=rfcmim
w=1.640200e-05
l=1.640200e-05
wfeed=5.0e-6
m=1
mm_ok=1
spiceprefix=X
}
N 0 210 0 210 {lab=tn}
C {devices/lab_pin.sym} 0 210 0 0 {name=p30 sig_type=std_logic lab=tn}
N 0 270 0 270 {lab=fx}
C {devices/lab_pin.sym} 0 270 0 0 {name=p31 sig_type=std_logic lab=fx}
N -30 240 -30 240 {lab=gnd}
C {devices/lab_pin.sym} -30 240 0 0 {name=p32 sig_type=std_logic lab=gnd}
C {devices/res.sym} 220 240 0 0 {name=rfx
value=200000.0
m=1
footprint=1206
device=resistor
sim_device=resistor
}
N 220 210 220 210 {lab=fx}
C {devices/lab_pin.sym} 220 210 0 0 {name=p33 sig_type=std_logic lab=fx}
N 220 270 220 270 {lab=gnd}
C {devices/lab_pin.sym} 220 270 0 0 {name=p34 sig_type=std_logic lab=gnd}
C {sg13g2_pr/cap_rfcmim.sym} 440 240 0 0 {name=xb0p
model=cap_rfcmim
lvs_model=rfcmim
w=2.844000e-06
l=2.844000e-06
wfeed=5.0e-6
m=1
mm_ok=1
spiceprefix=X
}
N 440 210 440 210 {lab=tp}
C {devices/lab_pin.sym} 440 210 0 0 {name=p35 sig_type=std_logic lab=tp}
N 440 270 440 270 {lab=a0}
C {devices/lab_pin.sym} 440 270 0 0 {name=p36 sig_type=std_logic lab=a0}
N 410 240 410 240 {lab=gnd}
C {devices/lab_pin.sym} 410 240 0 0 {name=p37 sig_type=std_logic lab=gnd}
C {sg13g2_pr/cap_rfcmim.sym} 660 240 0 0 {name=xb0n
model=cap_rfcmim
lvs_model=rfcmim
w=2.844000e-06
l=2.844000e-06
wfeed=5.0e-6
m=1
mm_ok=1
spiceprefix=X
}
N 660 210 660 210 {lab=tn}
C {devices/lab_pin.sym} 660 210 0 0 {name=p38 sig_type=std_logic lab=tn}
N 660 270 660 270 {lab=b0}
C {devices/lab_pin.sym} 660 270 0 0 {name=p39 sig_type=std_logic lab=b0}
N 630 240 630 240 {lab=gnd}
C {devices/lab_pin.sym} 630 240 0 0 {name=p40 sig_type=std_logic lab=gnd}
C {sg13g2_pr/sg13_lv_nmos.sym} 880 240 0 0 {name=ms0
w=10.11u
l=0.13u
ng=4
m=1
model=sg13_lv_nmos
spiceprefix=X
}
N 900 210 900 210 {lab=a0}
C {devices/lab_pin.sym} 900 210 0 0 {name=p41 sig_type=std_logic lab=a0}
N 860 240 860 240 {lab=g0}
C {devices/lab_pin.sym} 860 240 0 1 {name=p42 sig_type=std_logic lab=g0}
N 900 270 900 270 {lab=b0}
C {devices/lab_pin.sym} 900 270 0 0 {name=p43 sig_type=std_logic lab=b0}
N 900 240 900 240 {lab=gnd}
C {devices/lab_pin.sym} 900 240 0 0 {name=p44 sig_type=std_logic lab=gnd}
C {devices/res.sym} 1100 240 0 0 {name=rba0
value=2000000.0
m=1
footprint=1206
device=resistor
sim_device=resistor
}
N 1100 210 1100 210 {lab=a0}
C {devices/lab_pin.sym} 1100 210 0 0 {name=p45 sig_type=std_logic lab=a0}
N 1100 270 1100 270 {lab=bb0}
C {devices/lab_pin.sym} 1100 270 0 0 {name=p46 sig_type=std_logic lab=bb0}
C {devices/res.sym} 0 360 0 0 {name=rbb0
value=2000000.0
m=1
footprint=1206
device=resistor
sim_device=resistor
}
N 0 330 0 330 {lab=b0}
C {devices/lab_pin.sym} 0 330 0 0 {name=p47 sig_type=std_logic lab=b0}
N 0 390 0 390 {lab=bb0}
C {devices/lab_pin.sym} 0 390 0 0 {name=p48 sig_type=std_logic lab=bb0}
C {sg13g2_pr/sg13_lv_nmos.sym} 220 360 0 0 {name=mbp_rba0
w=5u
l=0.13u
ng=2
m=1
model=sg13_lv_nmos
spiceprefix=X
}
N 240 330 240 330 {lab=a0}
C {devices/lab_pin.sym} 240 330 0 0 {name=p49 sig_type=std_logic lab=a0}
N 200 360 200 360 {lab=vbp}
C {devices/lab_pin.sym} 200 360 0 1 {name=p50 sig_type=std_logic lab=vbp}
N 240 390 240 390 {lab=bb0}
C {devices/lab_pin.sym} 240 390 0 0 {name=p51 sig_type=std_logic lab=bb0}
N 240 360 240 360 {lab=gnd}
C {devices/lab_pin.sym} 240 360 0 0 {name=p52 sig_type=std_logic lab=gnd}
C {sg13g2_pr/sg13_lv_nmos.sym} 440 360 0 0 {name=mbp_rbb0
w=5u
l=0.13u
ng=2
m=1
model=sg13_lv_nmos
spiceprefix=X
}
N 460 330 460 330 {lab=b0}
C {devices/lab_pin.sym} 460 330 0 0 {name=p53 sig_type=std_logic lab=b0}
N 420 360 420 360 {lab=vbp}
C {devices/lab_pin.sym} 420 360 0 1 {name=p54 sig_type=std_logic lab=vbp}
N 460 390 460 390 {lab=bb0}
C {devices/lab_pin.sym} 460 390 0 0 {name=p55 sig_type=std_logic lab=bb0}
N 460 360 460 360 {lab=gnd}
C {devices/lab_pin.sym} 460 360 0 0 {name=p56 sig_type=std_logic lab=gnd}
C {sg13g2_pr/cap_rfcmim.sym} 660 360 0 0 {name=xb1p
model=cap_rfcmim
lvs_model=rfcmim
w=3.964000e-06
l=3.964000e-06
wfeed=5.0e-6
m=1
mm_ok=1
spiceprefix=X
}
N 660 330 660 330 {lab=tp}
C {devices/lab_pin.sym} 660 330 0 0 {name=p57 sig_type=std_logic lab=tp}
N 660 390 660 390 {lab=a1}
C {devices/lab_pin.sym} 660 390 0 0 {name=p58 sig_type=std_logic lab=a1}
N 630 360 630 360 {lab=gnd}
C {devices/lab_pin.sym} 630 360 0 0 {name=p59 sig_type=std_logic lab=gnd}
C {sg13g2_pr/cap_rfcmim.sym} 880 360 0 0 {name=xb1n
model=cap_rfcmim
lvs_model=rfcmim
w=3.964000e-06
l=3.964000e-06
wfeed=5.0e-6
m=1
mm_ok=1
spiceprefix=X
}
N 880 330 880 330 {lab=tn}
C {devices/lab_pin.sym} 880 330 0 0 {name=p60 sig_type=std_logic lab=tn}
N 880 390 880 390 {lab=b1}
C {devices/lab_pin.sym} 880 390 0 0 {name=p61 sig_type=std_logic lab=b1}
N 850 360 850 360 {lab=gnd}
C {devices/lab_pin.sym} 850 360 0 0 {name=p62 sig_type=std_logic lab=gnd}
C {sg13g2_pr/sg13_lv_nmos.sym} 1100 360 0 0 {name=ms1
w=19.64u
l=0.13u
ng=8
m=1
model=sg13_lv_nmos
spiceprefix=X
}
N 1120 330 1120 330 {lab=a1}
C {devices/lab_pin.sym} 1120 330 0 0 {name=p63 sig_type=std_logic lab=a1}
N 1080 360 1080 360 {lab=g1}
C {devices/lab_pin.sym} 1080 360 0 1 {name=p64 sig_type=std_logic lab=g1}
N 1120 390 1120 390 {lab=b1}
C {devices/lab_pin.sym} 1120 390 0 0 {name=p65 sig_type=std_logic lab=b1}
N 1120 360 1120 360 {lab=gnd}
C {devices/lab_pin.sym} 1120 360 0 0 {name=p66 sig_type=std_logic lab=gnd}
C {devices/res.sym} 0 480 0 0 {name=rba1
value=2000000.0
m=1
footprint=1206
device=resistor
sim_device=resistor
}
N 0 450 0 450 {lab=a1}
C {devices/lab_pin.sym} 0 450 0 0 {name=p67 sig_type=std_logic lab=a1}
N 0 510 0 510 {lab=bb1}
C {devices/lab_pin.sym} 0 510 0 0 {name=p68 sig_type=std_logic lab=bb1}
C {devices/res.sym} 220 480 0 0 {name=rbb1
value=2000000.0
m=1
footprint=1206
device=resistor
sim_device=resistor
}
N 220 450 220 450 {lab=b1}
C {devices/lab_pin.sym} 220 450 0 0 {name=p69 sig_type=std_logic lab=b1}
N 220 510 220 510 {lab=bb1}
C {devices/lab_pin.sym} 220 510 0 0 {name=p70 sig_type=std_logic lab=bb1}
C {sg13g2_pr/sg13_lv_nmos.sym} 440 480 0 0 {name=mbp_rba1
w=5u
l=0.13u
ng=2
m=1
model=sg13_lv_nmos
spiceprefix=X
}
N 460 450 460 450 {lab=a1}
C {devices/lab_pin.sym} 460 450 0 0 {name=p71 sig_type=std_logic lab=a1}
N 420 480 420 480 {lab=vbp}
C {devices/lab_pin.sym} 420 480 0 1 {name=p72 sig_type=std_logic lab=vbp}
N 460 510 460 510 {lab=bb1}
C {devices/lab_pin.sym} 460 510 0 0 {name=p73 sig_type=std_logic lab=bb1}
N 460 480 460 480 {lab=gnd}
C {devices/lab_pin.sym} 460 480 0 0 {name=p74 sig_type=std_logic lab=gnd}
C {sg13g2_pr/sg13_lv_nmos.sym} 660 480 0 0 {name=mbp_rbb1
w=5u
l=0.13u
ng=2
m=1
model=sg13_lv_nmos
spiceprefix=X
}
N 680 450 680 450 {lab=b1}
C {devices/lab_pin.sym} 680 450 0 0 {name=p75 sig_type=std_logic lab=b1}
N 640 480 640 480 {lab=vbp}
C {devices/lab_pin.sym} 640 480 0 1 {name=p76 sig_type=std_logic lab=vbp}
N 680 510 680 510 {lab=bb1}
C {devices/lab_pin.sym} 680 510 0 0 {name=p77 sig_type=std_logic lab=bb1}
N 680 480 680 480 {lab=gnd}
C {devices/lab_pin.sym} 680 480 0 0 {name=p78 sig_type=std_logic lab=gnd}
C {sg13g2_pr/cap_rfcmim.sym} 880 480 0 0 {name=xb2p
model=cap_rfcmim
lvs_model=rfcmim
w=5.564000e-06
l=5.564000e-06
wfeed=5.0e-6
m=1
mm_ok=1
spiceprefix=X
}
N 880 450 880 450 {lab=tp}
C {devices/lab_pin.sym} 880 450 0 0 {name=p79 sig_type=std_logic lab=tp}
N 880 510 880 510 {lab=a2}
C {devices/lab_pin.sym} 880 510 0 0 {name=p80 sig_type=std_logic lab=a2}
N 850 480 850 480 {lab=gnd}
C {devices/lab_pin.sym} 850 480 0 0 {name=p81 sig_type=std_logic lab=gnd}
C {sg13g2_pr/cap_rfcmim.sym} 1100 480 0 0 {name=xb2n
model=cap_rfcmim
lvs_model=rfcmim
w=5.564000e-06
l=5.564000e-06
wfeed=5.0e-6
m=1
mm_ok=1
spiceprefix=X
}
N 1100 450 1100 450 {lab=tn}
C {devices/lab_pin.sym} 1100 450 0 0 {name=p82 sig_type=std_logic lab=tn}
N 1100 510 1100 510 {lab=b2}
C {devices/lab_pin.sym} 1100 510 0 0 {name=p83 sig_type=std_logic lab=b2}
N 1070 480 1070 480 {lab=gnd}
C {devices/lab_pin.sym} 1070 480 0 0 {name=p84 sig_type=std_logic lab=gnd}
C {sg13g2_pr/sg13_lv_nmos.sym} 0 600 0 0 {name=ms2
w=38.70u
l=0.13u
ng=15
m=1
model=sg13_lv_nmos
spiceprefix=X
}
N 20 570 20 570 {lab=a2}
C {devices/lab_pin.sym} 20 570 0 0 {name=p85 sig_type=std_logic lab=a2}
N -20 600 -20 600 {lab=g2}
C {devices/lab_pin.sym} -20 600 0 1 {name=p86 sig_type=std_logic lab=g2}
N 20 630 20 630 {lab=b2}
C {devices/lab_pin.sym} 20 630 0 0 {name=p87 sig_type=std_logic lab=b2}
N 20 600 20 600 {lab=gnd}
C {devices/lab_pin.sym} 20 600 0 0 {name=p88 sig_type=std_logic lab=gnd}
C {devices/res.sym} 220 600 0 0 {name=rba2
value=2000000.0
m=1
footprint=1206
device=resistor
sim_device=resistor
}
N 220 570 220 570 {lab=a2}
C {devices/lab_pin.sym} 220 570 0 0 {name=p89 sig_type=std_logic lab=a2}
N 220 630 220 630 {lab=bb2}
C {devices/lab_pin.sym} 220 630 0 0 {name=p90 sig_type=std_logic lab=bb2}
C {devices/res.sym} 440 600 0 0 {name=rbb2
value=2000000.0
m=1
footprint=1206
device=resistor
sim_device=resistor
}
N 440 570 440 570 {lab=b2}
C {devices/lab_pin.sym} 440 570 0 0 {name=p91 sig_type=std_logic lab=b2}
N 440 630 440 630 {lab=bb2}
C {devices/lab_pin.sym} 440 630 0 0 {name=p92 sig_type=std_logic lab=bb2}
C {sg13g2_pr/sg13_lv_nmos.sym} 660 600 0 0 {name=mbp_rba2
w=5u
l=0.13u
ng=2
m=1
model=sg13_lv_nmos
spiceprefix=X
}
N 680 570 680 570 {lab=a2}
C {devices/lab_pin.sym} 680 570 0 0 {name=p93 sig_type=std_logic lab=a2}
N 640 600 640 600 {lab=vbp}
C {devices/lab_pin.sym} 640 600 0 1 {name=p94 sig_type=std_logic lab=vbp}
N 680 630 680 630 {lab=bb2}
C {devices/lab_pin.sym} 680 630 0 0 {name=p95 sig_type=std_logic lab=bb2}
N 680 600 680 600 {lab=gnd}
C {devices/lab_pin.sym} 680 600 0 0 {name=p96 sig_type=std_logic lab=gnd}
C {sg13g2_pr/sg13_lv_nmos.sym} 880 600 0 0 {name=mbp_rbb2
w=5u
l=0.13u
ng=2
m=1
model=sg13_lv_nmos
spiceprefix=X
}
N 900 570 900 570 {lab=b2}
C {devices/lab_pin.sym} 900 570 0 0 {name=p97 sig_type=std_logic lab=b2}
N 860 600 860 600 {lab=vbp}
C {devices/lab_pin.sym} 860 600 0 1 {name=p98 sig_type=std_logic lab=vbp}
N 900 630 900 630 {lab=bb2}
C {devices/lab_pin.sym} 900 630 0 0 {name=p99 sig_type=std_logic lab=bb2}
N 900 600 900 600 {lab=gnd}
C {devices/lab_pin.sym} 900 600 0 0 {name=p100 sig_type=std_logic lab=gnd}
C {sg13g2_pr/cap_rfcmim.sym} 1100 600 0 0 {name=xb3p
model=cap_rfcmim
lvs_model=rfcmim
w=7.841000e-06
l=7.841000e-06
wfeed=5.0e-6
m=1
mm_ok=1
spiceprefix=X
}
N 1100 570 1100 570 {lab=tp}
C {devices/lab_pin.sym} 1100 570 0 0 {name=p101 sig_type=std_logic lab=tp}
N 1100 630 1100 630 {lab=a3}
C {devices/lab_pin.sym} 1100 630 0 0 {name=p102 sig_type=std_logic lab=a3}
N 1070 600 1070 600 {lab=gnd}
C {devices/lab_pin.sym} 1070 600 0 0 {name=p103 sig_type=std_logic lab=gnd}
C {sg13g2_pr/cap_rfcmim.sym} 0 720 0 0 {name=xb3n
model=cap_rfcmim
lvs_model=rfcmim
w=7.841000e-06
l=7.841000e-06
wfeed=5.0e-6
m=1
mm_ok=1
spiceprefix=X
}
N 0 690 0 690 {lab=tn}
C {devices/lab_pin.sym} 0 690 0 0 {name=p104 sig_type=std_logic lab=tn}
N 0 750 0 750 {lab=b3}
C {devices/lab_pin.sym} 0 750 0 0 {name=p105 sig_type=std_logic lab=b3}
N -30 720 -30 720 {lab=gnd}
C {devices/lab_pin.sym} -30 720 0 0 {name=p106 sig_type=std_logic lab=gnd}
C {sg13g2_pr/sg13_lv_nmos.sym} 220 720 0 0 {name=ms3
w=76.85u
l=0.13u
ng=31
m=1
model=sg13_lv_nmos
spiceprefix=X
}
N 240 690 240 690 {lab=a3}
C {devices/lab_pin.sym} 240 690 0 0 {name=p107 sig_type=std_logic lab=a3}
N 200 720 200 720 {lab=g3}
C {devices/lab_pin.sym} 200 720 0 1 {name=p108 sig_type=std_logic lab=g3}
N 240 750 240 750 {lab=b3}
C {devices/lab_pin.sym} 240 750 0 0 {name=p109 sig_type=std_logic lab=b3}
N 240 720 240 720 {lab=gnd}
C {devices/lab_pin.sym} 240 720 0 0 {name=p110 sig_type=std_logic lab=gnd}
C {devices/res.sym} 440 720 0 0 {name=rba3
value=2000000.0
m=1
footprint=1206
device=resistor
sim_device=resistor
}
N 440 690 440 690 {lab=a3}
C {devices/lab_pin.sym} 440 690 0 0 {name=p111 sig_type=std_logic lab=a3}
N 440 750 440 750 {lab=bb3}
C {devices/lab_pin.sym} 440 750 0 0 {name=p112 sig_type=std_logic lab=bb3}
C {devices/res.sym} 660 720 0 0 {name=rbb3
value=2000000.0
m=1
footprint=1206
device=resistor
sim_device=resistor
}
N 660 690 660 690 {lab=b3}
C {devices/lab_pin.sym} 660 690 0 0 {name=p113 sig_type=std_logic lab=b3}
N 660 750 660 750 {lab=bb3}
C {devices/lab_pin.sym} 660 750 0 0 {name=p114 sig_type=std_logic lab=bb3}
C {sg13g2_pr/sg13_lv_nmos.sym} 880 720 0 0 {name=mbp_rba3
w=5u
l=0.13u
ng=2
m=1
model=sg13_lv_nmos
spiceprefix=X
}
N 900 690 900 690 {lab=a3}
C {devices/lab_pin.sym} 900 690 0 0 {name=p115 sig_type=std_logic lab=a3}
N 860 720 860 720 {lab=vbp}
C {devices/lab_pin.sym} 860 720 0 1 {name=p116 sig_type=std_logic lab=vbp}
N 900 750 900 750 {lab=bb3}
C {devices/lab_pin.sym} 900 750 0 0 {name=p117 sig_type=std_logic lab=bb3}
N 900 720 900 720 {lab=gnd}
C {devices/lab_pin.sym} 900 720 0 0 {name=p118 sig_type=std_logic lab=gnd}
C {sg13g2_pr/sg13_lv_nmos.sym} 1100 720 0 0 {name=mbp_rbb3
w=5u
l=0.13u
ng=2
m=1
model=sg13_lv_nmos
spiceprefix=X
}
N 1120 690 1120 690 {lab=b3}
C {devices/lab_pin.sym} 1120 690 0 0 {name=p119 sig_type=std_logic lab=b3}
N 1080 720 1080 720 {lab=vbp}
C {devices/lab_pin.sym} 1080 720 0 1 {name=p120 sig_type=std_logic lab=vbp}
N 1120 750 1120 750 {lab=bb3}
C {devices/lab_pin.sym} 1120 750 0 0 {name=p121 sig_type=std_logic lab=bb3}
N 1120 720 1120 720 {lab=gnd}
C {devices/lab_pin.sym} 1120 720 0 0 {name=p122 sig_type=std_logic lab=gnd}
C {sg13g2_pr/cap_rfcmim.sym} 0 840 0 0 {name=xb4p
model=cap_rfcmim
lvs_model=rfcmim
w=1.107500e-05
l=1.107500e-05
wfeed=5.0e-6
m=1
mm_ok=1
spiceprefix=X
}
N 0 810 0 810 {lab=tp}
C {devices/lab_pin.sym} 0 810 0 0 {name=p123 sig_type=std_logic lab=tp}
N 0 870 0 870 {lab=a4}
C {devices/lab_pin.sym} 0 870 0 0 {name=p124 sig_type=std_logic lab=a4}
N -30 840 -30 840 {lab=gnd}
C {devices/lab_pin.sym} -30 840 0 0 {name=p125 sig_type=std_logic lab=gnd}
C {sg13g2_pr/cap_rfcmim.sym} 220 840 0 0 {name=xb4n
model=cap_rfcmim
lvs_model=rfcmim
w=1.107500e-05
l=1.107500e-05
wfeed=5.0e-6
m=1
mm_ok=1
spiceprefix=X
}
N 220 810 220 810 {lab=tn}
C {devices/lab_pin.sym} 220 810 0 0 {name=p126 sig_type=std_logic lab=tn}
N 220 870 220 870 {lab=b4}
C {devices/lab_pin.sym} 220 870 0 0 {name=p127 sig_type=std_logic lab=b4}
N 190 840 190 840 {lab=gnd}
C {devices/lab_pin.sym} 190 840 0 0 {name=p128 sig_type=std_logic lab=gnd}
C {sg13g2_pr/sg13_lv_nmos.sym} 440 840 0 0 {name=ms4
w=153.32u
l=0.13u
ng=61
m=1
model=sg13_lv_nmos
spiceprefix=X
}
N 460 810 460 810 {lab=a4}
C {devices/lab_pin.sym} 460 810 0 0 {name=p129 sig_type=std_logic lab=a4}
N 420 840 420 840 {lab=g4}
C {devices/lab_pin.sym} 420 840 0 1 {name=p130 sig_type=std_logic lab=g4}
N 460 870 460 870 {lab=b4}
C {devices/lab_pin.sym} 460 870 0 0 {name=p131 sig_type=std_logic lab=b4}
N 460 840 460 840 {lab=gnd}
C {devices/lab_pin.sym} 460 840 0 0 {name=p132 sig_type=std_logic lab=gnd}
C {devices/res.sym} 660 840 0 0 {name=rba4
value=2000000.0
m=1
footprint=1206
device=resistor
sim_device=resistor
}
N 660 810 660 810 {lab=a4}
C {devices/lab_pin.sym} 660 810 0 0 {name=p133 sig_type=std_logic lab=a4}
N 660 870 660 870 {lab=bb4}
C {devices/lab_pin.sym} 660 870 0 0 {name=p134 sig_type=std_logic lab=bb4}
C {devices/res.sym} 880 840 0 0 {name=rbb4
value=2000000.0
m=1
footprint=1206
device=resistor
sim_device=resistor
}
N 880 810 880 810 {lab=b4}
C {devices/lab_pin.sym} 880 810 0 0 {name=p135 sig_type=std_logic lab=b4}
N 880 870 880 870 {lab=bb4}
C {devices/lab_pin.sym} 880 870 0 0 {name=p136 sig_type=std_logic lab=bb4}
C {sg13g2_pr/sg13_lv_nmos.sym} 1100 840 0 0 {name=mbp_rba4
w=5u
l=0.13u
ng=2
m=1
model=sg13_lv_nmos
spiceprefix=X
}
N 1120 810 1120 810 {lab=a4}
C {devices/lab_pin.sym} 1120 810 0 0 {name=p137 sig_type=std_logic lab=a4}
N 1080 840 1080 840 {lab=vbp}
C {devices/lab_pin.sym} 1080 840 0 1 {name=p138 sig_type=std_logic lab=vbp}
N 1120 870 1120 870 {lab=bb4}
C {devices/lab_pin.sym} 1120 870 0 0 {name=p139 sig_type=std_logic lab=bb4}
N 1120 840 1120 840 {lab=gnd}
C {devices/lab_pin.sym} 1120 840 0 0 {name=p140 sig_type=std_logic lab=gnd}
C {sg13g2_pr/sg13_lv_nmos.sym} 0 960 0 0 {name=mbp_rbb4
w=5u
l=0.13u
ng=2
m=1
model=sg13_lv_nmos
spiceprefix=X
}
N 20 930 20 930 {lab=b4}
C {devices/lab_pin.sym} 20 930 0 0 {name=p141 sig_type=std_logic lab=b4}
N -20 960 -20 960 {lab=vbp}
C {devices/lab_pin.sym} -20 960 0 1 {name=p142 sig_type=std_logic lab=vbp}
N 20 990 20 990 {lab=bb4}
C {devices/lab_pin.sym} 20 990 0 0 {name=p143 sig_type=std_logic lab=bb4}
N 20 960 20 960 {lab=gnd}
C {devices/lab_pin.sym} 20 960 0 0 {name=p144 sig_type=std_logic lab=gnd}
C {sg13g2_pr/cap_rfcmim.sym} 220 960 0 0 {name=xb5p
model=cap_rfcmim
lvs_model=rfcmim
w=1.565200e-05
l=1.565200e-05
wfeed=5.0e-6
m=1
mm_ok=1
spiceprefix=X
}
N 220 930 220 930 {lab=tp}
C {devices/lab_pin.sym} 220 930 0 0 {name=p145 sig_type=std_logic lab=tp}
N 220 990 220 990 {lab=a5}
C {devices/lab_pin.sym} 220 990 0 0 {name=p146 sig_type=std_logic lab=a5}
N 190 960 190 960 {lab=gnd}
C {devices/lab_pin.sym} 190 960 0 0 {name=p147 sig_type=std_logic lab=gnd}
C {sg13g2_pr/cap_rfcmim.sym} 440 960 0 0 {name=xb5n
model=cap_rfcmim
lvs_model=rfcmim
w=1.565200e-05
l=1.565200e-05
wfeed=5.0e-6
m=1
mm_ok=1
spiceprefix=X
}
N 440 930 440 930 {lab=tn}
C {devices/lab_pin.sym} 440 930 0 0 {name=p148 sig_type=std_logic lab=tn}
N 440 990 440 990 {lab=b5}
C {devices/lab_pin.sym} 440 990 0 0 {name=p149 sig_type=std_logic lab=b5}
N 410 960 410 960 {lab=gnd}
C {devices/lab_pin.sym} 410 960 0 0 {name=p150 sig_type=std_logic lab=gnd}
C {sg13g2_pr/sg13_lv_nmos.sym} 660 960 0 0 {name=ms5
w=306.21u
l=0.13u
ng=122
m=1
model=sg13_lv_nmos
spiceprefix=X
}
N 680 930 680 930 {lab=a5}
C {devices/lab_pin.sym} 680 930 0 0 {name=p151 sig_type=std_logic lab=a5}
N 640 960 640 960 {lab=g5}
C {devices/lab_pin.sym} 640 960 0 1 {name=p152 sig_type=std_logic lab=g5}
N 680 990 680 990 {lab=b5}
C {devices/lab_pin.sym} 680 990 0 0 {name=p153 sig_type=std_logic lab=b5}
N 680 960 680 960 {lab=gnd}
C {devices/lab_pin.sym} 680 960 0 0 {name=p154 sig_type=std_logic lab=gnd}
C {devices/res.sym} 880 960 0 0 {name=rba5
value=2000000.0
m=1
footprint=1206
device=resistor
sim_device=resistor
}
N 880 930 880 930 {lab=a5}
C {devices/lab_pin.sym} 880 930 0 0 {name=p155 sig_type=std_logic lab=a5}
N 880 990 880 990 {lab=bb5}
C {devices/lab_pin.sym} 880 990 0 0 {name=p156 sig_type=std_logic lab=bb5}
C {devices/res.sym} 1100 960 0 0 {name=rbb5
value=2000000.0
m=1
footprint=1206
device=resistor
sim_device=resistor
}
N 1100 930 1100 930 {lab=b5}
C {devices/lab_pin.sym} 1100 930 0 0 {name=p157 sig_type=std_logic lab=b5}
N 1100 990 1100 990 {lab=bb5}
C {devices/lab_pin.sym} 1100 990 0 0 {name=p158 sig_type=std_logic lab=bb5}
C {sg13g2_pr/sg13_lv_nmos.sym} 0 1080 0 0 {name=mbp_rba5
w=5u
l=0.13u
ng=2
m=1
model=sg13_lv_nmos
spiceprefix=X
}
N 20 1050 20 1050 {lab=a5}
C {devices/lab_pin.sym} 20 1050 0 0 {name=p159 sig_type=std_logic lab=a5}
N -20 1080 -20 1080 {lab=vbp}
C {devices/lab_pin.sym} -20 1080 0 1 {name=p160 sig_type=std_logic lab=vbp}
N 20 1110 20 1110 {lab=bb5}
C {devices/lab_pin.sym} 20 1110 0 0 {name=p161 sig_type=std_logic lab=bb5}
N 20 1080 20 1080 {lab=gnd}
C {devices/lab_pin.sym} 20 1080 0 0 {name=p162 sig_type=std_logic lab=gnd}
C {sg13g2_pr/sg13_lv_nmos.sym} 220 1080 0 0 {name=mbp_rbb5
w=5u
l=0.13u
ng=2
m=1
model=sg13_lv_nmos
spiceprefix=X
}
N 240 1050 240 1050 {lab=b5}
C {devices/lab_pin.sym} 240 1050 0 0 {name=p163 sig_type=std_logic lab=b5}
N 200 1080 200 1080 {lab=vbp}
C {devices/lab_pin.sym} 200 1080 0 1 {name=p164 sig_type=std_logic lab=vbp}
N 240 1110 240 1110 {lab=bb5}
C {devices/lab_pin.sym} 240 1110 0 0 {name=p165 sig_type=std_logic lab=bb5}
N 240 1080 240 1080 {lab=gnd}
C {devices/lab_pin.sym} 240 1080 0 0 {name=p166 sig_type=std_logic lab=gnd}
C {sg13g2_pr/cap_rfcmim.sym} 440 1080 0 0 {name=xb6p
model=cap_rfcmim
lvs_model=rfcmim
w=2.208500e-05
l=2.208500e-05
wfeed=5.0e-6
m=1
mm_ok=1
spiceprefix=X
}
N 440 1050 440 1050 {lab=tp}
C {devices/lab_pin.sym} 440 1050 0 0 {name=p167 sig_type=std_logic lab=tp}
N 440 1110 440 1110 {lab=a6}
C {devices/lab_pin.sym} 440 1110 0 0 {name=p168 sig_type=std_logic lab=a6}
N 410 1080 410 1080 {lab=gnd}
C {devices/lab_pin.sym} 410 1080 0 0 {name=p169 sig_type=std_logic lab=gnd}
C {sg13g2_pr/cap_rfcmim.sym} 660 1080 0 0 {name=xb6n
model=cap_rfcmim
lvs_model=rfcmim
w=2.208500e-05
l=2.208500e-05
wfeed=5.0e-6
m=1
mm_ok=1
spiceprefix=X
}
N 660 1050 660 1050 {lab=tn}
C {devices/lab_pin.sym} 660 1050 0 0 {name=p170 sig_type=std_logic lab=tn}
N 660 1110 660 1110 {lab=b6}
C {devices/lab_pin.sym} 660 1110 0 0 {name=p171 sig_type=std_logic lab=b6}
N 630 1080 630 1080 {lab=gnd}
C {devices/lab_pin.sym} 630 1080 0 0 {name=p172 sig_type=std_logic lab=gnd}
C {sg13g2_pr/sg13_lv_nmos.sym} 880 1080 0 0 {name=ms6
w=609.70u
l=0.13u
ng=244
m=1
model=sg13_lv_nmos
spiceprefix=X
}
N 900 1050 900 1050 {lab=a6}
C {devices/lab_pin.sym} 900 1050 0 0 {name=p173 sig_type=std_logic lab=a6}
N 860 1080 860 1080 {lab=g6}
C {devices/lab_pin.sym} 860 1080 0 1 {name=p174 sig_type=std_logic lab=g6}
N 900 1110 900 1110 {lab=b6}
C {devices/lab_pin.sym} 900 1110 0 0 {name=p175 sig_type=std_logic lab=b6}
N 900 1080 900 1080 {lab=gnd}
C {devices/lab_pin.sym} 900 1080 0 0 {name=p176 sig_type=std_logic lab=gnd}
C {devices/res.sym} 1100 1080 0 0 {name=rba6
value=2000000.0
m=1
footprint=1206
device=resistor
sim_device=resistor
}
N 1100 1050 1100 1050 {lab=a6}
C {devices/lab_pin.sym} 1100 1050 0 0 {name=p177 sig_type=std_logic lab=a6}
N 1100 1110 1100 1110 {lab=bb6}
C {devices/lab_pin.sym} 1100 1110 0 0 {name=p178 sig_type=std_logic lab=bb6}
C {devices/res.sym} 0 1200 0 0 {name=rbb6
value=2000000.0
m=1
footprint=1206
device=resistor
sim_device=resistor
}
N 0 1170 0 1170 {lab=b6}
C {devices/lab_pin.sym} 0 1170 0 0 {name=p179 sig_type=std_logic lab=b6}
N 0 1230 0 1230 {lab=bb6}
C {devices/lab_pin.sym} 0 1230 0 0 {name=p180 sig_type=std_logic lab=bb6}
C {sg13g2_pr/sg13_lv_nmos.sym} 220 1200 0 0 {name=mbp_rba6
w=5u
l=0.13u
ng=2
m=1
model=sg13_lv_nmos
spiceprefix=X
}
N 240 1170 240 1170 {lab=a6}
C {devices/lab_pin.sym} 240 1170 0 0 {name=p181 sig_type=std_logic lab=a6}
N 200 1200 200 1200 {lab=vbp}
C {devices/lab_pin.sym} 200 1200 0 1 {name=p182 sig_type=std_logic lab=vbp}
N 240 1230 240 1230 {lab=bb6}
C {devices/lab_pin.sym} 240 1230 0 0 {name=p183 sig_type=std_logic lab=bb6}
N 240 1200 240 1200 {lab=gnd}
C {devices/lab_pin.sym} 240 1200 0 0 {name=p184 sig_type=std_logic lab=gnd}
C {sg13g2_pr/sg13_lv_nmos.sym} 440 1200 0 0 {name=mbp_rbb6
w=5u
l=0.13u
ng=2
m=1
model=sg13_lv_nmos
spiceprefix=X
}
N 460 1170 460 1170 {lab=b6}
C {devices/lab_pin.sym} 460 1170 0 0 {name=p185 sig_type=std_logic lab=b6}
N 420 1200 420 1200 {lab=vbp}
C {devices/lab_pin.sym} 420 1200 0 1 {name=p186 sig_type=std_logic lab=vbp}
N 460 1230 460 1230 {lab=bb6}
C {devices/lab_pin.sym} 460 1230 0 0 {name=p187 sig_type=std_logic lab=bb6}
N 460 1200 460 1200 {lab=gnd}
C {devices/lab_pin.sym} 460 1200 0 0 {name=p188 sig_type=std_logic lab=gnd}
C {sg13g2_pr/cap_rfcmim.sym} 660 1200 0 0 {name=xb7p
model=cap_rfcmim
lvs_model=rfcmim
w=3.107700e-05
l=3.107700e-05
wfeed=5.0e-6
m=1
mm_ok=1
spiceprefix=X
}
N 660 1170 660 1170 {lab=tp}
C {devices/lab_pin.sym} 660 1170 0 0 {name=p189 sig_type=std_logic lab=tp}
N 660 1230 660 1230 {lab=a7}
C {devices/lab_pin.sym} 660 1230 0 0 {name=p190 sig_type=std_logic lab=a7}
N 630 1200 630 1200 {lab=gnd}
C {devices/lab_pin.sym} 630 1200 0 0 {name=p191 sig_type=std_logic lab=gnd}
C {sg13g2_pr/cap_rfcmim.sym} 880 1200 0 0 {name=xb7n
model=cap_rfcmim
lvs_model=rfcmim
w=3.107700e-05
l=3.107700e-05
wfeed=5.0e-6
m=1
mm_ok=1
spiceprefix=X
}
N 880 1170 880 1170 {lab=tn}
C {devices/lab_pin.sym} 880 1170 0 0 {name=p192 sig_type=std_logic lab=tn}
N 880 1230 880 1230 {lab=b7}
C {devices/lab_pin.sym} 880 1230 0 0 {name=p193 sig_type=std_logic lab=b7}
N 850 1200 850 1200 {lab=gnd}
C {devices/lab_pin.sym} 850 1200 0 0 {name=p194 sig_type=std_logic lab=gnd}
C {sg13g2_pr/sg13_lv_nmos.sym} 1100 1200 0 0 {name=ms7
w=1207.23u
l=0.13u
ng=483
m=1
model=sg13_lv_nmos
spiceprefix=X
}
N 1120 1170 1120 1170 {lab=a7}
C {devices/lab_pin.sym} 1120 1170 0 0 {name=p195 sig_type=std_logic lab=a7}
N 1080 1200 1080 1200 {lab=g7}
C {devices/lab_pin.sym} 1080 1200 0 1 {name=p196 sig_type=std_logic lab=g7}
N 1120 1230 1120 1230 {lab=b7}
C {devices/lab_pin.sym} 1120 1230 0 0 {name=p197 sig_type=std_logic lab=b7}
N 1120 1200 1120 1200 {lab=gnd}
C {devices/lab_pin.sym} 1120 1200 0 0 {name=p198 sig_type=std_logic lab=gnd}
C {devices/res.sym} 0 1320 0 0 {name=rba7
value=2000000.0
m=1
footprint=1206
device=resistor
sim_device=resistor
}
N 0 1290 0 1290 {lab=a7}
C {devices/lab_pin.sym} 0 1290 0 0 {name=p199 sig_type=std_logic lab=a7}
N 0 1350 0 1350 {lab=bb7}
C {devices/lab_pin.sym} 0 1350 0 0 {name=p200 sig_type=std_logic lab=bb7}
C {devices/res.sym} 220 1320 0 0 {name=rbb7
value=2000000.0
m=1
footprint=1206
device=resistor
sim_device=resistor
}
N 220 1290 220 1290 {lab=b7}
C {devices/lab_pin.sym} 220 1290 0 0 {name=p201 sig_type=std_logic lab=b7}
N 220 1350 220 1350 {lab=bb7}
C {devices/lab_pin.sym} 220 1350 0 0 {name=p202 sig_type=std_logic lab=bb7}
C {sg13g2_pr/sg13_lv_nmos.sym} 440 1320 0 0 {name=mbp_rba7
w=5u
l=0.13u
ng=2
m=1
model=sg13_lv_nmos
spiceprefix=X
}
N 460 1290 460 1290 {lab=a7}
C {devices/lab_pin.sym} 460 1290 0 0 {name=p203 sig_type=std_logic lab=a7}
N 420 1320 420 1320 {lab=vbp}
C {devices/lab_pin.sym} 420 1320 0 1 {name=p204 sig_type=std_logic lab=vbp}
N 460 1350 460 1350 {lab=bb7}
C {devices/lab_pin.sym} 460 1350 0 0 {name=p205 sig_type=std_logic lab=bb7}
N 460 1320 460 1320 {lab=gnd}
C {devices/lab_pin.sym} 460 1320 0 0 {name=p206 sig_type=std_logic lab=gnd}
C {sg13g2_pr/sg13_lv_nmos.sym} 660 1320 0 0 {name=mbp_rbb7
w=5u
l=0.13u
ng=2
m=1
model=sg13_lv_nmos
spiceprefix=X
}
N 680 1290 680 1290 {lab=b7}
C {devices/lab_pin.sym} 680 1290 0 0 {name=p207 sig_type=std_logic lab=b7}
N 640 1320 640 1320 {lab=vbp}
C {devices/lab_pin.sym} 640 1320 0 1 {name=p208 sig_type=std_logic lab=vbp}
N 680 1350 680 1350 {lab=bb7}
C {devices/lab_pin.sym} 680 1350 0 0 {name=p209 sig_type=std_logic lab=bb7}
N 680 1320 680 1320 {lab=gnd}
C {devices/lab_pin.sym} 680 1320 0 0 {name=p210 sig_type=std_logic lab=gnd}
C {sg13g2_pr/cap_rfcmim.sym} 880 1320 0 0 {name=xcp
model=cap_rfcmim
lvs_model=rfcmim
w=2.129200e-05
l=2.129200e-05
wfeed=5.0e-6
m=1
mm_ok=1
spiceprefix=X
}
N 880 1290 880 1290 {lab=tp}
C {devices/lab_pin.sym} 880 1290 0 0 {name=p211 sig_type=std_logic lab=tp}
N 880 1350 880 1350 {lab=vgp}
C {devices/lab_pin.sym} 880 1350 0 0 {name=p212 sig_type=std_logic lab=vgp}
N 850 1320 850 1320 {lab=gnd}
C {devices/lab_pin.sym} 850 1320 0 0 {name=p213 sig_type=std_logic lab=gnd}
C {sg13g2_pr/cap_rfcmim.sym} 1100 1320 0 0 {name=xcn
model=cap_rfcmim
lvs_model=rfcmim
w=2.129200e-05
l=2.129200e-05
wfeed=5.0e-6
m=1
mm_ok=1
spiceprefix=X
}
N 1100 1290 1100 1290 {lab=tn}
C {devices/lab_pin.sym} 1100 1290 0 0 {name=p214 sig_type=std_logic lab=tn}
N 1100 1350 1100 1350 {lab=vgn}
C {devices/lab_pin.sym} 1100 1350 0 0 {name=p215 sig_type=std_logic lab=vgn}
N 1070 1320 1070 1320 {lab=gnd}
C {devices/lab_pin.sym} 1070 1320 0 0 {name=p216 sig_type=std_logic lab=gnd}
C {devices/res.sym} 0 1440 0 0 {name=rvp
value=2000000.0
m=1
footprint=1206
device=resistor
sim_device=resistor
}
N 0 1410 0 1410 {lab=vgp}
C {devices/lab_pin.sym} 0 1410 0 0 {name=p217 sig_type=std_logic lab=vgp}
N 0 1470 0 1470 {lab=vvb}
C {devices/lab_pin.sym} 0 1470 0 0 {name=p218 sig_type=std_logic lab=vvb}
C {devices/res.sym} 220 1440 0 0 {name=rvn
value=2000000.0
m=1
footprint=1206
device=resistor
sim_device=resistor
}
N 220 1410 220 1410 {lab=vgn}
C {devices/lab_pin.sym} 220 1410 0 0 {name=p219 sig_type=std_logic lab=vgn}
N 220 1470 220 1470 {lab=vvb}
C {devices/lab_pin.sym} 220 1470 0 0 {name=p220 sig_type=std_logic lab=vvb}
C {devices/vsource.sym} 440 1440 0 0 {name=vvb value=0.3}
N 440 1410 440 1410 {lab=vvb}
C {devices/lab_pin.sym} 440 1410 0 0 {name=p221 sig_type=std_logic lab=vvb}
N 440 1470 440 1470 {lab=gnd}
C {devices/lab_pin.sym} 440 1470 0 0 {name=p222 sig_type=std_logic lab=gnd}
C {sg13g2_pr/sg13_svaricap.sym} 660 1440 0 0 {name=xv1
model=sg13_hv_svaricap_fx
W=3.740000e-06
L=3.000000e-07
Nx=10
spiceprefix=X
}
N 700 1440 700 1440 {lab=vgp}
C {devices/lab_pin.sym} 700 1440 0 0 {name=p223 sig_type=std_logic lab=vgp}
N 660 1410 660 1410 {lab=vt}
C {devices/lab_pin.sym} 660 1410 0 0 {name=p224 sig_type=std_logic lab=vt}
N 620 1440 620 1440 {lab=vgn}
C {devices/lab_pin.sym} 620 1440 0 0 {name=p225 sig_type=std_logic lab=vgn}
C {sg13g2_pr/sg13_svaricap.sym} 880 1440 0 0 {name=xv2
model=sg13_hv_svaricap_fx
W=3.740000e-06
L=3.000000e-07
Nx=10
spiceprefix=X
}
N 920 1440 920 1440 {lab=vgp}
C {devices/lab_pin.sym} 920 1440 0 0 {name=p226 sig_type=std_logic lab=vgp}
N 880 1410 880 1410 {lab=vt}
C {devices/lab_pin.sym} 880 1410 0 0 {name=p227 sig_type=std_logic lab=vt}
N 840 1440 840 1440 {lab=vgn}
C {devices/lab_pin.sym} 840 1440 0 0 {name=p228 sig_type=std_logic lab=vgn}
C {sg13g2_pr/sg13_lv_nmos.sym} 1100 1440 0 0 {name=mbp_rvp
w=5u
l=0.13u
ng=2
m=1
model=sg13_lv_nmos
spiceprefix=X
}
N 1120 1410 1120 1410 {lab=vgp}
C {devices/lab_pin.sym} 1120 1410 0 0 {name=p229 sig_type=std_logic lab=vgp}
N 1080 1440 1080 1440 {lab=vbp}
C {devices/lab_pin.sym} 1080 1440 0 1 {name=p230 sig_type=std_logic lab=vbp}
N 1120 1470 1120 1470 {lab=vvb}
C {devices/lab_pin.sym} 1120 1470 0 0 {name=p231 sig_type=std_logic lab=vvb}
N 1120 1440 1120 1440 {lab=gnd}
C {devices/lab_pin.sym} 1120 1440 0 0 {name=p232 sig_type=std_logic lab=gnd}
C {sg13g2_pr/sg13_lv_nmos.sym} 0 1560 0 0 {name=mbp_rvn
w=5u
l=0.13u
ng=2
m=1
model=sg13_lv_nmos
spiceprefix=X
}
N 20 1530 20 1530 {lab=vgn}
C {devices/lab_pin.sym} 20 1530 0 0 {name=p233 sig_type=std_logic lab=vgn}
N -20 1560 -20 1560 {lab=vbp}
C {devices/lab_pin.sym} -20 1560 0 1 {name=p234 sig_type=std_logic lab=vbp}
N 20 1590 20 1590 {lab=vvb}
C {devices/lab_pin.sym} 20 1590 0 0 {name=p235 sig_type=std_logic lab=vvb}
N 20 1560 20 1560 {lab=gnd}
C {devices/lab_pin.sym} 20 1560 0 0 {name=p236 sig_type=std_logic lab=gnd}
C {devices/capa.sym} 220 1560 0 0 {name=ctail
value=8e-12
m=1
footprint=1206
device=capacitor
sim_device=capacitor
}
N 220 1530 220 1530 {lab=tail}
C {devices/lab_pin.sym} 220 1530 0 0 {name=p237 sig_type=std_logic lab=tail}
N 220 1590 220 1590 {lab=gnd}
C {devices/lab_pin.sym} 220 1590 0 0 {name=p238 sig_type=std_logic lab=gnd}
C {sg13g2_pr/sg13_lv_nmos.sym} 440 1560 0 0 {name=mt
w=160u
l=4u
ng=32
m=1
model=sg13_lv_nmos
spiceprefix=X
}
N 460 1530 460 1530 {lab=tail}
C {devices/lab_pin.sym} 460 1530 0 0 {name=p239 sig_type=std_logic lab=tail}
N 420 1560 420 1560 {lab=nbf}
C {devices/lab_pin.sym} 420 1560 0 1 {name=p240 sig_type=std_logic lab=nbf}
N 460 1590 460 1590 {lab=gnd}
C {devices/lab_pin.sym} 460 1590 0 0 {name=p241 sig_type=std_logic lab=gnd}
N 460 1560 460 1560 {lab=gnd}
C {devices/lab_pin.sym} 460 1560 0 0 {name=p242 sig_type=std_logic lab=gnd}
C {devices/res.sym} 660 1560 0 0 {name=rbf
value=1000000.0
m=1
footprint=1206
device=resistor
sim_device=resistor
}
N 660 1530 660 1530 {lab=nb}
C {devices/lab_pin.sym} 660 1530 0 0 {name=p243 sig_type=std_logic lab=nb}
N 660 1590 660 1590 {lab=nbf}
C {devices/lab_pin.sym} 660 1590 0 0 {name=p244 sig_type=std_logic lab=nbf}
C {devices/capa.sym} 880 1560 0 0 {name=cbf
value=5e-11
m=1
footprint=1206
device=capacitor
sim_device=capacitor
}
N 880 1530 880 1530 {lab=nbf}
C {devices/lab_pin.sym} 880 1530 0 0 {name=p245 sig_type=std_logic lab=nbf}
N 880 1590 880 1590 {lab=gnd}
C {devices/lab_pin.sym} 880 1590 0 0 {name=p246 sig_type=std_logic lab=gnd}
C {sg13g2_pr/sg13_lv_nmos.sym} 1100 1560 0 0 {name=mr
w=20u
l=4u
ng=4
m=1
model=sg13_lv_nmos
spiceprefix=X
}
N 1120 1530 1120 1530 {lab=nb}
C {devices/lab_pin.sym} 1120 1530 0 0 {name=p247 sig_type=std_logic lab=nb}
N 1080 1560 1080 1560 {lab=nb}
C {devices/lab_pin.sym} 1080 1560 0 1 {name=p248 sig_type=std_logic lab=nb}
N 1120 1590 1120 1590 {lab=gnd}
C {devices/lab_pin.sym} 1120 1590 0 0 {name=p249 sig_type=std_logic lab=gnd}
N 1120 1560 1120 1560 {lab=gnd}
C {devices/lab_pin.sym} 1120 1560 0 0 {name=p250 sig_type=std_logic lab=gnd}
C {devices/isource.sym} 0 1680 0 0 {name=iref value=0.0005}
N 0 1650 0 1650 {lab=vdd}
C {devices/lab_pin.sym} 0 1650 0 0 {name=p251 sig_type=std_logic lab=vdd}
N 0 1710 0 1710 {lab=nb}
C {devices/lab_pin.sym} 0 1710 0 0 {name=p252 sig_type=std_logic lab=nb}
C {sg13g2_pr/sg13_lv_nmos.sym} 220 1680 0 0 {name=mbp_rbf
w=20u
l=0.13u
ng=4
m=1
model=sg13_lv_nmos
spiceprefix=X
}
N 240 1650 240 1650 {lab=nb}
C {devices/lab_pin.sym} 240 1650 0 0 {name=p253 sig_type=std_logic lab=nb}
N 200 1680 200 1680 {lab=vbp_tail}
C {devices/lab_pin.sym} 200 1680 0 1 {name=p254 sig_type=std_logic lab=vbp_tail}
N 240 1710 240 1710 {lab=nbf}
C {devices/lab_pin.sym} 240 1710 0 0 {name=p255 sig_type=std_logic lab=nbf}
N 240 1680 240 1680 {lab=gnd}
C {devices/lab_pin.sym} 240 1680 0 0 {name=p256 sig_type=std_logic lab=gnd}
C {sg13g2_pr/sg13_lv_nmos.sym} 440 1680 0 0 {name=mb1
w=10u
l=0.13u
ng=4
m=1
model=sg13_lv_nmos
spiceprefix=X
}
N 460 1650 460 1650 {lab=op}
C {devices/lab_pin.sym} 460 1650 0 0 {name=p257 sig_type=std_logic lab=op}
N 420 1680 420 1680 {lab=tp}
C {devices/lab_pin.sym} 420 1680 0 1 {name=p258 sig_type=std_logic lab=tp}
N 460 1710 460 1710 {lab=tb}
C {devices/lab_pin.sym} 460 1710 0 0 {name=p259 sig_type=std_logic lab=tb}
N 460 1680 460 1680 {lab=gnd}
C {devices/lab_pin.sym} 460 1680 0 0 {name=p260 sig_type=std_logic lab=gnd}
C {sg13g2_pr/sg13_lv_nmos.sym} 660 1680 0 0 {name=mb2
w=10u
l=0.13u
ng=4
m=1
model=sg13_lv_nmos
spiceprefix=X
}
N 680 1650 680 1650 {lab=on}
C {devices/lab_pin.sym} 680 1650 0 0 {name=p261 sig_type=std_logic lab=on}
N 640 1680 640 1680 {lab=tn}
C {devices/lab_pin.sym} 640 1680 0 1 {name=p262 sig_type=std_logic lab=tn}
N 680 1710 680 1710 {lab=tb}
C {devices/lab_pin.sym} 680 1710 0 0 {name=p263 sig_type=std_logic lab=tb}
N 680 1680 680 1680 {lab=gnd}
C {devices/lab_pin.sym} 680 1680 0 0 {name=p264 sig_type=std_logic lab=gnd}
C {devices/res.sym} 880 1680 0 0 {name=rl1
value=400
m=1
footprint=1206
device=resistor
sim_device=resistor
}
N 880 1650 880 1650 {lab=vdd}
C {devices/lab_pin.sym} 880 1650 0 0 {name=p265 sig_type=std_logic lab=vdd}
N 880 1710 880 1710 {lab=op}
C {devices/lab_pin.sym} 880 1710 0 0 {name=p266 sig_type=std_logic lab=op}
C {devices/res.sym} 1100 1680 0 0 {name=rl2
value=400
m=1
footprint=1206
device=resistor
sim_device=resistor
}
N 1100 1650 1100 1650 {lab=vdd}
C {devices/lab_pin.sym} 1100 1650 0 0 {name=p267 sig_type=std_logic lab=vdd}
N 1100 1710 1100 1710 {lab=on}
C {devices/lab_pin.sym} 1100 1710 0 0 {name=p268 sig_type=std_logic lab=on}
C {devices/isource.sym} 0 1800 0 0 {name=ib value=0.001}
N 0 1770 0 1770 {lab=tb}
C {devices/lab_pin.sym} 0 1770 0 0 {name=p269 sig_type=std_logic lab=tb}
N 0 1830 0 1830 {lab=gnd}
C {devices/lab_pin.sym} 0 1830 0 0 {name=p270 sig_type=std_logic lab=gnd}
C {devices/capa.sym} 220 1800 0 0 {name=ctb
value=2e-12
m=1
footprint=1206
device=capacitor
sim_device=capacitor
}
N 220 1770 220 1770 {lab=tb}
C {devices/lab_pin.sym} 220 1770 0 0 {name=p271 sig_type=std_logic lab=tb}
N 220 1830 220 1830 {lab=gnd}
C {devices/lab_pin.sym} 220 1830 0 0 {name=p272 sig_type=std_logic lab=gnd}
C {devices/capa.sym} 440 1800 0 0 {name=cl1
value=2e-14
m=1
footprint=1206
device=capacitor
sim_device=capacitor
}
N 440 1770 440 1770 {lab=op}
C {devices/lab_pin.sym} 440 1770 0 0 {name=p273 sig_type=std_logic lab=op}
N 440 1830 440 1830 {lab=gnd}
C {devices/lab_pin.sym} 440 1830 0 0 {name=p274 sig_type=std_logic lab=gnd}
C {devices/capa.sym} 660 1800 0 0 {name=cl2
value=2e-14
m=1
footprint=1206
device=capacitor
sim_device=capacitor
}
N 660 1770 660 1770 {lab=on}
C {devices/lab_pin.sym} 660 1770 0 0 {name=p275 sig_type=std_logic lab=on}
N 660 1830 660 1830 {lab=gnd}
C {devices/lab_pin.sym} 660 1830 0 0 {name=p276 sig_type=std_logic lab=gnd}
