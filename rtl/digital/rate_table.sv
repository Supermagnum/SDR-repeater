`timescale 1ns/1ps
// Sample-rate divider for a 32 MHz or 36 MHz reference.
// The 1-bit front end decimates by r0 (2 or 4). Two order-4 CIC
// stages then finish M/(2*r0), and the half-band takes the last 2.
// sh1/sh2 are floor(4*log2(R)) reduced so the signal keeps resolution
// (2026-10-18 output-scale fix). sh1 is reduced by up to 6 bits: CIC 1 output
// is 800..4050 at full scale. The limit is CIC 2's 28-bit registers:
// CIC1_out * r2^4 must stay below 2^27 (worst case 32 MHz/25 kHz: 1.28e8,
// safe because the front end never exceeds +/-50). sh2 takes the rest.
// norm (Q15) then equalises every pair to about 16384 at the output.
//
// I2S bit bit_cells are an even number of reference clocks, so BCLK is
// 50 percent and uniform. The slot width is the widest value in
// 16..32 that fits in the frame at that bit_cell length. 16-bit data is
// MSB-justified in the slot. A pair that cannot meet the 16 MHz
// repeater cap sets clk_error. The old "BCLK is the 32 MHz reference"
// case is not generated.

module rate_table (
    input  logic        ref_36,
    input  logic [2:0]  rate,
    output logic [10:0] frame_clks,
    output logic [2:0]  r0,
    output logic [5:0]  r1,
    output logic [5:0]  r2,
    output logic [4:0]  sh1,
    output logic [4:0]  sh2,
    output logic signed [15:0] norm,
    output logic [5:0]  slot,
    output logic [2:0]  bit_cell,
    output logic        clk_error
);

    always_comb begin
        frame_clks = 11'd64;
        r0 = 3'd4;
        r1 = 6'd2;
        r2 = 6'd4;
        sh1 = 5'd0;
        sh2 = 5'd4;
        norm = 16'sd30241;
        slot = 6'd16;
        bit_cell = 3'd2;
        clk_error = 1'b0;
        if (!ref_36) begin
            // bit_cell = 2, BCLK = 16 MHz, high = low = 1 reference clock.
            bit_cell = 3'd2;
            case (rate)
                3'd0: begin frame_clks = 11'd1280; r0 = 3'd4; r1 = 6'd10; r2 = 6'd16; sh1 = 5'd8; sh2 = 5'd13; norm = 16'sd24774; slot = 6'd32; end
                3'd1: begin frame_clks = 11'd640;  r0 = 3'd4; r1 = 6'd8;  r2 = 6'd10; sh1 = 5'd7; sh2 = 5'd10; norm = 16'sd24774; slot = 6'd32; end
                3'd2: begin frame_clks = 11'd320;  r0 = 3'd4; r1 = 6'd5;  r2 = 6'd8;  sh1 = 5'd4;  sh2 = 5'd9; norm = 16'sd24774; slot = 6'd32; end
                3'd3: begin frame_clks = 11'd160;  r0 = 3'd4; r1 = 6'd4;  r2 = 6'd5;  sh1 = 5'd3;  sh2 = 5'd6; norm = 16'sd24774; slot = 6'd32; end
                default: begin frame_clks = 11'd64; r0 = 3'd4; r1 = 6'd2; r2 = 6'd4; sh1 = 5'd0; sh2 = 5'd4; norm = 16'sd30241; slot = 6'd16; end
            endcase
        end else begin
            // bit_cell = 4, BCLK = 9 MHz, high = low = 2 reference clocks.
            bit_cell = 3'd4;
            case (rate)
                3'd0: begin frame_clks = 11'd1440; r0 = 3'd4; r1 = 6'd12; r2 = 6'd15; sh1 = 5'd9; sh2 = 5'd13; norm = 16'sd30932; slot = 6'd32; end
                3'd1: begin frame_clks = 11'd720;  r0 = 3'd4; r1 = 6'd9;  r2 = 6'd10; sh1 = 5'd7; sh2 = 5'd11; norm = 16'sd30932; slot = 6'd32; end
                3'd2: begin frame_clks = 11'd360;  r0 = 3'd4; r1 = 6'd5;  r2 = 6'd9;  sh1 = 5'd4;  sh2 = 5'd10; norm = 16'sd30932; slot = 6'd32; end
                3'd3: begin frame_clks = 11'd180;  r0 = 3'd2; r1 = 6'd5;  r2 = 6'd9;  sh1 = 5'd4;  sh2 = 5'd10; norm = 16'sd30932; slot = 6'd22; end
                default: begin
                    // 36 MHz, 500 kHz. A 16-bit slot needs 128 clocks at
                    // bit_cell = 4, and the frame is 72. bit_cell = 2 would make
                    // BCLK 18 MHz, over the 16 MHz repeater cap.
                    frame_clks = 11'd72;
                    r0 = 3'd4; r1 = 6'd3; r2 = 6'd3; sh1 = 5'd0; sh2 = 5'd4;
                    norm = 16'sd18879;
                    slot = 6'd16;
                    clk_error = 1'b1;
                end
            endcase
        end
    end

endmodule
