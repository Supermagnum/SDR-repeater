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
C {devices/iopin.sym} -200 -360 0 0 {name=en lab=en}
C {devices/iopin.sym} -200 -400 0 0 {name=vthn lab=vthn}
C {devices/title.sym} 0 40 0 0 {name=t1 author="HT13G-M P2.7.1"}
C {devices/lab_pin.sym} 200 40 0 0 {name=ttitle lab=ampcal_det_cmp_D22_fab}
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
C {sg13g2_pr/sg13_lv_nmos.sym} 440 0 0 0 {name=mrtp
w=0.5u
l=0.13u
ng=1
m=1
model=sg13_lv_nmos
spiceprefix=X
}
N 460 -30 460 -30 {lab=vdd}
C {devices/lab_pin.sym} 460 -30 0 0 {name=p9 sig_type=std_logic lab=vdd}
N 420 0 420 0 {lab=ct}
C {devices/lab_pin.sym} 420 0 0 1 {name=p10 sig_type=std_logic lab=ct}
N 460 30 460 30 {lab=rep}
C {devices/lab_pin.sym} 460 30 0 0 {name=p11 sig_type=std_logic lab=rep}
N 460 0 460 0 {lab=gnd}
C {devices/lab_pin.sym} 460 0 0 0 {name=p12 sig_type=std_logic lab=gnd}
C {sg13g2_pr/sg13_lv_nmos.sym} 660 0 0 0 {name=mrtn
w=0.5u
l=0.13u
ng=1
m=1
model=sg13_lv_nmos
spiceprefix=X
}
N 680 -30 680 -30 {lab=vdd}
C {devices/lab_pin.sym} 680 -30 0 0 {name=p13 sig_type=std_logic lab=vdd}
N 640 0 640 0 {lab=ct}
C {devices/lab_pin.sym} 640 0 0 1 {name=p14 sig_type=std_logic lab=ct}
N 680 30 680 30 {lab=rep}
C {devices/lab_pin.sym} 680 30 0 0 {name=p15 sig_type=std_logic lab=rep}
N 680 0 680 0 {lab=gnd}
C {devices/lab_pin.sym} 680 0 0 0 {name=p16 sig_type=std_logic lab=gnd}
C {sg13g2_pr/cap_cmim.sym} 880 0 0 0 {name=chold
model=cap_cmim
lvs_model=cmim
w=1.627000e-05
l=1.627000e-05
m=1
mm_ok=1
spiceprefix=X
}
N 880 -30 880 -30 {lab=hold}
C {devices/lab_pin.sym} 880 -30 0 0 {name=p17 sig_type=std_logic lab=hold}
N 880 30 880 30 {lab=gnd}
C {devices/lab_pin.sym} 880 30 0 0 {name=p18 sig_type=std_logic lab=gnd}
C {sg13g2_pr/cap_cmim.sym} 1100 0 0 0 {name=crep
model=cap_cmim
lvs_model=cmim
w=1.627000e-05
l=1.627000e-05
m=1
mm_ok=1
spiceprefix=X
}
N 1100 -30 1100 -30 {lab=rep}
C {devices/lab_pin.sym} 1100 -30 0 0 {name=p19 sig_type=std_logic lab=rep}
N 1100 30 1100 30 {lab=gnd}
C {devices/lab_pin.sym} 1100 30 0 0 {name=p20 sig_type=std_logic lab=gnd}
C {sg13g2_pr/rhigh.sym} 0 120 0 0 {name=rbias
w=5.000000e-07
l=1.923000e-05
b=0
m=1
model=rhigh
body=gnd
spiceprefix=X
mm_ok=1
}
N 0 90 0 90 {lab=vdd}
C {devices/lab_pin.sym} 0 90 0 0 {name=p21 sig_type=std_logic lab=vdd}
N 0 150 0 150 {lab=nbias}
C {devices/lab_pin.sym} 0 150 0 0 {name=p22 sig_type=std_logic lab=nbias}
C {sg13g2_pr/sg13_lv_nmos.sym} 220 120 0 0 {name=mdiode
w=1.0u
l=1.0u
ng=1
m=1
model=sg13_lv_nmos
spiceprefix=X
}
N 240 90 240 90 {lab=nbias}
C {devices/lab_pin.sym} 240 90 0 0 {name=p23 sig_type=std_logic lab=nbias}
N 200 120 200 120 {lab=nbias}
C {devices/lab_pin.sym} 200 120 0 1 {name=p24 sig_type=std_logic lab=nbias}
N 240 150 240 150 {lab=pd_d}
C {devices/lab_pin.sym} 240 150 0 0 {name=p25 sig_type=std_logic lab=pd_d}
N 240 120 240 120 {lab=gnd}
C {devices/lab_pin.sym} 240 120 0 0 {name=p26 sig_type=std_logic lab=gnd}
C {sg13g2_pr/sg13_lv_nmos.sym} 440 120 0 0 {name=men_d
w=2.0u
l=0.13u
ng=1
m=1
model=sg13_lv_nmos
spiceprefix=X
}
N 460 90 460 90 {lab=pd_d}
C {devices/lab_pin.sym} 460 90 0 0 {name=p27 sig_type=std_logic lab=pd_d}
N 420 120 420 120 {lab=en}
C {devices/lab_pin.sym} 420 120 0 1 {name=p28 sig_type=std_logic lab=en}
N 460 150 460 150 {lab=gnd}
C {devices/lab_pin.sym} 460 150 0 0 {name=p29 sig_type=std_logic lab=gnd}
N 460 120 460 120 {lab=gnd}
C {devices/lab_pin.sym} 460 120 0 0 {name=p30 sig_type=std_logic lab=gnd}
C {sg13g2_pr/sg13_lv_nmos.sym} 660 120 0 0 {name=mid_h
w=1.0u
l=1.0u
ng=1
m=1
model=sg13_lv_nmos
spiceprefix=X
}
N 680 90 680 90 {lab=hold}
C {devices/lab_pin.sym} 680 90 0 0 {name=p31 sig_type=std_logic lab=hold}
N 640 120 640 120 {lab=nbias}
C {devices/lab_pin.sym} 640 120 0 1 {name=p32 sig_type=std_logic lab=nbias}
N 680 150 680 150 {lab=pd_h}
C {devices/lab_pin.sym} 680 150 0 0 {name=p33 sig_type=std_logic lab=pd_h}
N 680 120 680 120 {lab=gnd}
C {devices/lab_pin.sym} 680 120 0 0 {name=p34 sig_type=std_logic lab=gnd}
C {sg13g2_pr/sg13_lv_nmos.sym} 880 120 0 0 {name=men_h
w=2.0u
l=0.13u
ng=1
m=1
model=sg13_lv_nmos
spiceprefix=X
}
N 900 90 900 90 {lab=pd_h}
C {devices/lab_pin.sym} 900 90 0 0 {name=p35 sig_type=std_logic lab=pd_h}
N 860 120 860 120 {lab=en}
C {devices/lab_pin.sym} 860 120 0 1 {name=p36 sig_type=std_logic lab=en}
N 900 150 900 150 {lab=gnd}
C {devices/lab_pin.sym} 900 150 0 0 {name=p37 sig_type=std_logic lab=gnd}
N 900 120 900 120 {lab=gnd}
C {devices/lab_pin.sym} 900 120 0 0 {name=p38 sig_type=std_logic lab=gnd}
C {sg13g2_pr/sg13_lv_nmos.sym} 1100 120 0 0 {name=mid_r
w=1.0u
l=1.0u
ng=1
m=1
model=sg13_lv_nmos
spiceprefix=X
}
N 1120 90 1120 90 {lab=rep}
C {devices/lab_pin.sym} 1120 90 0 0 {name=p39 sig_type=std_logic lab=rep}
N 1080 120 1080 120 {lab=nbias}
C {devices/lab_pin.sym} 1080 120 0 1 {name=p40 sig_type=std_logic lab=nbias}
N 1120 150 1120 150 {lab=pd_r}
C {devices/lab_pin.sym} 1120 150 0 0 {name=p41 sig_type=std_logic lab=pd_r}
N 1120 120 1120 120 {lab=gnd}
C {devices/lab_pin.sym} 1120 120 0 0 {name=p42 sig_type=std_logic lab=gnd}
C {sg13g2_pr/sg13_lv_nmos.sym} 0 240 0 0 {name=men_r
w=2.0u
l=0.13u
ng=1
m=1
model=sg13_lv_nmos
spiceprefix=X
}
N 20 210 20 210 {lab=pd_r}
C {devices/lab_pin.sym} 20 210 0 0 {name=p43 sig_type=std_logic lab=pd_r}
N -20 240 -20 240 {lab=en}
C {devices/lab_pin.sym} -20 240 0 1 {name=p44 sig_type=std_logic lab=en}
N 20 270 20 270 {lab=gnd}
C {devices/lab_pin.sym} 20 270 0 0 {name=p45 sig_type=std_logic lab=gnd}
N 20 240 20 240 {lab=gnd}
C {devices/lab_pin.sym} 20 240 0 0 {name=p46 sig_type=std_logic lab=gnd}
C {sg13g2_pr/sg13_lv_nmos.sym} 220 240 0 0 {name=mid_tt
w=2.0u
l=1.0u
ng=2
m=1
model=sg13_lv_nmos
spiceprefix=X
}
N 240 210 240 210 {lab=ttail}
C {devices/lab_pin.sym} 240 210 0 0 {name=p47 sig_type=std_logic lab=ttail}
N 200 240 200 240 {lab=nbias}
C {devices/lab_pin.sym} 200 240 0 1 {name=p48 sig_type=std_logic lab=nbias}
N 240 270 240 270 {lab=pd_tt}
C {devices/lab_pin.sym} 240 270 0 0 {name=p49 sig_type=std_logic lab=pd_tt}
N 240 240 240 240 {lab=gnd}
C {devices/lab_pin.sym} 240 240 0 0 {name=p50 sig_type=std_logic lab=gnd}
C {sg13g2_pr/sg13_lv_nmos.sym} 440 240 0 0 {name=men_tt
w=2.0u
l=0.13u
ng=1
m=1
model=sg13_lv_nmos
spiceprefix=X
}
N 460 210 460 210 {lab=pd_tt}
C {devices/lab_pin.sym} 460 210 0 0 {name=p51 sig_type=std_logic lab=pd_tt}
N 420 240 420 240 {lab=en}
C {devices/lab_pin.sym} 420 240 0 1 {name=p52 sig_type=std_logic lab=en}
N 460 270 460 270 {lab=gnd}
C {devices/lab_pin.sym} 460 270 0 0 {name=p53 sig_type=std_logic lab=gnd}
N 460 240 460 240 {lab=gnd}
C {devices/lab_pin.sym} 460 240 0 0 {name=p54 sig_type=std_logic lab=gnd}
C {sg13g2_pr/sg13_lv_nmos.sym} 660 240 0 0 {name=mid_ss
w=2.0u
l=1.0u
ng=2
m=1
model=sg13_lv_nmos
spiceprefix=X
}
N 680 210 680 210 {lab=ss2}
C {devices/lab_pin.sym} 680 210 0 0 {name=p55 sig_type=std_logic lab=ss2}
N 640 240 640 240 {lab=nbias}
C {devices/lab_pin.sym} 640 240 0 1 {name=p56 sig_type=std_logic lab=nbias}
N 680 270 680 270 {lab=pd_ss}
C {devices/lab_pin.sym} 680 270 0 0 {name=p57 sig_type=std_logic lab=pd_ss}
N 680 240 680 240 {lab=gnd}
C {devices/lab_pin.sym} 680 240 0 0 {name=p58 sig_type=std_logic lab=gnd}
C {sg13g2_pr/sg13_lv_nmos.sym} 880 240 0 0 {name=men_ss
w=2.0u
l=0.13u
ng=1
m=1
model=sg13_lv_nmos
spiceprefix=X
}
N 900 210 900 210 {lab=pd_ss}
C {devices/lab_pin.sym} 900 210 0 0 {name=p59 sig_type=std_logic lab=pd_ss}
N 860 240 860 240 {lab=en}
C {devices/lab_pin.sym} 860 240 0 1 {name=p60 sig_type=std_logic lab=en}
N 900 270 900 270 {lab=gnd}
C {devices/lab_pin.sym} 900 270 0 0 {name=p61 sig_type=std_logic lab=gnd}
N 900 240 900 240 {lab=gnd}
C {devices/lab_pin.sym} 900 240 0 0 {name=p62 sig_type=std_logic lab=gnd}
C {sg13g2_pr/sg13_lv_nmos.sym} 1100 240 0 0 {name=mc1
w=4u
l=0.5u
ng=2
m=1
model=sg13_lv_nmos
spiceprefix=X
}
N 1120 210 1120 210 {lab=co}
C {devices/lab_pin.sym} 1120 210 0 0 {name=p63 sig_type=std_logic lab=co}
N 1080 240 1080 240 {lab=hold}
C {devices/lab_pin.sym} 1080 240 0 1 {name=p64 sig_type=std_logic lab=hold}
N 1120 270 1120 270 {lab=ttail}
C {devices/lab_pin.sym} 1120 270 0 0 {name=p65 sig_type=std_logic lab=ttail}
N 1120 240 1120 240 {lab=gnd}
C {devices/lab_pin.sym} 1120 240 0 0 {name=p66 sig_type=std_logic lab=gnd}
C {sg13g2_pr/sg13_lv_nmos.sym} 0 360 0 0 {name=mc2
w=4u
l=0.5u
ng=2
m=1
model=sg13_lv_nmos
spiceprefix=X
}
N 20 330 20 330 {lab=co2}
C {devices/lab_pin.sym} 20 330 0 0 {name=p67 sig_type=std_logic lab=co2}
N -20 360 -20 360 {lab=vthn}
C {devices/lab_pin.sym} -20 360 0 1 {name=p68 sig_type=std_logic lab=vthn}
N 20 390 20 390 {lab=ttail}
C {devices/lab_pin.sym} 20 390 0 0 {name=p69 sig_type=std_logic lab=ttail}
N 20 360 20 360 {lab=gnd}
C {devices/lab_pin.sym} 20 360 0 0 {name=p70 sig_type=std_logic lab=gnd}
C {sg13g2_pr/rhigh.sym} 220 360 0 0 {name=rc1
w=5.000000e-07
l=6.960000e-06
b=0
m=1
model=rhigh
body=gnd
spiceprefix=X
mm_ok=1
}
N 220 330 220 330 {lab=vdd}
C {devices/lab_pin.sym} 220 330 0 0 {name=p71 sig_type=std_logic lab=vdd}
N 220 390 220 390 {lab=co}
C {devices/lab_pin.sym} 220 390 0 0 {name=p72 sig_type=std_logic lab=co}
C {sg13g2_pr/rhigh.sym} 440 360 0 0 {name=rc2
w=5.000000e-07
l=6.960000e-06
b=0
m=1
model=rhigh
body=gnd
spiceprefix=X
mm_ok=1
}
N 440 330 440 330 {lab=vdd}
C {devices/lab_pin.sym} 440 330 0 0 {name=p73 sig_type=std_logic lab=vdd}
N 440 390 440 390 {lab=co2}
C {devices/lab_pin.sym} 440 390 0 0 {name=p74 sig_type=std_logic lab=co2}
C {sg13g2_pr/sg13_lv_nmos.sym} 660 360 0 0 {name=mcs1
w=4u
l=0.5u
ng=2
m=1
model=sg13_lv_nmos
spiceprefix=X
}
N 680 330 680 330 {lab=n1}
C {devices/lab_pin.sym} 680 330 0 0 {name=p75 sig_type=std_logic lab=n1}
N 640 360 640 360 {lab=co2}
C {devices/lab_pin.sym} 640 360 0 1 {name=p76 sig_type=std_logic lab=co2}
N 680 390 680 390 {lab=ss2}
C {devices/lab_pin.sym} 680 390 0 0 {name=p77 sig_type=std_logic lab=ss2}
N 680 360 680 360 {lab=gnd}
C {devices/lab_pin.sym} 680 360 0 0 {name=p78 sig_type=std_logic lab=gnd}
C {sg13g2_pr/sg13_lv_nmos.sym} 880 360 0 0 {name=mcs2
w=4u
l=0.5u
ng=2
m=1
model=sg13_lv_nmos
spiceprefix=X
}
N 900 330 900 330 {lab=cmp}
C {devices/lab_pin.sym} 900 330 0 0 {name=p79 sig_type=std_logic lab=cmp}
N 860 360 860 360 {lab=co}
C {devices/lab_pin.sym} 860 360 0 1 {name=p80 sig_type=std_logic lab=co}
N 900 390 900 390 {lab=ss2}
C {devices/lab_pin.sym} 900 390 0 0 {name=p81 sig_type=std_logic lab=ss2}
N 900 360 900 360 {lab=gnd}
C {devices/lab_pin.sym} 900 360 0 0 {name=p82 sig_type=std_logic lab=gnd}
C {sg13g2_pr/sg13_lv_pmos.sym} 1100 360 0 0 {name=mpl1
w=4u
l=0.5u
ng=2
m=1
model=sg13_lv_pmos
spiceprefix=X
}
N 1120 390 1120 390 {lab=n1}
C {devices/lab_pin.sym} 1120 390 0 0 {name=p83 sig_type=std_logic lab=n1}
N 1080 360 1080 360 {lab=n1}
C {devices/lab_pin.sym} 1080 360 0 1 {name=p84 sig_type=std_logic lab=n1}
N 1120 330 1120 330 {lab=vdd}
C {devices/lab_pin.sym} 1120 330 0 0 {name=p85 sig_type=std_logic lab=vdd}
N 1120 360 1120 360 {lab=vdd}
C {devices/lab_pin.sym} 1120 360 0 0 {name=p86 sig_type=std_logic lab=vdd}
C {sg13g2_pr/sg13_lv_pmos.sym} 0 480 0 0 {name=mpl2
w=4u
l=0.5u
ng=2
m=1
model=sg13_lv_pmos
spiceprefix=X
}
N 20 510 20 510 {lab=cmp}
C {devices/lab_pin.sym} 20 510 0 0 {name=p87 sig_type=std_logic lab=cmp}
N -20 480 -20 480 {lab=n1}
C {devices/lab_pin.sym} -20 480 0 1 {name=p88 sig_type=std_logic lab=n1}
N 20 450 20 450 {lab=vdd}
C {devices/lab_pin.sym} 20 450 0 0 {name=p89 sig_type=std_logic lab=vdd}
N 20 480 20 480 {lab=vdd}
C {devices/lab_pin.sym} 20 480 0 0 {name=p90 sig_type=std_logic lab=vdd}
C {sg13g2_pr/cap_cmim.sym} 220 480 0 0 {name=cl_cmp
model=cap_cmim
lvs_model=cmim
w=5.780000e-06
l=5.780000e-06
m=1
mm_ok=1
spiceprefix=X
}
N 220 450 220 450 {lab=cmp}
C {devices/lab_pin.sym} 220 450 0 0 {name=p91 sig_type=std_logic lab=cmp}
N 220 510 220 510 {lab=gnd}
C {devices/lab_pin.sym} 220 510 0 0 {name=p92 sig_type=std_logic lab=gnd}
