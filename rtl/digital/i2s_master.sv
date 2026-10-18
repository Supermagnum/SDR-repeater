`timescale 1ns/1ps
// I2S master, Philips (standard I2S) format.
// BCLK and LRCLK are divided from the reference. Every bit cell is
// `bit_cell` reference clocks (2 or 4). BCLK is low in the first half of
// a cell and high in the second half, so DOUT and LRCLK change on the BCLK
// falling edge and the receiver samples on the rising edge. DIN from the
// host is captured on the rising edge.
// LRCLK low = left (I), high = right (Q). LRCLK changes one bit cell before
// each channel's MSB. The first 16 bits of a channel are the sample, MSB
// first; extra slot bits are zero. With 16-bit slots the right-channel LSB
// falls in cell 0 of the next frame, so the frame's words are latched into
// shadow registers at cell 0. Clocks stay low when clk_bad is set. BCLK is
// never forwarded from the reference.

module i2s_master (
    input  logic               clk,
    input  logic               rst_n,
    input  logic               en,
    input  logic [5:0]         slot,
    input  logic [2:0]         bit_cell,
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

    logic [10:0] fc;
    logic [15:0] cap;
    logic [10:0] frame_d;
    logic [5:0]  slot_d;
    logic [10:0] bit_at;
    logic [10:0] sub;
    logic [10:0] half;
    logic        in_bits;
    logic        right;
    logic [10:0] e;
    logic        d_right;
    logic [5:0]  k;
    logic [15:0] i_sh, q_sh;

    assign clk_error = en && clk_bad;

    always_comb begin
        bit_at = (bit_cell == 3'd4) ? {2'b0, fc[10:2]} : {1'b0, fc[10:1]};
        sub = (bit_cell == 3'd4) ? {9'b0, fc[1:0]} : {10'b0, fc[0]};
        half = {9'b0, bit_cell[2:1]};
        in_bits = fc < ({5'b0, slot} << (bit_cell == 3'd4 ? 3 : 2));
        right = bit_at >= {5'b0, slot};
        // Philips: the bit in cell b is position b-1. Cell 0 carries the
        // last bit of the previous frame's right channel.
        e = (bit_at == 11'd0) ? (({5'b0, slot} << 1) - 11'd1) : (bit_at - 11'd1);
        d_right = e >= {5'b0, slot};
        k = d_right ? 6'(e - {5'b0, slot}) : e[5:0];
    end

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            fc <= '0;
            cap <= '0;
            bclk <= 1'b0;
            lrclk <= 1'b0;
            dout <= 1'b0;
            frame_done <= 1'b0;
            i_in <= '0;
            q_in <= '0;
            frame_d <= '0;
            slot_d <= '0;
            i_sh <= '0;
            q_sh <= '0;
        end else begin
            frame_done <= 1'b0;
            if (!en || clk_bad || frame_clks != frame_d || slot != slot_d) begin
                frame_d <= frame_clks;
                slot_d <= slot;
                fc <= '0;
                bclk <= 1'b0;
                lrclk <= 1'b0;
                dout <= 1'b0;
            end else begin
                bclk <= in_bits && (sub >= half);
                lrclk <= !(fc == 11'd0 || (in_bits && !right));
                if (in_bits && sub == 11'd0) begin
                    // BCLK falling edge: present the next bit.
                    if (bit_at == 11'd0) begin
                        i_sh <= i_out;
                        q_sh <= q_out;
                    end
                    if (k < 6'd16)
                        dout <= d_right ? q_sh[4'd15 - k[3:0]] : i_sh[4'd15 - k[3:0]];
                    else
                        dout <= 1'b0;
                end else if (!in_bits) begin
                    dout <= 1'b0;
                end
                if (in_bits && sub == half && k < 6'd16) begin
                    // BCLK rising edge: capture the host's bit.
                    cap <= {cap[14:0], din};
                    if (k == 6'd15) begin
                        if (d_right) q_in <= {cap[14:0], din};
                        else i_in <= {cap[14:0], din};
                    end
                end
                if (fc + 11'd1 == frame_clks) begin
                    fc <= '0;
                    frame_done <= 1'b1;
                end else begin
                    fc <= fc + 11'd1;
                end
            end
        end
    end

endmodule
