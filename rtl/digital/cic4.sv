`timescale 1ns/1ps
// One order-4 CIC decimator.
// Each integrator is its own cycle and its own enable flop, so a
// valid is not a combo enable across four adders. The comb runs on
// the decimated beat, one stage per clock. Integrators wrap. Only
// the shifted 16-bit result saturates. shift is floor(4*log2(ratio)).
//
// Hogenauer pruning. The error budget is half a 16-bit LSB at the
// output. The last integrator and the comb registers drop the bottom
// DROP bits. Those bits are below the shift of every rate in the
// table (NOTE: since the 2026-10-18 output-scale change the smallest shift is 0,
// so DROP must stay 0 unless the rate table is revisited), so a residue under 2^DROP changes
// the output by less than 2^(DROP-shift) LSB. DROP is 2, which is
// under 0.25 LSB at shift 4 and far under it at the wider shifts.
// Earlier integrators stay full width: an LSB dropped there is
// multiplied by the remaining powers of the ratio.
//
// SHARE muxes the first two integrator adders onto an external
// operand pair. Transmit uses those adders for its order-2
// interpolator while receive is gated off, so the adder exists once.

module cic4 #(
    parameter bit SHARE = 1'b0
) (
    input  logic               clk,
    input  logic               rst_n,
    input  logic               en,
    input  logic [5:0]         ratio,
    input  logic [4:0]         shift,
    input  logic               valid_in,
    input  logic signed [15:0] din,
    output logic               valid_out,
    output logic signed [15:0] dout,
    input  logic               alt,
    input  logic signed [39:0] a0,
    input  logic signed [39:0] b0,
    input  logic signed [39:0] a1,
    input  logic signed [39:0] b1,
    output logic signed [39:0] s0,
    output logic signed [39:0] s1
);

    localparam int AW = 28;
    // 0 disables the prune so a negative-code failure can be attributed.
    localparam int DROP = 0;
    logic signed [AW-1:0] i0, i1, i2;
    logic signed [AW-DROP-1:0] i3, c0, c1, c2, c3;
    logic signed [15:0] x_r;
    logic v_in;
    (* keep = "true" *) logic e0, e1, e2, e3;
    logic comb_go;
    logic [1:0] comb_st;
    logic [5:0] count;
    logic signed [AW-DROP-1:0] comb_v;

    wire signed [AW-1:0] i3_ext = (DROP == 0) ? i3 : {i3, {DROP{1'b0}}};
    wire signed [AW-1:0] i3_sum = i3_ext + i2;
    wire signed [39:0] add0 = (SHARE && alt) ? (a0 + b0) : ({{(40-AW){i0[AW-1]}}, i0} + {{24{x_r[15]}}, x_r});
    wire signed [39:0] add1 = (SHARE && alt) ? (a1 + b1) : ({{(40-AW){i1[AW-1]}}, i1} + {{(40-AW){i0[AW-1]}}, i0});

    assign s0 = add0;
    assign s1 = add1;

    function automatic logic signed [15:0] sat16(input logic signed [AW-1:0] v);
        if (v > 28'sd32767) sat16 = 16'sd32767;
        else if (v < -28'sd32768) sat16 = -16'sd32768;
        else sat16 = v[15:0];
    endfunction

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            i0 <= '0;
            i1 <= '0;
            i2 <= '0;
            i3 <= '0;
            c0 <= '0;
            c1 <= '0;
            c2 <= '0;
            c3 <= '0;
            x_r <= '0;
            v_in <= 1'b0;
            e0 <= 1'b0;
            e1 <= 1'b0;
            e2 <= 1'b0;
            e3 <= 1'b0;
            comb_go <= 1'b0;
            comb_st <= 2'd0;
            count <= '0;
            comb_v <= '0;
            valid_out <= 1'b0;
            dout <= '0;
        end else begin
            valid_out <= 1'b0;
            if (!en) begin
                v_in <= 1'b0;
                e0 <= 1'b0;
                e1 <= 1'b0;
                e2 <= 1'b0;
                e3 <= 1'b0;
                comb_go <= 1'b0;
                comb_st <= 2'd0;
                count <= '0;
            end else begin
                v_in <= valid_in;
                x_r <= din;
                e0 <= v_in;
                e1 <= e0;
                e2 <= e1;
                e3 <= e2;
                if (e0 && !(SHARE && alt)) i0 <= add0[AW-1:0];
                if (e1 && !(SHARE && alt)) i1 <= add1[AW-1:0];
                if (e2) i2 <= i2 + i1;
                if (e3) i3 <= i3_sum[AW-1:DROP];
                comb_go <= 1'b0;
                if (e3 && ratio != 6'd0) begin
                    if (count + 6'd1 == ratio) begin
                        count <= '0;
                        comb_go <= 1'b1;
                    end else begin
                        count <= count + 6'd1;
                    end
                end
                if (comb_go) begin
                    comb_st <= 2'd1;
                    comb_v <= i3 - c0;
                    c0 <= i3;
                end else if (comb_st == 2'd1) begin
                    comb_st <= 2'd2;
                    comb_v <= comb_v - c1;
                    c1 <= comb_v;
                end else if (comb_st == 2'd2) begin
                    comb_st <= 2'd3;
                    comb_v <= comb_v - c2;
                    c2 <= comb_v;
                end else if (comb_st == 2'd3) begin
                    comb_st <= 2'd0;
                    c3 <= comb_v;
                    // Restoring the dropped bits and then applying the
                    // table shift keeps the DC gain of the unpruned CIC.
                    dout <= sat16($signed(comb_v - c3) >>> shift);
                    valid_out <= 1'b1;
                end
            end
        end
    end

endmodule
