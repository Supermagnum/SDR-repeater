`timescale 1ns/1ps
// I2S slave, Philips (standard I2S) format. BCLK and LRCLK belong to the
// host and are asynchronous to the reference; IQ words cross in
// sample_fifo. The host changes LRCLK and DIN on the BCLK falling edge and
// samples DOUT on the rising edge. This module samples LRCLK and DIN on the
// rising edge and drives DOUT on the falling edge. A channel's MSB is in
// the bit cell after the LRCLK change. The next IQ pair is fetched from the
// FIFO at the start of the right channel and presented from the start of
// the next left channel. Empty fetch raises underflow and sends zeros. A
// write into a full FIFO raises overflow. The frame length follows the
// host's LRCLK, so `slot` is not used here.

module i2s_slave (
    input  logic               clk,
    input  logic               rst_n,
    input  logic               en,
    input  logic [5:0]         slot,
    input  logic               sample_valid,
    input  logic signed [15:0] i_out,
    input  logic signed [15:0] q_out,
    input  logic               clr_flags,
    input  logic               bclk,
    input  logic               lrclk,
    input  logic               din,
    output logic               dout,
    output logic               overflow,
    output logic               underflow,
    output logic signed [15:0] i_in,
    output logic signed [15:0] q_in
);

    logic rd_en;
    logic [31:0] rd_data;
    logic [15:0] hold_i, hold_q, nxt_i, nxt_q;
    logic [5:0] k_r;      // bit index of the next cell (63 = idle)
    logic ch_r;           // channel of that bit: 0 left, 1 right
    logic lr_q;
    logic use_next;
    logic change;
    /* verilator lint_off UNUSEDSIGNAL */
    logic [15:0] cap;
    logic [5:0] slot_unused;
    /* verilator lint_on UNUSEDSIGNAL */

    assign slot_unused = slot;
    assign change = (lrclk != lr_q);

    sample_fifo u_fifo (
        .wr_clk(clk),
        .rd_clk(bclk),
        .rst_n(rst_n),
        .clr(clr_flags),
        .wr_en(en && sample_valid),
        .wr_data({i_out, q_out}),
        .overflow(overflow),
        .rd_en(rd_en),
        .rd_data(rd_data),
        .underflow(underflow)
    );

    always_ff @(posedge bclk or negedge rst_n) begin
        if (!rst_n) begin
            rd_en <= 1'b0;
            hold_i <= '0;
            hold_q <= '0;
            nxt_i <= '0;
            nxt_q <= '0;
            k_r <= 6'd63;
            ch_r <= 1'b0;
            cap <= '0;
            lr_q <= 1'b0;
            use_next <= 1'b0;
            i_in <= '0;
            q_in <= '0;
        end else begin
            rd_en <= 1'b0;
            lr_q <= lrclk;
            if (use_next) begin
                nxt_i <= rd_data[31:16];
                nxt_q <= rd_data[15:0];
                use_next <= 1'b0;
            end
            if (!en) begin
                k_r <= 6'd63;
            end else begin
                // Capture the bit of the cell sampled now (k_r, ch_r before update).
                if (k_r < 6'd16) begin
                    cap <= {cap[14:0], din};
                    if (k_r == 6'd15) begin
                        if (ch_r) q_in <= {cap[14:0], din};
                        else i_in <= {cap[14:0], din};
                    end
                end
                if (change) begin
                    k_r <= 6'd0;
                    ch_r <= lrclk;
                    if (lrclk) begin
                        rd_en <= 1'b1;      // right channel starts: fetch the next pair
                        use_next <= 1'b1;
                    end else begin
                        hold_i <= nxt_i;    // left channel starts: present it
                        hold_q <= nxt_q;
                    end
                end else if (k_r != 6'd63) begin
                    k_r <= k_r + 6'd1;
                end
            end
        end
    end

    always_ff @(negedge bclk or negedge rst_n) begin
        if (!rst_n) dout <= 1'b0;
        else if (!en || k_r >= 6'd16) dout <= 1'b0;
        else dout <= ch_r ? hold_q[4'd15 - k_r[3:0]] : hold_i[4'd15 - k_r[3:0]];
    end

endmodule
