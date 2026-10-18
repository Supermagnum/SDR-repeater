`timescale 1ns/1ps
// Modulator-rate to IQ-rate chain.
// Two order-4 CIC stages, then one shared symmetric MAC for the
// 3-tap compensation FIR and the 31-tap half-band decimator.
// `norm` is the Q15 scale that puts every rate's DC gain at 1.
// en low bypasses and does not clear CIC state.

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
    output logic signed [15:0] q_out,
    input  logic               alt,
    input  logic signed [39:0] a0,
    input  logic signed [39:0] b0,
    input  logic signed [39:0] a1,
    input  logic signed [39:0] b1,
    input  logic signed [39:0] a2,
    input  logic signed [39:0] b2,
    input  logic signed [39:0] a3,
    input  logic signed [39:0] b3,
    output logic signed [39:0] s0,
    output logic signed [39:0] s1,
    output logic signed [39:0] s2,
    output logic signed [39:0] s3
);

    logic v1_i, v2_i, v1_q, v2_q;
    logic signed [15:0] d1_i, d2_i, d1_q, d2_q;
    // Private copies of the input valid, one per CIC, so the pin
    // does not enable every integrator through one net.
    (* keep = "true" *) logic v_i, v_q;
    logic signed [15:0] x_i, x_q;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            v_i <= 1'b0;
            v_q <= 1'b0;
            x_i <= '0;
            x_q <= '0;
        end else begin
            v_i <= valid_in && en;
            v_q <= valid_in && en;
            x_i <= i_in;
            x_q <= q_in;
        end
    end

    cic4 #(.SHARE(1'b1)) u_i1 (
        .clk(clk), .rst_n(rst_n), .en(en), .ratio(r1), .shift(sh1),
        .valid_in(v_i), .din(x_i), .valid_out(v1_i), .dout(d1_i),
        .alt(alt), .a0(a0), .b0(b0), .a1(a1), .b1(b1), .s0(s0), .s1(s1)
    );
    cic4 u_i2 (
        .clk(clk), .rst_n(rst_n), .en(en), .ratio(r2), .shift(sh2),
        .valid_in(v1_i), .din(d1_i), .valid_out(v2_i), .dout(d2_i),
        // s0/s1 (shared-adder outputs) are only used on the SHARE instances.
        /* verilator lint_off PINCONNECTEMPTY */
        .alt(1'b0), .a0('0), .b0('0), .a1('0), .b1('0), .s0(), .s1()
        /* verilator lint_on PINCONNECTEMPTY */
    );
    cic4 #(.SHARE(1'b1)) u_q1 (
        .clk(clk), .rst_n(rst_n), .en(en), .ratio(r1), .shift(sh1),
        .valid_in(v_q), .din(x_q), .valid_out(v1_q), .dout(d1_q),
        .alt(alt), .a0(a2), .b0(b2), .a1(a3), .b1(b3), .s0(s2), .s1(s3)
    );
    cic4 u_q2 (
        .clk(clk), .rst_n(rst_n), .en(en), .ratio(r2), .shift(sh2),
        .valid_in(v1_q), .din(d1_q), .valid_out(v2_q), .dout(d2_q),
        // s0/s1 (shared-adder outputs) are only used on the SHARE instances.
        /* verilator lint_off PINCONNECTEMPTY */
        .alt(1'b0), .a0('0), .b0('0), .a1('0), .b1('0), .s0(), .s1()
        /* verilator lint_on PINCONNECTEMPTY */
    );

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

    assign valid_out = en ? (v2_i && v2_q) : bypass_v;
    assign i_out = en ? d2_i : bypass_i;
    assign q_out = en ? d2_q : bypass_q;

endmodule
