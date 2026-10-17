`timescale 1ns/1ps
// Power-of-two boxcar decimator for one I/Q stream.
// ratio_sel 0, 1, 2, 3 selects N = 1, 2, 4, 8.
// When en is low the block is powered down and samples pass through.

module decim_iq (
    input  logic               clk,
    input  logic               rst_n,
    input  logic               en,
    input  logic [1:0]         ratio_sel,
    input  logic               valid_in,
    input  logic signed [15:0] i_in,
    input  logic signed [15:0] q_in,
    output logic               valid_out,
    output logic signed [15:0] i_out,
    output logic signed [15:0] q_out
);

    logic [3:0] n;
    logic [3:0] count;
    logic signed [18:0] acc_i, acc_q;

    assign n = (ratio_sel == 2'd0) ? 4'd1 :
               (ratio_sel == 2'd1) ? 4'd2 :
               (ratio_sel == 2'd2) ? 4'd4 : 4'd8;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            count <= 4'd0;
            acc_i <= 19'sd0;
            acc_q <= 19'sd0;
            valid_out <= 1'b0;
            i_out <= 16'sd0;
            q_out <= 16'sd0;
        end else begin
            valid_out <= 1'b0;
            if (!en) begin
                count <= 4'd0;
                acc_i <= 19'sd0;
                acc_q <= 19'sd0;
                if (valid_in) begin
                    valid_out <= 1'b1;
                    i_out <= i_in;
                    q_out <= q_in;
                end
            end else if (valid_in) begin
                if (count + 4'd1 == n) begin
                    valid_out <= 1'b1;
                    i_out <= (acc_i + i_in) >>> ratio_sel;
                    q_out <= (acc_q + q_in) >>> ratio_sel;
                    acc_i <= 19'sd0;
                    acc_q <= 19'sd0;
                    count <= 4'd0;
                end else begin
                    acc_i <= acc_i + i_in;
                    acc_q <= acc_q + q_in;
                    count <= count + 4'd1;
                end
            end
        end
    end

endmodule
