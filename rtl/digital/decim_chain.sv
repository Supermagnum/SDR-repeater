`timescale 1ns/1ps
// Modulator-rate to IQ-rate chain.
// Two order-4 CIC stages, a 3-tap CIC-compensation FIR, then a
// 31-tap half-band that decimates by 2. The half-band input rate
// is exactly twice the output sample rate.
// Compensation taps are [-5006, 32767, -5006] / 2^15.
// Half-band taps are the quantized 31-tap design in notes.md.
// en low bypasses the chain and does not clear CIC state. A bypass
// is power-down. Sleep (en low because RX is off) keeps the state
// only if the caller stops valid_in instead of clearing en. The
// top keeps en tied to the block power-down bit, not to RX sleep.

module decim_chain (
    input  logic               clk,
    input  logic               rst_n,
    input  logic               en,
    input  logic [5:0]         r1,
    input  logic [5:0]         r2,
    input  logic [4:0]         sh1,
    input  logic [4:0]         sh2,
    input  logic               valid_in,
    input  logic signed [15:0] i_in,
    input  logic signed [15:0] q_in,
    output logic               valid_out,
    output logic signed [15:0] i_out,
    output logic signed [15:0] q_out
);

    logic v1_i, v2_i, vc_i, vh_i;
    logic v1_q, v2_q, vc_q, vh_q;
    logic signed [15:0] d1_i, d2_i, dc_i, dh_i;
    logic signed [15:0] d1_q, d2_q, dc_q, dh_q;
    localparam logic signed [47:0] CFIR = {-16'sd5006, 16'sd32767, -16'sd5006};
    localparam logic signed [495:0] HB = {
        -16'sd138, 16'sd0, 16'sd305, 16'sd0, -16'sd617, 16'sd0, 16'sd1128, 16'sd0,
        -16'sd1952, 16'sd0, 16'sd3376, 16'sd0, -16'sd6450, 16'sd0, 16'sd20688, 16'sd32767,
        16'sd20688, 16'sd0, -16'sd6450, 16'sd0, 16'sd3376, 16'sd0, -16'sd1952, 16'sd0,
        16'sd1128, 16'sd0, -16'sd617, 16'sd0, 16'sd305, 16'sd0, -16'sd138
    };

    cic4 u_i1 (.clk(clk), .rst_n(rst_n), .en(en), .ratio(r1), .shift(sh1), .valid_in(valid_in && en), .din(i_in), .valid_out(v1_i), .dout(d1_i));
    cic4 u_i2 (.clk(clk), .rst_n(rst_n), .en(en), .ratio(r2), .shift(sh2), .valid_in(v1_i), .din(d1_i), .valid_out(v2_i), .dout(d2_i));
    fir_mac #(.TAPS(3), .DEC2(0), .COEFF(CFIR)) u_ic (.clk(clk), .rst_n(rst_n), .en(en), .valid_in(v2_i), .din(d2_i), .valid_out(vc_i), .dout(dc_i));
    fir_mac #(.TAPS(31), .DEC2(1), .COEFF(HB)) u_ih (.clk(clk), .rst_n(rst_n), .en(en), .valid_in(vc_i), .din(dc_i), .valid_out(vh_i), .dout(dh_i));

    cic4 u_q1 (.clk(clk), .rst_n(rst_n), .en(en), .ratio(r1), .shift(sh1), .valid_in(valid_in && en), .din(q_in), .valid_out(v1_q), .dout(d1_q));
    cic4 u_q2 (.clk(clk), .rst_n(rst_n), .en(en), .ratio(r2), .shift(sh2), .valid_in(v1_q), .din(d1_q), .valid_out(v2_q), .dout(d2_q));
    fir_mac #(.TAPS(3), .DEC2(0), .COEFF(CFIR)) u_qc (.clk(clk), .rst_n(rst_n), .en(en), .valid_in(v2_q), .din(d2_q), .valid_out(vc_q), .dout(dc_q));
    fir_mac #(.TAPS(31), .DEC2(1), .COEFF(HB)) u_qh (.clk(clk), .rst_n(rst_n), .en(en), .valid_in(vc_q), .din(dc_q), .valid_out(vh_q), .dout(dh_q));

    // Bypass is one register so the disabled filter does not feed I2S.
    logic bypass_v;
    logic signed [15:0] bypass_i, bypass_q;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            bypass_v <= 1'b0;
            bypass_i <= '0;
            bypass_q <= '0;
        end else begin
            bypass_v <= valid_in && !en;
            if (valid_in && !en) begin
                bypass_i <= i_in;
                bypass_q <= q_in;
            end
        end
    end

    assign valid_out = en ? (vh_i && vh_q) : bypass_v;
    assign i_out = en ? dh_i : bypass_i;
    assign q_out = en ? dh_q : bypass_q;

endmodule
