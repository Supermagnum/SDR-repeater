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
C {devices/iopin.sym} -200 -440 0 0 {name=hold lab=hold}
C {devices/iopin.sym} -200 -480 0 0 {name=rep lab=rep}
C {devices/iopin.sym} -200 -520 0 0 {name=g0 lab=g0}
C {devices/iopin.sym} -200 -560 0 0 {name=g1 lab=g1}
C {devices/iopin.sym} -200 -600 0 0 {name=g2 lab=g2}
C {devices/iopin.sym} -200 -640 0 0 {name=g3 lab=g3}
C {devices/iopin.sym} -200 -680 0 0 {name=g4 lab=g4}
C {devices/iopin.sym} -200 -720 0 0 {name=g5 lab=g5}
C {devices/iopin.sym} -200 -760 0 0 {name=g6 lab=g6}
C {devices/iopin.sym} -200 -800 0 0 {name=g7 lab=g7}
C {devices/iopin.sym} -200 -840 0 0 {name=g8 lab=g8}
C {devices/iopin.sym} -200 -880 0 0 {name=g9 lab=g9}
C {devices/iopin.sym} -200 -920 0 0 {name=g10 lab=g10}
C {devices/iopin.sym} -200 -960 0 0 {name=g11 lab=g11}
C {devices/iopin.sym} -200 -1000 0 0 {name=code0 lab=code0}
C {devices/iopin.sym} -200 -1040 0 0 {name=code1 lab=code1}
C {devices/iopin.sym} -200 -1080 0 0 {name=code2 lab=code2}
C {devices/iopin.sym} -200 -1120 0 0 {name=code3 lab=code3}
C {devices/iopin.sym} -200 -1160 0 0 {name=code4 lab=code4}
C {devices/title.sym} 0 40 0 0 {name=t1 author="HT13G-M P2.7.1"}
C {devices/lab_pin.sym} 200 40 0 0 {name=ttitle lab=vco_top_P272a_hier}
C {l2n0.sym} 0 0 0 0 {name=xl
p=tp
n=tn
ct=ct
}
C {vco_core.sym} 200 0 0 0 {name=xcore
tp=tp
tn=tn
tail=tail
ct=ct
vdd=vdd
gnd=gnd
}
C {vco_bank.sym} 400 0 0 0 {name=xbank
tp=tp
tn=tn
vbp=vbp
gnd=gnd
g0=g0
bb0=bb0
g1=g1
bb1=bb1
g2=g2
bb2=bb2
g3=g3
bb3=bb3
g4=g4
bb4=bb4
g5=g5
bb5=bb5
g6=g6
bb6=bb6
g7=g7
bb7=bb7
g8=g8
bb8=bb8
g9=g9
bb9=bb9
g10=g10
bb10=bb10
g11=g11
bb11=bb11
}
C {vco_var.sym} 600 0 0 0 {name=xvar
tp=tp
tn=tn
vt=vt
vbp=vbp
gnd=gnd
}
C {vco_tail_dac.sym} 200 200 0 0 {name=xtail
tail=tail
vdd=vdd
gnd=gnd
vbp_tail=vbp_tail
nb=nb
nbf=nbf
code0=code0
code1=code1
code2=code2
code3=code3
code4=code4
}
C {ampcal_det.sym} 400 200 0 0 {name=xdet
tp=tp
tn=tn
ct=ct
vdd=vdd
gnd=gnd
cmp=cmp
hold=hold
rep=rep
}
