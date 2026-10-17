// First-order DC loop. dc <= dc + ((x - dc) >>> shift).
// y = x - dc. shift is clipped to 1..7. en low bypasses the loop.

module dc_offset (
    input  logic               clk,
    input  logic               rst_n,
    input  logic               en,
    input  logic [2:0]         shift,
    input  logic               valid_in,
    input  logic signed [15:0] i_in,
    input  logic signed [15:0] q_in,
    output logic               valid_out,
    output logic signed [15:0] i_out,
    output logic signed [15:0] q_out
);

    logic signed [15:0] dc_i, dc_q;
    logic [2:0] sh;

    assign sh = (shift == 3'd0) ? 3'd1 : shift;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            dc_i <= 16'sd0;
            dc_q <= 16'sd0;
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
                    dc_i <= dc_i + ((i_in - dc_i) >>> sh);
                    dc_q <= dc_q + ((q_in - dc_q) >>> sh);
                    i_out <= i_in - (dc_i + ((i_in - dc_i) >>> sh));
                    q_out <= q_in - (dc_q + ((q_in - dc_q) >>> sh));
                end
            end
        end
    end

endmodule
