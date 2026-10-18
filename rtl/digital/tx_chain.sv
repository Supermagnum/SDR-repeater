`timescale 1ns/1ps
// TX path. DC and IQ correction stay here. The half-band multiplier
// and the delay memory are the shared fir_seq. The order-2 CIC
// integrator adders are the shared stage-1 adders in cic4; the
// 40-bit accumulator state stays here because the decimator banks
// are 28 bits and widening them costs more than a second copy.
// A 2nd-order 1-bit sigma-delta is separate on I and on Q.
// TX_DC_* and TX_PHASE are signed 8-bit. PHASE LSB is 1/128 rad.
// TX_GAIN 128 means 1.0.

module tx_chain (
    input  logic               clk,
    input  logic               rst_n,
    input  logic               en,
    input  logic               valid_in,
    input  logic signed [15:0] i_in,
    input  logic signed [15:0] q_in,
    input  logic signed [7:0]  dc_i,
    input  logic signed [7:0]  dc_q,
    input  logic [7:0]         gain_i,
    input  logic [7:0]         gain_q,
    input  logic signed [7:0]  phase,
    input  logic [10:0]        frame_clks,
    input  logic               mac_done,
    input  logic signed [15:0] ye_i,
    input  logic signed [15:0] yo_i,
    input  logic signed [15:0] ye_q,
    input  logic signed [15:0] yo_q,
    input  logic signed [39:0] s0,
    input  logic signed [39:0] s1,
    input  logic signed [39:0] s2,
    input  logic signed [39:0] s3,
    output logic               mac_valid,
    output logic signed [15:0] mac_i,
    output logic signed [15:0] mac_q,
    output logic signed [39:0] a0,
    output logic signed [39:0] b0,
    output logic signed [39:0] a1,
    output logic signed [39:0] b1,
    output logic signed [39:0] a2,
    output logic signed [39:0] b2,
    output logic signed [39:0] a3,
    output logic signed [39:0] b3,
    output logic               dac_bit_i,
    output logic               dac_bit_q,
    output logic               dac_bit_valid
);

    function automatic logic signed [15:0] sat16(input logic signed [24:0] v);
        if (v > 25'sd32767) sat16 = 16'sd32767;
        else if (v < -25'sd32768) sat16 = -16'sd32768;
        else sat16 = v[15:0];
    endfunction

    function automatic logic [4:0] flog(input logic [10:0] v);
        if (v >= 11'd512) flog = 5'd9;
        else if (v >= 11'd256) flog = 5'd8;
        else if (v >= 11'd128) flog = 5'd7;
        else if (v >= 11'd64) flog = 5'd6;
        else if (v >= 11'd32) flog = 5'd5;
        else if (v >= 11'd16) flog = 5'd4;
        else flog = 5'd3;
    endfunction

    logic signed [15:0] hold_ei, hold_oi, hold_eq, hold_oq;
    logic signed [15:0] lat_oi, lat_oq;
    logic [1:0] step;
    logic active;
    logic signed [15:0] cal_i, cal_q;
    logic [10:0] gap;
    logic odd_ph;
    logic signed [15:0] inj_i, inj_q;
    logic inject;
    logic signed [39:0] ci0, ci1, cq0, cq1;
    logic signed [39:0] xi_d, xq_d, ci_d, cq_d;
    logic signed [39:0] comb_i, comb_q;
    logic signed [24:0] si1, si2, sq1, sq2;
    logic bi, bq;

    wire [10:0] half = (frame_clks < 11'd2) ? 11'd1 : (frame_clks >> 1);
    wire [4:0] sh = flog(half);

    logic signed [24:0] n1i, n2i, n1q, n2q;
    logic signed [15:0] xi16, xq16;
    logic signed [39:0] ys_i, ys_q;

    // s0/s1 are I, s2/s3 are Q. Each pair is the shared cic4 adder.
    assign a0 = ci0;
    assign b0 = comb_i;
    assign a1 = ci1;
    assign b1 = ci0;
    assign a2 = cq0;
    assign b2 = comb_q;
    assign a3 = cq1;
    assign b3 = cq0;

    always_comb begin
        ys_i = ci1 >>> sh;
        ys_q = cq1 >>> sh;
        if (ys_i > 40'sd32767) xi16 = 16'sd32767;
        else if (ys_i < -40'sd32768) xi16 = -16'sd32768;
        else xi16 = ys_i[15:0];
        if (ys_q > 40'sd32767) xq16 = 16'sd32767;
        else if (ys_q < -40'sd32768) xq16 = -16'sd32768;
        else xq16 = ys_q[15:0];
        n1i = si1 + 25'(xi16) - (bi ? 25'sd32767 : -25'sd32767);
        n2i = si2 + n1i - (bi ? 25'sd32767 : -25'sd32767);
        n1q = sq1 + 25'(xq16) - (bq ? 25'sd32767 : -25'sd32767);
        n2q = sq2 + n1q - (bq ? 25'sd32767 : -25'sd32767);
        comb_i = 40'(inj_i) - xi_d - ci_d;
        comb_q = 40'(inj_q) - xq_d - cq_d;
    end

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            hold_ei <= '0; hold_oi <= '0; hold_eq <= '0; hold_oq <= '0;
            lat_oi <= '0; lat_oq <= '0;
            step <= '0; active <= 1'b0;
            cal_i <= '0; cal_q <= '0;
            gap <= '0; odd_ph <= 1'b0;
            inj_i <= '0; inj_q <= '0; inject <= 1'b0;
            ci0 <= '0; ci1 <= '0; cq0 <= '0; cq1 <= '0;
            xi_d <= '0; xq_d <= '0; ci_d <= '0; cq_d <= '0;
            si1 <= '0; si2 <= '0; sq1 <= '0; sq2 <= '0;
            bi <= 1'b0; bq <= 1'b0;
            mac_valid <= 1'b0;
            mac_i <= '0; mac_q <= '0;
            dac_bit_i <= 1'b0; dac_bit_q <= 1'b0; dac_bit_valid <= 1'b0;
        end else if (!en) begin
            active <= 1'b0;
            inject <= 1'b0;
            mac_valid <= 1'b0;
            dac_bit_valid <= 1'b0;
            gap <= '0;
            odd_ph <= 1'b0;
            bi <= 1'b0;
            bq <= 1'b0;
        end else begin
            dac_bit_valid <= 1'b1;
            mac_valid <= 1'b0;
            if (!active && valid_in) begin
                cal_i <= sat16(25'(i_in) - 25'(dc_i));
                cal_q <= sat16(25'(q_in) - 25'(dc_q));
                active <= 1'b1;
                step <= 2'd0;
            end else if (active && step == 2'd0) begin
                cal_i <= sat16((25'(cal_i) * $signed({1'b0, gain_i}) + 25'(cal_q) * phase) >>> 7);
                cal_q <= sat16((25'(cal_q) * $signed({1'b0, gain_q})) >>> 7);
                step <= 2'd1;
            end else if (active && step == 2'd1) begin
                mac_i <= cal_i;
                mac_q <= cal_q;
                mac_valid <= 1'b1;
                active <= 1'b0;
            end

            if (mac_done) begin
                hold_ei <= ye_i;
                hold_oi <= yo_i;
                hold_eq <= ye_q;
                hold_oq <= yo_q;
            end

            if (gap == 11'd0) begin
                gap <= half - 11'd1;
                if (!odd_ph) begin
                    inj_i <= hold_ei;
                    inj_q <= hold_eq;
                    lat_oi <= hold_oi;
                    lat_oq <= hold_oq;
                end else begin
                    inj_i <= lat_oi;
                    inj_q <= lat_oq;
                end
                odd_ph <= ~odd_ph;
                inject <= 1'b1;
            end else begin
                gap <= gap - 11'd1;
                inject <= 1'b0;
            end

            if (inject) begin
                xi_d <= 40'(inj_i);
                xq_d <= 40'(inj_q);
                ci_d <= 40'(inj_i) - xi_d;
                cq_d <= 40'(inj_q) - xq_d;
                ci0 <= s0;
                cq0 <= s2;
            end
            ci1 <= s1;
            cq1 <= s3;

            si1 <= n1i;
            si2 <= n2i;
            sq1 <= n1q;
            sq2 <= n2q;
            bi <= ~n2i[24];
            bq <= ~n2q[24];
            dac_bit_i <= ~n2i[24];
            dac_bit_q <= ~n2q[24];
        end
    end

endmodule
