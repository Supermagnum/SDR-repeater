`timescale 1ns/1ps
// One order-4 CIC decimator. Integrators run at valid_in.
// Combs run once per `ratio` inputs. The comb result is shifted
// right by `shift` and saturated to 16 bits. `shift` is
// floor(4*log2(ratio)). Integrators wrap; only the 16-bit result clips.

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
    logic signed [AW-1:0] s0, s1, s2, s3;
    logic signed [AW-1:0] d0, d1, d2, d3;
    logic signed [AW-1:0] ext;
    logic [5:0] count;

    // Integrators wrap. A saturating accumulator would grow as n^N and
    // then the combs would see a constant and output zero. The width is
    // enough that one decimation period's growth, R^N times full scale,
    // still fits, so the wrapped difference is the true difference.

    function automatic logic signed [15:0] sat16(input logic signed [AW-1:0] v);
        if (v > 40'sd32767) sat16 = 16'sd32767;
        else if (v < -40'sd32768) sat16 = -16'sd32768;
        else sat16 = v[15:0];
    endfunction

    always_comb begin
        ext = {{(AW-16){din[15]}}, din};
        s0 = i0 + ext;
        s1 = i1 + s0;
        s2 = i2 + s1;
        s3 = i3 + s2;
        d0 = s3 - c0;
        d1 = d0 - c1;
        d2 = d1 - c2;
        d3 = d2 - c3;
    end

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
            count <= '0;
            valid_out <= 1'b0;
            dout <= '0;
        end else begin
            valid_out <= 1'b0;
            if (!en) begin
                count <= '0;
            end else if (valid_in && ratio != 6'd0) begin
                i0 <= s0;
                i1 <= s1;
                i2 <= s2;
                i3 <= s3;
                if (count + 6'd1 == ratio) begin
                    count <= '0;
                    c0 <= s3;
                    c1 <= d0;
                    c2 <= d1;
                    c3 <= d2;
                    dout <= sat16(d3 >>> shift);
                    valid_out <= 1'b1;
                end else begin
                    count <= count + 6'd1;
                end
            end
        end
    end

endmodule
