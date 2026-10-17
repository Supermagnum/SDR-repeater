`timescale 1ns/1ps
// One order-4 CIC decimator.
// Each integrator is its own cycle and its own enable flop, so a
// valid is not a combo enable across four adders. The comb runs on
// the decimated beat, one stage per clock. Integrators wrap. Only
// the shifted 16-bit result saturates. shift is floor(4*log2(ratio)).

module cic4 (
    input  logic               clk,
    input  logic               rst_n,
    input  logic               en,
    input  logic [5:0]         ratio,
    input  logic [4:0]         shift,
    input  logic               valid_in,
    input  logic signed [15:0] din,
    output logic               valid_out,
    output logic signed [15:0] dout
);

    localparam int AW = 40;
    logic signed [AW-1:0] i0, i1, i2, i3;
    logic signed [AW-1:0] c0, c1, c2, c3;
    logic signed [15:0] x_r;
    logic v_in;
    // Replicated enables. keep stops synthesis merging them back
    // into one high-fanout net.
    (* keep = "true" *) logic e0, e1, e2, e3;
    logic comb_go;
    logic [1:0] comb_st;
    logic [5:0] count;
    logic signed [AW-1:0] comb_v;

    function automatic logic signed [15:0] sat16(input logic signed [AW-1:0] v);
        if (v > 40'sd32767) sat16 = 16'sd32767;
        else if (v < -40'sd32768) sat16 = -16'sd32768;
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
                if (e0) i0 <= i0 + {{(AW-16){x_r[15]}}, x_r};
                if (e1) i1 <= i1 + i0;
                if (e2) i2 <= i2 + i1;
                if (e3) i3 <= i3 + i2;
                comb_go <= 1'b0;
                if (e3 && ratio != 6'd0) begin
                    if (count + 6'd1 == ratio) begin
                        count <= '0;
                        comb_go <= 1'b1;
                    end else begin
                        count <= count + 6'd1;
                    end
                end
                // i3 has the new value on the cycle after e3.
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
                    dout <= sat16((comb_v - c3) >>> shift);
                    valid_out <= 1'b1;
                end
            end
        end
    end

endmodule
