`timescale 1ns/1ps
// Sample-rate divider for a 32 MHz or 36 MHz reference.
// Every listed output rate divides the reference exactly.
// The CIC is two order-4 stages. Their ratios multiply to
// half the frame length, and the half-band takes the last factor of 2.
// sh1/sh2 are floor(4*log2(R)) so each stage's DC gain lands in [1, 2).

module rate_table (
    input  logic        ref_36,
    input  logic [2:0]  rate,
    output logic [10:0] frame_clks,
    output logic [5:0]  r1,
    output logic [5:0]  r2,
    output logic [4:0]  sh1,
    output logic [4:0]  sh2
);

    always_comb begin
        frame_clks = 11'd64;
        r1 = 6'd4;
        r2 = 6'd8;
        sh1 = 5'd8;
        sh2 = 5'd12;
        if (!ref_36) begin
            case (rate)
                3'd0: begin frame_clks = 11'd1280; r1 = 6'd16; r2 = 6'd40; sh1 = 5'd16; sh2 = 5'd21; end
                3'd1: begin frame_clks = 11'd640;  r1 = 6'd16; r2 = 6'd20; sh1 = 5'd16; sh2 = 5'd17; end
                3'd2: begin frame_clks = 11'd320;  r1 = 6'd10; r2 = 6'd16; sh1 = 5'd13; sh2 = 5'd16; end
                3'd3: begin frame_clks = 11'd160;  r1 = 6'd8;  r2 = 6'd10; sh1 = 5'd12; sh2 = 5'd13; end
                default: begin frame_clks = 11'd64; r1 = 6'd4; r2 = 6'd8; sh1 = 5'd8; sh2 = 5'd12; end
            endcase
        end else begin
            case (rate)
                3'd0: begin frame_clks = 11'd1440; r1 = 6'd16; r2 = 6'd45; sh1 = 5'd16; sh2 = 5'd21; end
                3'd1: begin frame_clks = 11'd720;  r1 = 6'd15; r2 = 6'd24; sh1 = 5'd15; sh2 = 5'd18; end
                3'd2: begin frame_clks = 11'd360;  r1 = 6'd12; r2 = 6'd15; sh1 = 5'd14; sh2 = 5'd15; end
                3'd3: begin frame_clks = 11'd180;  r1 = 6'd9;  r2 = 6'd10; sh1 = 5'd12; sh2 = 5'd13; end
                default: begin frame_clks = 11'd72; r1 = 6'd4; r2 = 6'd9; sh1 = 5'd8; sh2 = 5'd12; end
            endcase
        end
    end

endmodule
