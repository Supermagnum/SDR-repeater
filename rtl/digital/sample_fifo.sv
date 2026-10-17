`timescale 1ns/1ps
// Depth-8 async FIFO. Write side is the reference. Read side is BCLK.
// Pointers are gray-coded and synchronized by two flops.
// Overflow and underflow stick until clr.

module sample_fifo (
    input  logic        wr_clk,
    input  logic        rd_clk,
    input  logic        rst_n,
    input  logic        clr,
    input  logic        wr_en,
    input  logic [31:0] wr_data,
    output logic        overflow,
    input  logic        rd_en,
    output logic [31:0] rd_data,
    output logic        underflow
);

    logic [31:0] mem [0:7];
    logic [3:0] wr_bin, rd_bin;
    logic [3:0] wr_gray, rd_gray;
    logic [3:0] wr_gray_s1, wr_gray_s2;
    logic [3:0] rd_gray_s1, rd_gray_s2;
    logic wr_full, rd_empty;
    logic clr_req, clr_ack;
    logic clr_req_s1, clr_req_s2;
    logic clr_ack_s1, clr_ack_s2;

    function automatic logic [3:0] bin2gray(input logic [3:0] b);
        bin2gray = b ^ (b >> 1);
    endfunction

    assign wr_full = (wr_gray == {~rd_gray_s2[3:2], rd_gray_s2[1:0]});
    assign rd_empty = (rd_gray == wr_gray_s2);

    always_ff @(posedge wr_clk or negedge rst_n) begin
        if (!rst_n) begin
            wr_bin <= '0;
            wr_gray <= '0;
            rd_gray_s1 <= '0;
            rd_gray_s2 <= '0;
            overflow <= 1'b0;
            clr_req <= 1'b0;
            clr_ack_s1 <= 1'b0;
            clr_ack_s2 <= 1'b0;
        end else begin
            rd_gray_s1 <= rd_gray;
            rd_gray_s2 <= rd_gray_s1;
            clr_ack_s1 <= clr_ack;
            clr_ack_s2 <= clr_ack_s1;
            if (clr) clr_req <= 1'b1;
            else if (clr_ack_s2) clr_req <= 1'b0;
            if (clr || clr_req) overflow <= 1'b0;
            if (wr_en) begin
                if (wr_full) overflow <= 1'b1;
                else begin
                    mem[wr_bin[2:0]] <= wr_data;
                    wr_bin <= wr_bin + 4'd1;
                    wr_gray <= bin2gray(wr_bin + 4'd1);
                end
            end
        end
    end

    always_ff @(posedge rd_clk or negedge rst_n) begin
        if (!rst_n) begin
            rd_bin <= '0;
            rd_gray <= '0;
            wr_gray_s1 <= '0;
            wr_gray_s2 <= '0;
            rd_data <= '0;
            underflow <= 1'b0;
            clr_ack <= 1'b0;
            clr_req_s1 <= 1'b0;
            clr_req_s2 <= 1'b0;
        end else begin
            wr_gray_s1 <= wr_gray;
            wr_gray_s2 <= wr_gray_s1;
            clr_req_s1 <= clr_req;
            clr_req_s2 <= clr_req_s1;
            clr_ack <= clr_req_s2;
            if (clr_req_s2) underflow <= 1'b0;
            else if (rd_en) begin
                if (rd_empty) begin
                    underflow <= 1'b1;
                    rd_data <= '0;
                end else begin
                    rd_data <= mem[rd_bin[2:0]];
                    rd_bin <= rd_bin + 4'd1;
                    rd_gray <= bin2gray(rd_bin + 4'd1);
                end
            end
        end
    end

endmodule
