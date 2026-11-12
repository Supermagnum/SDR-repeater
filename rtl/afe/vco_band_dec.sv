// D24: 3→7 thermometer decoder for VCO_BAND[7:5]; [4:0] pass through as binary LSBs.
// Logical 8-bit code is unchanged (VCO_BAND / D20). Physical bank: 5 binary + 7 unit cells.
`timescale 1ns / 1ps

module vco_band_dec (
    input  wire [7:0] code,
    output wire [4:0] bin,     // LSB cells, weight 1..16
    output wire [6:0] therm    // unit cells, weight 32 each; therm[i] = (code[7:5] > i)
);
    assign bin = code[4:0];
    wire [2:0] msb = code[7:5];
    genvar i;
    generate
        for (i = 0; i < 7; i = i + 1) begin : g_th
            assign therm[i] = (msb > i[2:0]);
        end
    endgenerate
endmodule
