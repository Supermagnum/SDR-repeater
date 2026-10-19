`timescale 1ns/1ps
// I2S master, Philips (standard I2S) format, continuous BCLK.
// A bit cell is `bit_cell` reference clocks (2..63) and a frame is exactly
// 2 * slot cells, so BCLK runs without gaps and frame_clks = 2*slot*bit_cell
// (guaranteed by rate_table). BCLK is low for the first bit_cell/2 clocks of
// a cell and high for the rest, so DOUT and LRCLK change on the BCLK falling
// edge and the receiver samples on the rising edge. DIN from the host is
// captured on the rising edge.
// LRCLK low = left (I), high = right (Q); it changes one bit cell before each
// channel's MSB. The first 16 bits of a channel are the sample, MSB first;
// extra slot bits are zero. With 16-bit slots the right-channel LSB falls in
// cell 0 of the next frame, so the frame's words are latched into shadow
// registers at cell 0. Clocks stay low when clk_bad is set. BCLK is never
// forwarded from the reference.

module i2s_master (
    input  logic               clk,
    input  logic               rst_n,
    input  logic               en,
    input  logic [5:0]         slot,
    input  logic [5:0]         bit_cell,
    input  logic [10:0]        frame_clks,
    input  logic               clk_bad,
    input  logic signed [15:0] i_out,
    input  logic signed [15:0] q_out,
    input  logic               din,
    output logic               bclk,
    output logic               lrclk,
    output logic               dout,
    output logic               clk_error,
    output logic               frame_done,
    output logic signed [15:0] i_in,
    output logic signed [15:0] q_in
);

    logic [5:0]  sub;         // reference clock within the cell
    logic [6:0]  bit_at;      // cell within the frame, 0..2*slot-1
    logic [5:0]  half;
    logic        right;
    logic [6:0]  e;
    logic        d_right;
    logic [5:0]  k;
    logic        cell_end, frame_end;
    logic [10:0] frame_d;
    logic [5:0]  slot_d, cell_d;
    // cap[15] is the bit that shifts out; it is never read.
    /* verilator lint_off UNUSEDSIGNAL */
    logic [15:0] cap;
    /* verilator lint_on UNUSEDSIGNAL */
    logic [15:0] i_sh, q_sh;

    assign clk_error = en && clk_bad;

    always_comb begin
        half = {1'b0, bit_cell[5:1]};
        right = bit_at >= {1'b0, slot};
        // Philips: the bit in cell b is position b-1. Cell 0 carries the
        // last bit of the previous frame's right channel.
        e = (bit_at == 7'd0) ? (({1'b0, slot} << 1) - 7'd1) : (bit_at - 7'd1);
        d_right = e >= {1'b0, slot};
        k = d_right ? 6'(e - {1'b0, slot}) : e[5:0];
        cell_end = (sub + 6'd1 == bit_cell);
        frame_end = cell_end && (bit_at + 7'd1 == ({1'b0, slot} << 1));
    end

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            sub <= '0;
            bit_at <= '0;
            cap <= '0;
            bclk <= 1'b0;
            lrclk <= 1'b0;
            dout <= 1'b0;
            frame_done <= 1'b0;
            i_in <= '0;
            q_in <= '0;
            frame_d <= '0;
            slot_d <= '0;
            cell_d <= '0;
            i_sh <= '0;
            q_sh <= '0;
        end else begin
            frame_done <= 1'b0;
            if (!en || clk_bad || frame_clks != frame_d || slot != slot_d || bit_cell != cell_d) begin
                frame_d <= frame_clks;
                slot_d <= slot;
                cell_d <= bit_cell;
                sub <= '0;
                bit_at <= '0;
                bclk <= 1'b0;
                lrclk <= 1'b0;
                dout <= 1'b0;
            end else begin
                bclk <= (sub >= half);
                lrclk <= right;
                if (sub == 6'd0) begin
                    // BCLK falling edge: present the next bit.
                    if (bit_at == 7'd0) begin
                        i_sh <= i_out;
                        q_sh <= q_out;
                    end
                    if (k < 6'd16)
                        dout <= d_right ? q_sh[4'd15 - k[3:0]] : i_sh[4'd15 - k[3:0]];
                    else
                        dout <= 1'b0;
                end
                if (sub == half && k < 6'd16) begin
                    // BCLK rising edge: capture the host's bit.
                    cap <= {cap[14:0], din};
                    if (k == 6'd15) begin
                        if (d_right) q_in <= {cap[14:0], din};
                        else i_in <= {cap[14:0], din};
                    end
                end
                frame_done <= frame_end;
                if (cell_end) begin
                    sub <= '0;
                    bit_at <= frame_end ? 7'd0 : bit_at + 7'd1;
                end else begin
                    sub <= sub + 6'd1;
                end
            end
        end
    end

endmodule
