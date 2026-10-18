`timescale 1ns/1ps
// I2S master. BCLK and LRCLK are divided from the reference.
// Every bit bit_cell is `bit_cell` reference clocks, and `bit_cell` is even, so
// BCLK is high for bit_cell/2 and low for bit_cell/2. The slot width is
// chosen by the rate table. The first 16 bits of a slot are the
// sample, MSB first. Extra slot bits are zero. Clocks stay low when
// clk_bad is set. BCLK is never forwarded from the reference.

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
    logic [5:0]  bitn;
    logic        in_bits;
    logic        right;
    logic [5:0]  in_slot;

    assign clk_error = en && clk_bad;

    always_comb begin
        bit_at = (bit_cell == 3'd4) ? {2'b0, fc[10:2]} : {1'b0, fc[10:1]};
        sub = (bit_cell == 3'd4) ? {8'b0, fc[1:0]} : {9'b0, fc[0]};
        in_bits = fc < ({5'b0, slot} << (bit_cell == 3'd4 ? 3 : 2));
        // active length = 2 * slot * bit_cell. slot<<1 is the bit count,
        // times bit_cell (2 or 4) is another shift.
        right = bit_at >= {5'b0, slot};
        in_slot = right ? bit_at[5:0] - slot : bit_at[5:0];
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
                bclk <= in_bits && (sub < {8'b0, bit_cell[2:1]});
                lrclk <= !(fc == 11'd0 || (in_bits && !right));
                if (in_bits && sub == 11'd0) begin
                    if (in_slot < 6'd16) begin
                        dout <= right ? q_out[15 - in_slot[3:0]] : i_out[15 - in_slot[3:0]];
                        cap <= {cap[14:0], din};
                        if (in_slot == 6'd15) begin
                            if (right) q_in <= {cap[14:0], din};
                            else i_in <= {cap[14:0], din};
                        end
                    end else begin
                        dout <= 1'b0;
                    end
                end else if (!in_bits) begin
                    dout <= 1'b0;
                    bclk <= 1'b0;
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
