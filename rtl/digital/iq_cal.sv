// IQ calibration. gain 128 means 1.0. phase is a signed cross term
// in the same units: yI = (gain_i * xI + phase * xQ) / 128,
// yQ = (gain_q * xQ) / 128. Results saturate to signed 16 bit.
// en low bypasses the block.

module iq_cal (
    input  logic               clk,
    input  logic               rst_n,
    input  logic               en,
    input  logic [7:0]         gain_i,
    input  logic [7:0]         gain_q,
    input  logic signed [7:0]  phase,
    input  logic               valid_in,
    input  logic signed [15:0] i_in,
    input  logic signed [15:0] q_in,
    output logic               valid_out,
    output logic signed [15:0] i_out,
    output logic signed [15:0] q_out
);

    function automatic logic signed [15:0] sat(input logic signed [24:0] v);
        if (v > 25'sd32767) sat = 16'sd32767;
        else if (v < -25'sd32768) sat = -16'sd32768;
        else sat = v[15:0];
    endfunction

    logic signed [24:0] si, sq, yi, yq;

    always_comb begin
        si = i_in;
        sq = q_in;
        yi = (si * $signed({1'b0, gain_i}) + sq * phase) >>> 7;
        yq = (sq * $signed({1'b0, gain_q})) >>> 7;
    end

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            valid_out <= 1'b0;
            i_out <= 16'sd0;
            q_out <= 16'sd0;
        end else begin
            valid_out <= 1'b0;
            if (valid_in) begin
                valid_out <= 1'b1;
                if (!en) begin
                    i_out <= i_in;
                    q_out <= q_in;
                end else begin
                    i_out <= sat(yi);
                    q_out <= sat(yq);
                end
            end
        end
    end

endmodule
