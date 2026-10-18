`timescale 1ns/1ps
// Multiplier-free first decimator for a 1-bit modulator stream.
// A bit of 1 is +1 and a bit of 0 is -1. Eight coefficients
// [1, 4, 8, 12, 12, 8, 4, 1] are added or subtracted, which is a
// polyphase view of that FIR: no multiplier, and the ratio is 2 or 4.
// The wide CIC integrators see one sample per ratio clocks.

module bit_front (
    input  logic             clk,
    input  logic             rst_n,
    input  logic             en,
    input  logic [2:0]       ratio,
    input  logic             valid_in,
    input  logic             bit_i,
    input  logic             bit_q,
    output logic             valid_out,
    output logic signed [7:0] i_out,
    output logic signed [7:0] q_out
);

    logic [7:0] hist_i, hist_q;
    logic [2:0] count;
    integer k;

    function automatic logic signed [7:0] coef(input logic [2:0] idx);
        case (idx)
            3'd0, 3'd7: coef = 8'sd1;
            3'd1, 3'd6: coef = 8'sd4;
            3'd2, 3'd5: coef = 8'sd8;
            default:    coef = 8'sd12;
        endcase
    endfunction

    function automatic logic signed [7:0] dot(input logic [7:0] hist);
        logic signed [7:0] acc;
        acc = '0;
        for (k = 0; k < 8; k = k + 1)
            acc = acc + (hist[k] ? coef(3'(k)) : -coef(3'(k)));
        dot = acc;
    endfunction

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            hist_i <= '0;
            hist_q <= '0;
            count <= '0;
            valid_out <= 1'b0;
            i_out <= '0;
            q_out <= '0;
        end else begin
            valid_out <= 1'b0;
            if (!en) begin
                count <= '0;
            end else if (valid_in) begin
                hist_i <= {hist_i[6:0], bit_i};
                hist_q <= {hist_q[6:0], bit_q};
                if (count + 3'd1 == ratio) begin
                    count <= '0;
                    // The new bit is in [0] after the shift. dot() sees
                    // the pre-shift history, so fold the new bit in here.
                    i_out <= dot({hist_i[6:0], bit_i});
                    q_out <= dot({hist_q[6:0], bit_q});
                    valid_out <= 1'b1;
                end else begin
                    count <= count + 3'd1;
                end
            end
        end
    end

endmodule
