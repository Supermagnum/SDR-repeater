set clock_port __VIRTUAL_CLK__
if { [info exists ::env(CLOCK_PORT)] } {
    set port_count [llength $::env(CLOCK_PORT)]
    if { $port_count > "0" } {
        set ::clock_port [lindex $::env(CLOCK_PORT) 0]
    }
}
set port_args [get_ports $clock_port]
create_clock {*}$port_args -name $clock_port -period $::env(CLOCK_PERIOD)
# SPI is a separate clock. 40 ns is 25 MHz.
create_clock [get_ports sclk] -name sclk -period 40.0
# Slave bit clock. 62.5 ns is the 16 MHz repeater cap.
create_clock [get_ports bclk_i] -name bclk_i -period 62.5
set_clock_groups -asynchronous \
    -group [get_clocks $clock_port] \
    -group [get_clocks sclk] \
    -group [get_clocks bclk_i]

set input_delay_value [expr $::env(CLOCK_PERIOD) * $::env(IO_DELAY_CONSTRAINT) / 100]
set output_delay_value [expr $::env(CLOCK_PERIOD) * $::env(IO_DELAY_CONSTRAINT) / 100]

set_max_fanout $::env(MAX_FANOUT_CONSTRAINT) [current_design]
if { [info exists ::env(MAX_TRANSITION_CONSTRAINT)] } {
    set_max_transition $::env(MAX_TRANSITION_CONSTRAINT) [current_design]
}
if { [info exists ::env(MAX_CAPACITANCE_CONSTRAINT)] } {
    set_max_capacitance $::env(MAX_CAPACITANCE_CONSTRAINT) [current_design]
}

set clk_input [get_port $clock_port]
set clk_indx [lsearch [all_inputs] $clk_input]
set all_inputs_wo_clk [lreplace [all_inputs] $clk_indx $clk_indx ""]
set sclk_indx [lsearch $all_inputs_wo_clk [get_port sclk]]
set all_inputs_wo_clk [lreplace $all_inputs_wo_clk $sclk_indx $sclk_indx ""]
set bclk_indx [lsearch $all_inputs_wo_clk [get_port bclk_i]]
set all_inputs_wo_clk [lreplace $all_inputs_wo_clk $bclk_indx $bclk_indx ""]
set all_inputs_wo_clk_rst $all_inputs_wo_clk

set clocks [get_clocks $clock_port]
set_input_delay $input_delay_value -clock $clocks $all_inputs_wo_clk_rst
set_output_delay $output_delay_value -clock $clocks [all_outputs]

if { ![info exists ::env(SYNTH_CLK_DRIVING_CELL)] } {
    set ::env(SYNTH_CLK_DRIVING_CELL) $::env(SYNTH_DRIVING_CELL)
}
set_driving_cell \
    -lib_cell [lindex [split $::env(SYNTH_DRIVING_CELL) "/"] 0] \
    -pin [lindex [split $::env(SYNTH_DRIVING_CELL) "/"] 1] \
    $all_inputs_wo_clk_rst
set_driving_cell \
    -lib_cell [lindex [split $::env(SYNTH_CLK_DRIVING_CELL) "/"] 0] \
    -pin [lindex [split $::env(SYNTH_CLK_DRIVING_CELL) "/"] 1] \
    $clk_input
set_driving_cell \
    -lib_cell [lindex [split $::env(SYNTH_CLK_DRIVING_CELL) "/"] 0] \
    -pin [lindex [split $::env(SYNTH_CLK_DRIVING_CELL) "/"] 1] \
    [get_ports {sclk bclk_i}]

set cap_load [expr $::env(OUTPUT_CAP_LOAD) / 1000.0]
set_load $cap_load [all_outputs]
set_clock_uncertainty -setup $::env(CLOCK_UNCERTAINTY_CONSTRAINT) [all_clocks]
set_clock_uncertainty -hold 0.05 [all_clocks]
set_clock_transition $::env(CLOCK_TRANSITION_CONSTRAINT) [all_clocks]
set_timing_derate -early [expr 1-[expr $::env(TIME_DERATING_CONSTRAINT) / 100.0]]
set_timing_derate -late [expr 1+[expr $::env(TIME_DERATING_CONSTRAINT) / 100.0]]
set_propagated_clock [all_clocks]
