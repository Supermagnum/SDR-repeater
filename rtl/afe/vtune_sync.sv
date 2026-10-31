// Synchronise V_tune monitor comparator outputs into the reference/SPI clock domain
// for PLL_STATUS[4:5] (D20, spec/analog-digital-interface.md §5.2).
//
// vtune_lo_a / vtune_hi_a are the asynchronous comparator outputs (analog).
// After two flops: vtune_lo / vtune_hi are safe to OR into the status register.
`timescale 1ns / 1ps

module vtune_sync (
    input  wire clk,
    input  wire rst_n,
    input  wire vtune_lo_a,
    input  wire vtune_hi_a,
    output reg  vtune_lo,   // PLL_STATUS[4]
    output reg  vtune_hi    // PLL_STATUS[5]
);
    reg lo_m, hi_m;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            lo_m     <= 1'b0;
            hi_m     <= 1'b0;
            vtune_lo <= 1'b0;
            vtune_hi <= 1'b0;
        end else begin
            lo_m     <= vtune_lo_a;
            hi_m     <= vtune_hi_a;
            vtune_lo <= lo_m;
            vtune_hi <= hi_m;
        end
    end
endmodule
