`timescale 1ns/1ps
// Symmetric FIR. Coefficients are signed 16-bit and already scaled
// so a unity-gain DC sum is about 2^15. The accumulator is shifted
// right by 15 and saturated. `dec2` keeps every second valid input.

module fir_mac #(
    parameter int TAPS = 3,
    parameter int DEC2 = 0,
    // Tap 0 is the most significant 16 bits. The concatenation
    // {tap0, tap1, ...} matches that order.
    parameter logic signed [TAPS*16-1:0] COEFF = '0
) (
    input  logic               clk,
    input  logic               rst_n,
    input  logic               en,
    input  logic               valid_in,
    input  logic signed [15:0] din,
    output logic               valid_out,
    output logic signed [15:0] dout
);

    logic signed [15:0] delay [0:TAPS-1];
    logic signed [15:0] nxt [0:TAPS-1];
    logic signed [15:0] coeff [0:TAPS-1];
    logic signed [39:0] prod [0:TAPS-1];
    logic signed [39:0] acc;
    genvar gi;
    generate
        for (gi = 0; gi < TAPS; gi = gi + 1) begin : g_tap
            assign coeff[gi] = COEFF[((TAPS - 1 - gi) * 16) +: 16];
        end
    endgenerate
    logic phase;
    integer kc;
    integer kf;

    function automatic logic signed [15:0] sat16(input logic signed [39:0] v);
        if (v > 40'sd32767) sat16 = 16'sd32767;
        else if (v < -40'sd32768) sat16 = -16'sd32768;
        else sat16 = v[15:0];
    endfunction

    always_comb begin
        nxt[0] = din;
        prod[0] = din * coeff[0];
        acc = prod[0];
        for (kc = 1; kc < TAPS; kc = kc + 1) begin
            nxt[kc] = delay[kc-1];
            prod[kc] = delay[kc-1] * coeff[kc];
            acc = acc + prod[kc];
        end
    end

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (kf = 0; kf < TAPS; kf = kf + 1) delay[kf] <= '0;
            phase <= 1'b0;
            valid_out <= 1'b0;
            dout <= '0;
        end else begin
            valid_out <= 1'b0;
            if (!en) begin
                phase <= 1'b0;
            end else if (valid_in) begin
                for (kf = 0; kf < TAPS; kf = kf + 1) delay[kf] <= nxt[kf];
                phase <= ~phase;
                if (DEC2 == 0 || phase == 1'b0) begin
                    dout <= sat16(acc >>> 15);
                    valid_out <= 1'b1;
                end
            end
        end
    end

endmodule
