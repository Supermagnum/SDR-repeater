v {xschem version=3.4.7 file_version=1.2}
G {}
K {}
V {}
S {}
E {}
C {devices/iopin.sym} -200 -40 0 0 {name=tail lab=tail}
C {devices/iopin.sym} -200 -80 0 0 {name=vdd lab=vdd}
C {devices/iopin.sym} -200 -120 0 0 {name=gnd lab=gnd}
C {devices/iopin.sym} -200 -160 0 0 {name=vbp_tail lab=vbp_tail}
C {devices/iopin.sym} -200 -200 0 0 {name=nb lab=nb}
C {devices/iopin.sym} -200 -240 0 0 {name=nbf lab=nbf}
C {devices/iopin.sym} -200 -280 0 0 {name=code0 lab=code0}
C {devices/iopin.sym} -200 -320 0 0 {name=code1 lab=code1}
C {devices/iopin.sym} -200 -360 0 0 {name=code2 lab=code2}
C {devices/iopin.sym} -200 -400 0 0 {name=code3 lab=code3}
C {devices/iopin.sym} -200 -440 0 0 {name=code4 lab=code4}
C {devices/title.sym} 0 40 0 0 {name=t1 author="HT13G-M P2.7.1"}
C {devices/lab_pin.sym} 200 40 0 0 {name=ttitle lab=vco_tail_dac_D22}
C {devices/isource.sym} 0 0 0 0 {name=imaster value=1.05e-05}
N 0 -30 0 -30 {lab=pbias}
C {devices/lab_pin.sym} 0 -30 0 0 {name=p1 sig_type=std_logic lab=pbias}
N 0 30 0 30 {lab=gnd}
C {devices/lab_pin.sym} 0 30 0 0 {name=p2 sig_type=std_logic lab=gnd}
C {sg13g2_pr/sg13_lv_pmos.sym} 220 0 0 0 {name=mm0
w=2u
l=2u
ng=1
m=1
model=sg13_lv_pmos
spiceprefix=X
}
N 240 30 240 30 {lab=pbias}
C {devices/lab_pin.sym} 240 30 0 0 {name=p3 sig_type=std_logic lab=pbias}
N 200 0 200 0 {lab=pbias}
C {devices/lab_pin.sym} 200 0 0 1 {name=p4 sig_type=std_logic lab=pbias}
N 240 -30 240 -30 {lab=vdd}
C {devices/lab_pin.sym} 240 -30 0 0 {name=p5 sig_type=std_logic lab=vdd}
N 240 0 240 0 {lab=vdd}
C {devices/lab_pin.sym} 240 0 0 0 {name=p6 sig_type=std_logic lab=vdd}
C {sg13g2_pr/sg13_lv_pmos.sym} 440 0 0 0 {name=moff
w=38u
l=2u
ng=19
m=1
model=sg13_lv_pmos
spiceprefix=X
}
N 460 30 460 30 {lab=xoff}
C {devices/lab_pin.sym} 460 30 0 0 {name=p7 sig_type=std_logic lab=xoff}
N 420 0 420 0 {lab=pbias}
C {devices/lab_pin.sym} 420 0 0 1 {name=p8 sig_type=std_logic lab=pbias}
N 460 -30 460 -30 {lab=vdd}
C {devices/lab_pin.sym} 460 -30 0 0 {name=p9 sig_type=std_logic lab=vdd}
N 460 0 460 0 {lab=vdd}
C {devices/lab_pin.sym} 460 0 0 0 {name=p10 sig_type=std_logic lab=vdd}
C {sg13g2_pr/sg13_lv_pmos.sym} 660 0 0 0 {name=msoff
w=38u
l=0.13u
ng=1
m=1
model=sg13_lv_pmos
spiceprefix=X
}
N 680 30 680 30 {lab=xraw}
C {devices/lab_pin.sym} 680 30 0 0 {name=p11 sig_type=std_logic lab=xraw}
N 640 0 640 0 {lab=gnd}
C {devices/lab_pin.sym} 640 0 0 1 {name=p12 sig_type=std_logic lab=gnd}
N 680 -30 680 -30 {lab=xoff}
C {devices/lab_pin.sym} 680 -30 0 0 {name=p13 sig_type=std_logic lab=xoff}
N 680 0 680 0 {lab=vdd}
C {devices/lab_pin.sym} 680 0 0 0 {name=p14 sig_type=std_logic lab=vdd}
C {sg13g2_pr/sg13_lv_pmos.sym} 880 0 0 0 {name=mdb0
w=2u
l=2u
ng=1
m=1
model=sg13_lv_pmos
spiceprefix=X
}
N 900 30 900 30 {lab=xd0}
C {devices/lab_pin.sym} 900 30 0 0 {name=p15 sig_type=std_logic lab=xd0}
N 860 0 860 0 {lab=pbias}
C {devices/lab_pin.sym} 860 0 0 1 {name=p16 sig_type=std_logic lab=pbias}
N 900 -30 900 -30 {lab=vdd}
C {devices/lab_pin.sym} 900 -30 0 0 {name=p17 sig_type=std_logic lab=vdd}
N 900 0 900 0 {lab=vdd}
C {devices/lab_pin.sym} 900 0 0 0 {name=p18 sig_type=std_logic lab=vdd}
C {sg13g2_pr/sg13_lv_pmos.sym} 1100 0 0 0 {name=msw0
w=2u
l=0.13u
ng=1
m=1
model=sg13_lv_pmos
spiceprefix=X
}
N 1120 30 1120 30 {lab=xraw}
C {devices/lab_pin.sym} 1120 30 0 0 {name=p19 sig_type=std_logic lab=xraw}
N 1080 0 1080 0 {lab=code0}
C {devices/lab_pin.sym} 1080 0 0 1 {name=p20 sig_type=std_logic lab=code0}
N 1120 -30 1120 -30 {lab=xd0}
C {devices/lab_pin.sym} 1120 -30 0 0 {name=p21 sig_type=std_logic lab=xd0}
N 1120 0 1120 0 {lab=vdd}
C {devices/lab_pin.sym} 1120 0 0 0 {name=p22 sig_type=std_logic lab=vdd}
C {sg13g2_pr/sg13_lv_pmos.sym} 0 120 0 0 {name=mdb1
w=4u
l=2u
ng=2
m=1
model=sg13_lv_pmos
spiceprefix=X
}
N 20 150 20 150 {lab=xd1}
C {devices/lab_pin.sym} 20 150 0 0 {name=p23 sig_type=std_logic lab=xd1}
N -20 120 -20 120 {lab=pbias}
C {devices/lab_pin.sym} -20 120 0 1 {name=p24 sig_type=std_logic lab=pbias}
N 20 90 20 90 {lab=vdd}
C {devices/lab_pin.sym} 20 90 0 0 {name=p25 sig_type=std_logic lab=vdd}
N 20 120 20 120 {lab=vdd}
C {devices/lab_pin.sym} 20 120 0 0 {name=p26 sig_type=std_logic lab=vdd}
C {sg13g2_pr/sg13_lv_pmos.sym} 220 120 0 0 {name=msw1
w=4u
l=0.13u
ng=1
m=1
model=sg13_lv_pmos
spiceprefix=X
}
N 240 150 240 150 {lab=xraw}
C {devices/lab_pin.sym} 240 150 0 0 {name=p27 sig_type=std_logic lab=xraw}
N 200 120 200 120 {lab=code1}
C {devices/lab_pin.sym} 200 120 0 1 {name=p28 sig_type=std_logic lab=code1}
N 240 90 240 90 {lab=xd1}
C {devices/lab_pin.sym} 240 90 0 0 {name=p29 sig_type=std_logic lab=xd1}
N 240 120 240 120 {lab=vdd}
C {devices/lab_pin.sym} 240 120 0 0 {name=p30 sig_type=std_logic lab=vdd}
C {sg13g2_pr/sg13_lv_pmos.sym} 440 120 0 0 {name=mdb2
w=8u
l=2u
ng=4
m=1
model=sg13_lv_pmos
spiceprefix=X
}
N 460 150 460 150 {lab=xd2}
C {devices/lab_pin.sym} 460 150 0 0 {name=p31 sig_type=std_logic lab=xd2}
N 420 120 420 120 {lab=pbias}
C {devices/lab_pin.sym} 420 120 0 1 {name=p32 sig_type=std_logic lab=pbias}
N 460 90 460 90 {lab=vdd}
C {devices/lab_pin.sym} 460 90 0 0 {name=p33 sig_type=std_logic lab=vdd}
N 460 120 460 120 {lab=vdd}
C {devices/lab_pin.sym} 460 120 0 0 {name=p34 sig_type=std_logic lab=vdd}
C {sg13g2_pr/sg13_lv_pmos.sym} 660 120 0 0 {name=msw2
w=8u
l=0.13u
ng=1
m=1
model=sg13_lv_pmos
spiceprefix=X
}
N 680 150 680 150 {lab=xraw}
C {devices/lab_pin.sym} 680 150 0 0 {name=p35 sig_type=std_logic lab=xraw}
N 640 120 640 120 {lab=code2}
C {devices/lab_pin.sym} 640 120 0 1 {name=p36 sig_type=std_logic lab=code2}
N 680 90 680 90 {lab=xd2}
C {devices/lab_pin.sym} 680 90 0 0 {name=p37 sig_type=std_logic lab=xd2}
N 680 120 680 120 {lab=vdd}
C {devices/lab_pin.sym} 680 120 0 0 {name=p38 sig_type=std_logic lab=vdd}
C {sg13g2_pr/sg13_lv_pmos.sym} 880 120 0 0 {name=mdb3
w=16u
l=2u
ng=8
m=1
model=sg13_lv_pmos
spiceprefix=X
}
N 900 150 900 150 {lab=xd3}
C {devices/lab_pin.sym} 900 150 0 0 {name=p39 sig_type=std_logic lab=xd3}
N 860 120 860 120 {lab=pbias}
C {devices/lab_pin.sym} 860 120 0 1 {name=p40 sig_type=std_logic lab=pbias}
N 900 90 900 90 {lab=vdd}
C {devices/lab_pin.sym} 900 90 0 0 {name=p41 sig_type=std_logic lab=vdd}
N 900 120 900 120 {lab=vdd}
C {devices/lab_pin.sym} 900 120 0 0 {name=p42 sig_type=std_logic lab=vdd}
C {sg13g2_pr/sg13_lv_pmos.sym} 1100 120 0 0 {name=msw3
w=16u
l=0.13u
ng=1
m=1
model=sg13_lv_pmos
spiceprefix=X
}
N 1120 150 1120 150 {lab=xraw}
C {devices/lab_pin.sym} 1120 150 0 0 {name=p43 sig_type=std_logic lab=xraw}
N 1080 120 1080 120 {lab=code3}
C {devices/lab_pin.sym} 1080 120 0 1 {name=p44 sig_type=std_logic lab=code3}
N 1120 90 1120 90 {lab=xd3}
C {devices/lab_pin.sym} 1120 90 0 0 {name=p45 sig_type=std_logic lab=xd3}
N 1120 120 1120 120 {lab=vdd}
C {devices/lab_pin.sym} 1120 120 0 0 {name=p46 sig_type=std_logic lab=vdd}
C {sg13g2_pr/sg13_lv_pmos.sym} 0 240 0 0 {name=mdb4
w=32u
l=2u
ng=16
m=1
model=sg13_lv_pmos
spiceprefix=X
}
N 20 270 20 270 {lab=xd4}
C {devices/lab_pin.sym} 20 270 0 0 {name=p47 sig_type=std_logic lab=xd4}
N -20 240 -20 240 {lab=pbias}
C {devices/lab_pin.sym} -20 240 0 1 {name=p48 sig_type=std_logic lab=pbias}
N 20 210 20 210 {lab=vdd}
C {devices/lab_pin.sym} 20 210 0 0 {name=p49 sig_type=std_logic lab=vdd}
N 20 240 20 240 {lab=vdd}
C {devices/lab_pin.sym} 20 240 0 0 {name=p50 sig_type=std_logic lab=vdd}
C {sg13g2_pr/sg13_lv_pmos.sym} 220 240 0 0 {name=msw4
w=32u
l=0.13u
ng=1
m=1
model=sg13_lv_pmos
spiceprefix=X
}
N 240 270 240 270 {lab=xraw}
C {devices/lab_pin.sym} 240 270 0 0 {name=p51 sig_type=std_logic lab=xraw}
N 200 240 200 240 {lab=code4}
C {devices/lab_pin.sym} 200 240 0 1 {name=p52 sig_type=std_logic lab=code4}
N 240 210 240 210 {lab=xd4}
C {devices/lab_pin.sym} 240 210 0 0 {name=p53 sig_type=std_logic lab=xd4}
N 240 240 240 240 {lab=vdd}
C {devices/lab_pin.sym} 240 240 0 0 {name=p54 sig_type=std_logic lab=vdd}
C {devices/vsource.sym} 440 240 0 0 {name=vsense value=0}
N 440 210 440 210 {lab=xraw}
C {devices/lab_pin.sym} 440 210 0 0 {name=p55 sig_type=std_logic lab=xraw}
N 440 270 440 270 {lab=xref}
C {devices/lab_pin.sym} 440 270 0 0 {name=p56 sig_type=std_logic lab=xref}
C {sg13g2_pr/sg13_lv_nmos.sym} 660 240 0 0 {name=mr
w=60u
l=4u
ng=12
m=1
model=sg13_lv_nmos
spiceprefix=X
}
N 680 210 680 210 {lab=xref}
C {devices/lab_pin.sym} 680 210 0 0 {name=p57 sig_type=std_logic lab=xref}
N 640 240 640 240 {lab=nbf}
C {devices/lab_pin.sym} 640 240 0 1 {name=p58 sig_type=std_logic lab=nbf}
N 680 270 680 270 {lab=gnd}
C {devices/lab_pin.sym} 680 270 0 0 {name=p59 sig_type=std_logic lab=gnd}
N 680 240 680 240 {lab=gnd}
C {devices/lab_pin.sym} 680 240 0 0 {name=p60 sig_type=std_logic lab=gnd}
C {sg13g2_pr/sg13_lv_nmos.sym} 880 240 0 0 {name=mt
w=480u
l=4u
ng=96
m=1
model=sg13_lv_nmos
spiceprefix=X
}
N 900 210 900 210 {lab=tail}
C {devices/lab_pin.sym} 900 210 0 0 {name=p61 sig_type=std_logic lab=tail}
N 860 240 860 240 {lab=nbf}
C {devices/lab_pin.sym} 860 240 0 1 {name=p62 sig_type=std_logic lab=nbf}
N 900 270 900 270 {lab=gnd}
C {devices/lab_pin.sym} 900 270 0 0 {name=p63 sig_type=std_logic lab=gnd}
N 900 240 900 240 {lab=gnd}
C {devices/lab_pin.sym} 900 240 0 0 {name=p64 sig_type=std_logic lab=gnd}
C {devices/res.sym} 1100 240 0 0 {name=rtf
value=100000.0
m=1
footprint=1206
device=resistor
sim_device=resistor
}
N 1100 210 1100 210 {lab=tail}
C {devices/lab_pin.sym} 1100 210 0 0 {name=p65 sig_type=std_logic lab=tail}
N 1100 270 1100 270 {lab=tail_f}
C {devices/lab_pin.sym} 1100 270 0 0 {name=p66 sig_type=std_logic lab=tail_f}
C {devices/capa.sym} 0 360 0 0 {name=ctf
value=1e-12
m=1
footprint=1206
device=capacitor
sim_device=capacitor
}
N 0 330 0 330 {lab=tail_f}
C {devices/lab_pin.sym} 0 330 0 0 {name=p67 sig_type=std_logic lab=tail_f}
N 0 390 0 390 {lab=gnd}
C {devices/lab_pin.sym} 0 390 0 0 {name=p68 sig_type=std_logic lab=gnd}
C {sg13g2_pr/sg13_lv_nmos.sym} 220 360 0 0 {name=mo1
w=8u
l=2u
ng=2
m=1
model=sg13_lv_nmos
spiceprefix=X
}
N 240 330 240 330 {lab=d1}
C {devices/lab_pin.sym} 240 330 0 0 {name=p69 sig_type=std_logic lab=d1}
N 200 360 200 360 {lab=xref}
C {devices/lab_pin.sym} 200 360 0 1 {name=p70 sig_type=std_logic lab=xref}
N 240 390 240 390 {lab=ss}
C {devices/lab_pin.sym} 240 390 0 0 {name=p71 sig_type=std_logic lab=ss}
N 240 360 240 360 {lab=gnd}
C {devices/lab_pin.sym} 240 360 0 0 {name=p72 sig_type=std_logic lab=gnd}
C {sg13g2_pr/sg13_lv_nmos.sym} 440 360 0 0 {name=mo2
w=8u
l=2u
ng=2
m=1
model=sg13_lv_nmos
spiceprefix=X
}
N 460 330 460 330 {lab=d2}
C {devices/lab_pin.sym} 460 330 0 0 {name=p73 sig_type=std_logic lab=d2}
N 420 360 420 360 {lab=tail_f}
C {devices/lab_pin.sym} 420 360 0 1 {name=p74 sig_type=std_logic lab=tail_f}
N 460 390 460 390 {lab=ss}
C {devices/lab_pin.sym} 460 390 0 0 {name=p75 sig_type=std_logic lab=ss}
N 460 360 460 360 {lab=gnd}
C {devices/lab_pin.sym} 460 360 0 0 {name=p76 sig_type=std_logic lab=gnd}
C {devices/isource.sym} 660 360 0 0 {name=iss value=2e-05}
N 660 330 660 330 {lab=ss}
C {devices/lab_pin.sym} 660 330 0 0 {name=p77 sig_type=std_logic lab=ss}
N 660 390 660 390 {lab=gnd}
C {devices/lab_pin.sym} 660 390 0 0 {name=p78 sig_type=std_logic lab=gnd}
C {sg13g2_pr/sg13_lv_pmos.sym} 880 360 0 0 {name=mp1
w=4u
l=2u
ng=2
m=1
model=sg13_lv_pmos
spiceprefix=X
}
N 900 390 900 390 {lab=d1}
C {devices/lab_pin.sym} 900 390 0 0 {name=p79 sig_type=std_logic lab=d1}
N 860 360 860 360 {lab=d1}
C {devices/lab_pin.sym} 860 360 0 1 {name=p80 sig_type=std_logic lab=d1}
N 900 330 900 330 {lab=vdd}
C {devices/lab_pin.sym} 900 330 0 0 {name=p81 sig_type=std_logic lab=vdd}
N 900 360 900 360 {lab=vdd}
C {devices/lab_pin.sym} 900 360 0 0 {name=p82 sig_type=std_logic lab=vdd}
C {sg13g2_pr/sg13_lv_pmos.sym} 1100 360 0 0 {name=mp2
w=4u
l=2u
ng=2
m=1
model=sg13_lv_pmos
spiceprefix=X
}
N 1120 390 1120 390 {lab=d2}
C {devices/lab_pin.sym} 1120 390 0 0 {name=p83 sig_type=std_logic lab=d2}
N 1080 360 1080 360 {lab=d1}
C {devices/lab_pin.sym} 1080 360 0 1 {name=p84 sig_type=std_logic lab=d1}
N 1120 330 1120 330 {lab=vdd}
C {devices/lab_pin.sym} 1120 330 0 0 {name=p85 sig_type=std_logic lab=vdd}
N 1120 360 1120 360 {lab=vdd}
C {devices/lab_pin.sym} 1120 360 0 0 {name=p86 sig_type=std_logic lab=vdd}
C {devices/res.sym} 0 480 0 0 {name=rout
value=1
m=1
footprint=1206
device=resistor
sim_device=resistor
}
N 0 450 0 450 {lab=d2}
C {devices/lab_pin.sym} 0 450 0 0 {name=p87 sig_type=std_logic lab=d2}
N 0 510 0 510 {lab=nb}
C {devices/lab_pin.sym} 0 510 0 0 {name=p88 sig_type=std_logic lab=nb}
C {devices/res.sym} 220 480 0 0 {name=rbf
value=1000000.0
m=1
footprint=1206
device=resistor
sim_device=resistor
}
N 220 450 220 450 {lab=nb}
C {devices/lab_pin.sym} 220 450 0 0 {name=p89 sig_type=std_logic lab=nb}
N 220 510 220 510 {lab=nbf}
C {devices/lab_pin.sym} 220 510 0 0 {name=p90 sig_type=std_logic lab=nbf}
C {devices/capa.sym} 440 480 0 0 {name=cbf
value=5e-11
m=1
footprint=1206
device=capacitor
sim_device=capacitor
}
N 440 450 440 450 {lab=nbf}
C {devices/lab_pin.sym} 440 450 0 0 {name=p91 sig_type=std_logic lab=nbf}
N 440 510 440 510 {lab=gnd}
C {devices/lab_pin.sym} 440 510 0 0 {name=p92 sig_type=std_logic lab=gnd}
C {devices/res.sym} 660 480 0 0 {name=rpd
value=200000.0
m=1
footprint=1206
device=resistor
sim_device=resistor
}
N 660 450 660 450 {lab=nb}
C {devices/lab_pin.sym} 660 450 0 0 {name=p93 sig_type=std_logic lab=nb}
N 660 510 660 510 {lab=gnd}
C {devices/lab_pin.sym} 660 510 0 0 {name=p94 sig_type=std_logic lab=gnd}
C {devices/capa.sym} 880 480 0 0 {name=ctail
value=8e-12
m=1
footprint=1206
device=capacitor
sim_device=capacitor
}
N 880 450 880 450 {lab=tail}
C {devices/lab_pin.sym} 880 450 0 0 {name=p95 sig_type=std_logic lab=tail}
N 880 510 880 510 {lab=gnd}
C {devices/lab_pin.sym} 880 510 0 0 {name=p96 sig_type=std_logic lab=gnd}
C {sg13g2_pr/sg13_lv_nmos.sym} 1100 480 0 0 {name=mbp_rbf
w=20u
l=0.13u
ng=4
m=1
model=sg13_lv_nmos
spiceprefix=X
}
N 1120 450 1120 450 {lab=nb}
C {devices/lab_pin.sym} 1120 450 0 0 {name=p97 sig_type=std_logic lab=nb}
N 1080 480 1080 480 {lab=vbp_tail}
C {devices/lab_pin.sym} 1080 480 0 1 {name=p98 sig_type=std_logic lab=vbp_tail}
N 1120 510 1120 510 {lab=nbf}
C {devices/lab_pin.sym} 1120 510 0 0 {name=p99 sig_type=std_logic lab=nbf}
N 1120 480 1120 480 {lab=gnd}
C {devices/lab_pin.sym} 1120 480 0 0 {name=p100 sig_type=std_logic lab=gnd}
