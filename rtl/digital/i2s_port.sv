`timescale 1ns/1ps
// I2S slave, MSB-justified. The host owns bclk and lrclk.
// lrclk 0 is Left / I, lrclk 1 is Right / Q.
// The bclk rise on which lrclk changes is bit 0 and carries the MSB.
// slot_32 = 0: 16 clocks per channel. slot_32 = 1: 32 clocks per channel,
// with the 16-bit sample in the first 16 clocks and zeros after it.
// en low forces dout to 0 and drops incoming samples.

module i2s_port (
    input  logic               clk,
    input  logic               rst_n,
    input  logic               en,
    input  logic               slot_32,
    input  logic               bclk,
    input  logic               lrclk,
    input  logic               din,
    input  logic signed [15:0] i_out,
    input  logic signed [15:0] q_out,
    output logic               dout,
    output logic               frame_done,
    output logic signed [15:0] i_in,
    output logic signed [15:0] q_in
);

    logic bclk_q;
    logic slot_right;
    logic [5:0] bitn;
    logic [15:0] sh;
    logic [15:0] cap;
    logic [4:0] width_m1;

    assign width_m1 = slot_32 ? 5'd31 : 5'd15;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            bclk_q <= 1'b0;
            slot_right <= 1'b0;
            bitn <= 6'd0;
            sh <= 16'h0000;
            cap <= 16'h0000;
            dout <= 1'b0;
            frame_done <= 1'b0;
            i_in <= 16'sd0;
            q_in <= 16'sd0;
        end else begin
            bclk_q <= bclk;
            frame_done <= 1'b0;
            if (!en) begin
                dout <= 1'b0;
                bitn <= 6'd0;
            end else if (bclk && !bclk_q) begin
                if (lrclk != slot_right || bitn == 6'd0) begin
                    slot_right <= lrclk;
                    bitn <= 6'd1;
                    dout <= lrclk ? q_out[15] : i_out[15];
                    sh <= lrclk ? {q_out[14:0], 1'b0} : {i_out[14:0], 1'b0};
                    cap <= {15'b0, din};
                end else begin
                    if (bitn <= 6'd15) begin
                        dout <= sh[15];
                        sh <= {sh[14:0], 1'b0};
                        cap <= {cap[14:0], din};
                    end else begin
                        dout <= 1'b0;
                    end
                    if (bitn == 6'd15) begin
                        if (slot_right) q_in <= {cap[14:0], din};
                        else i_in <= {cap[14:0], din};
                    end
                    if (bitn[4:0] == width_m1) begin
                        bitn <= 6'd0;
                        if (slot_right) frame_done <= 1'b1;
                    end else begin
                        bitn <= bitn + 6'd1;
                    end
                end
            end
        end
    end

endmodule
