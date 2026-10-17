`timescale 1ns/1ps
// Latch-based integrated clock gate.
// sg13g2_lgcp_1 and sg13g2_slgcp_1 are the library cells (GATE high
// enables GCLK, latch transparent while CLK is low). Both are marked
// dont_use and are listed in the PDK synth_exclude and pnr_exclude
// files, so this flow cannot place them. The network below is the
// same function: the enable is latched while clk is low, then AND-ed
// with clk, which is the glitch-free clock-gate structure.

module clk_gate (
    input  logic clk,
    input  logic en,
    output logic gclk
);
    logic lat;
    always_latch if (!clk) lat = en;
    assign gclk = clk & lat;
endmodule
