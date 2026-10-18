`timescale 1ns/1ps
// I2S slave. BCLK and LRCLK belong to the host and are asynchronous
// to the reference. IQ words cross in sample_fifo.
// The shifter is in the BCLK domain. A word is prefetched at the
// start of Left and used on the next frame, so the slave path has
// one frame of latency. Empty prefetch raises underflow and sends
// zeros. A write into a full FIFO raises overflow.

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
    logic [15:0] hold_i, hold_q;
    logic [5:0] bitn;
    // cap[15] is the bit that shifts out of the DIN capture register.
    /* verilator lint_off UNUSEDSIGNAL */
    logic [15:0] sh, cap;
    /* verilator lint_on UNUSEDSIGNAL */
    logic lr_q;
    logic use_next;

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
            bitn <= '0;
            sh <= '0;
            cap <= '0;
            lr_q <= 1'b0;
            use_next <= 1'b0;
            dout <= 1'b0;
            i_in <= '0;
            q_in <= '0;
        end else begin
            rd_en <= 1'b0;
            lr_q <= lrclk;
            if (use_next) begin
                hold_i <= rd_data[31:16];
                hold_q <= rd_data[15:0];
                use_next <= 1'b0;
            end
            if (!en) begin
                dout <= 1'b0;
                bitn <= '0;
            end else if (lrclk != lr_q || bitn == 6'd0) begin
                bitn <= 6'd1;
                if (lr_q && !lrclk) begin
                    rd_en <= 1'b1;
                    use_next <= 1'b1;
                end
                dout <= !lrclk ? hold_i[15] : hold_q[15];
                sh <= !lrclk ? {hold_i[14:0], 1'b0} : {hold_q[14:0], 1'b0};
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
                    if (lrclk) q_in <= {cap[14:0], din};
                    else i_in <= {cap[14:0], din};
                end
                if (bitn + 6'd1 == {1'b0, slot}) bitn <= '0;
                else bitn <= bitn + 6'd1;
            end
        end
    end

endmodule
