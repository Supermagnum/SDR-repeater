`timescale 1ns/1ps
// I2S master. BCLK and LRCLK are derived from clk, which is the
// reference. One LRCLK frame is exactly `frame_clks` reference
// cycles, so the sample rate is ref/frame_clks with no remainder.
// A 16-bit slot uses 32 bit cells per frame. A 32-bit slot uses 64.
// Bit cells are  floor(frame/bits) or one more, spread across the
// frame. Data changes when BCLK rises. The host samples on the fall.
// clk_error is set when a bit cell would be only one reference
// cycle and the cells are not all exactly one cycle. The one exact
// case (32-bit slot, 500 kHz, 32 MHz reference) forwards clk as BCLK.

module i2s_master (
    input  logic               clk,
    input  logic               rst_n,
    input  logic               en,
    input  logic               slot_32,
    input  logic [10:0]        frame_clks,
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

    logic [10:0] frame_cnt;
    logic [6:0]  bit_idx;
    logic [10:0] cell_left;
    logic [10:0] cell_len;
    logic [6:0]  spread;
    // Bit 15 is the bit that shifts out of the capture register.
    /* verilator lint_off UNUSEDSIGNAL */
    logic [15:0] sh_i;
    /* verilator lint_on UNUSEDSIGNAL */
    logic        bclk_r;
    logic        direct;
    logic [10:0] len_c;
    logic [6:0]  next_spread;
    logic [6:0]  this_bit;
    logic        right_c;
    logic        right_nb;
    logic [6:0]  nb;
    logic [6:0]  spread_sum;
    logic [10:0] frame_d;
    logic        slot_d;

    logic [6:0] bits;
    logic [10:0] base;
    logic [5:0] rem;

    assign bits = slot_32 ? 7'd64 : 7'd32;
    assign base = slot_32 ? {6'b0, frame_clks[10:6]} : {5'b0, frame_clks[10:5]};
    assign rem  = slot_32 ? frame_clks[5:0] : {1'b0, frame_clks[4:0]};
    assign direct = (base == 11'd1) && (rem == 6'd0);
    assign clk_error = en && !direct && (base < 11'd2);
    assign bclk = en && (direct ? clk : bclk_r);

    always_comb begin
        spread_sum = spread + {1'b0, rem};
        if (spread_sum >= bits) begin
            next_spread = spread_sum - bits;
            len_c = base + 11'd1;
        end else begin
            next_spread = spread_sum;
            len_c = base;
        end
        this_bit = bit_idx;
        right_c = this_bit >= (bits >> 1);
        nb = (bit_idx == bits - 7'd1) ? 7'd0 : bit_idx + 7'd1;
        right_nb = nb >= (bits >> 1);
    end

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            frame_cnt <= '0;
            bit_idx <= '0;
            cell_left <= '0;
            cell_len <= '0;
            spread <= '0;
            sh_i <= '0;
            bclk_r <= 1'b0;
            lrclk <= 1'b0;
            dout <= 1'b0;
            frame_done <= 1'b0;
            i_in <= '0;
            q_in <= '0;
            frame_d <= '0;
            slot_d <= 1'b0;
        end else begin
            frame_done <= 1'b0;
            // A rate or slot change restarts the divider. Leaving the
            // old cell running used a length from the previous rate.
            if (!en || clk_error || frame_clks != frame_d || slot_32 != slot_d) begin
                frame_d <= frame_clks;
                slot_d <= slot_32;
                frame_cnt <= '0;
                bit_idx <= '0;
                cell_left <= '0;
                cell_len <= '0;
                spread <= '0;
                bclk_r <= 1'b0;
                dout <= 1'b0;
                lrclk <= 1'b0;
            end else if (direct) begin
                // One bit per reference cycle. BCLK is clk.
                if (bit_idx == bits - 7'd1) frame_cnt <= '0;
                else frame_cnt <= frame_cnt + 11'd1;
                bit_idx <= nb;
                lrclk <= right_nb;
                if (nb < 7'd16) begin
                    dout <= i_out[15 - nb[3:0]];
                    sh_i <= {sh_i[14:0], din};
                end else if (!right_nb) begin
                    dout <= 1'b0;
                end else if (nb < (bits >> 1) + 7'd16) begin
                    dout <= q_out[15 - (nb - (bits >> 1))];
                    if ((nb - (bits >> 1)) == 7'd15) q_in <= {sh_i[14:0], din};
                    sh_i <= {sh_i[14:0], din};
                end else begin
                    dout <= 1'b0;
                end
                if (nb == 7'd15) i_in <= {sh_i[14:0], din};
                if (nb == bits - 7'd1) frame_done <= 1'b1;
            end else if (cell_left == 11'd0) begin
                spread <= next_spread;
                cell_len <= len_c;
                cell_left <= len_c - 11'd1;
                bclk_r <= 1'b1;
                lrclk <= right_c;
                if (this_bit < 7'd16) dout <= i_out[15 - this_bit[3:0]];
                else if (!right_c) dout <= 1'b0;
                else if ((this_bit - (bits >> 1)) < 7'd16)
                    dout <= q_out[15 - (this_bit - (bits >> 1))];
                else dout <= 1'b0;
                sh_i <= {sh_i[14:0], din};
                if (this_bit == 7'd15) i_in <= {sh_i[14:0], din};
                if (right_c && (this_bit - (bits >> 1) == 7'd15)) q_in <= {sh_i[14:0], din};
                if (this_bit + 7'd1 == bits) begin
                    bit_idx <= '0;
                    spread <= '0;
                    frame_cnt <= '0;
                    frame_done <= 1'b1;
                end else begin
                    bit_idx <= this_bit + 7'd1;
                    frame_cnt <= frame_cnt + 11'd1;
                end
            end else begin
                cell_left <= cell_left - 11'd1;
                frame_cnt <= frame_cnt + 11'd1;
                // Launch cycle already drove BCLK high. Stay high while
                // the remaining count is still in the first half.
                bclk_r <= (cell_left > (cell_len >> 1));
            end
        end
    end

endmodule
