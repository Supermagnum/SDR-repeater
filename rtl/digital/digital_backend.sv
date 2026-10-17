`timescale 1ns/1ps

// Phase 1 digital back end for one RX/TX chain.
// clk is the reference, 32 MHz or 36 MHz. ref_36 selects the divider table.
// I2S master is the default: the chip drives BCLK and LRCLK.
// Slave mode is ctrl[4]. The register map is frozen at this gate.
// Tank Q is not an input.

module digital_backend #(
    parameter int RELOCK_CYCLES = 64
) (
    input  logic               clk,
    input  logic               rst_n,
    input  logic               ref_36,
    input  logic               sclk,
    input  logic               cs_n,
    input  logic               mosi,
    output logic               miso,
    input  logic               bclk_i,
    input  logic               lrclk_i,
    input  logic               din,
    output logic               bclk_o,
    output logic               lrclk_o,
    output logic               bclk_oe,
    output logic               lrclk_oe,
    output logic               dout,
    output logic               valid_iq,
    input  logic               adc_valid,
    input  logic        [15:0] adc_i,
    input  logic        [15:0] adc_q,
    output logic               dac_valid,
    output logic        [15:0] dac_i,
    output logic        [15:0] dac_q,
    output logic               dac_bit_i,
    output logic               dac_bit_q,
    output logic               dac_bit_valid
);

    // Register bytes are wider than the fields the back end decodes.
    // ctrl[7] is a write-1 flag clear and is not stored. ctrl[6:5] are reserved.
    // rate and dc_shift use the low bits. block_pd[7:4] is reserved.
    // band is the analog divider select; it is not consumed in this netlist.
    /* verilator lint_off UNUSEDSIGNAL */
    logic [7:0] ctrl, duty_on, duty_off, rate, dc_shift;
    logic [7:0] gain_i, gain_q, phase, block_pd, wake_cycles, band, status;
    logic [7:0] tx_dc_i, tx_dc_q, tx_gain_i, tx_gain_q, tx_phase, clk_gate;
    /* verilator lint_on UNUSEDSIGNAL */
    logic flag_clear, dc_clear, band_write;
    logic rx_en, tx_en, blank;
    logic [1:0] status_mode;
    logic [10:0] frame_clks;
    logic [5:0] r1, r2;
    logic [4:0] sh1, sh2;
    logic signed [15:0] norm;
    logic decim_v, dc_v, cal_v;
    logic signed [15:0] decim_i, decim_q, dc_i, dc_q, cal_i, cal_q;
    logic signed [15:0] i_hold, q_hold;
    logic sample_valid;
    logic slave_mode;
    logic clk_error, frame_done;
    logic m_bclk, m_lrclk, m_dout;
    logic s_dout, fifo_over, fifo_under;
    logic signed [15:0] m_i_in, m_q_in, s_i_in, s_q_in;
    logic [15:0] relock_cnt;
    logic relock_busy;

    assign slave_mode = ctrl[4];
    assign status = {relock_busy, clk_error, fifo_under, fifo_over, sample_valid, blank, status_mode};
    assign valid_iq = sample_valid;
    assign bclk_oe = !slave_mode && (rx_en || tx_en);
    assign lrclk_oe = bclk_oe;
    assign bclk_o = bclk_oe ? m_bclk : 1'b0;
    assign lrclk_o = bclk_oe ? m_lrclk : 1'b0;
    assign dout = slave_mode ? s_dout : m_dout;
    assign dac_valid = (slave_mode ? 1'b0 : frame_done) && tx_en && !blank;
    assign dac_i = slave_mode ? s_i_in : m_i_in;
    assign dac_q = slave_mode ? s_q_in : m_q_in;

    spi_regs u_spi (
        .clk(clk), .rst_n(rst_n), .sclk(sclk), .cs_n(cs_n), .mosi(mosi), .miso(miso),
        .status(status), .ctrl(ctrl), .duty_on(duty_on), .duty_off(duty_off),
        .rate(rate), .dc_shift(dc_shift), .gain_i(gain_i), .gain_q(gain_q),
        .phase(phase), .block_pd(block_pd), .wake_cycles(wake_cycles), .band(band),
        .flag_clear(flag_clear), .dc_clear(dc_clear), .band_write(band_write),
        .tx_dc_i(tx_dc_i), .tx_dc_q(tx_dc_q), .tx_gain_i(tx_gain_i),
        .tx_gain_q(tx_gain_q), .tx_phase(tx_phase), .clk_gate(clk_gate)
    );

    rate_table u_rate (
        .ref_36(ref_36), .rate(rate[2:0]), .frame_clks(frame_clks),
        .r1(r1), .r2(r2), .sh1(sh1), .sh2(sh2), .norm(norm)
    );

    power_ctrl u_pwr (
        .clk(clk), .rst_n(rst_n), .mode(ctrl[1:0]), .duty_en(ctrl[2]),
        .duty_on(duty_on), .duty_off(duty_off), .wake_cycles(wake_cycles),
        .frame_tick(slave_mode ? cal_v : frame_done),
        .rx_en(rx_en), .tx_en(tx_en), .blank(blank),
        .status_mode(status_mode)
    );

    // Enables are registered on the free clock. The latch inside
    // clk_gate samples them while clk is low.
    logic rx_run, i2s_run, tx_run;
    logic clk_rx, clk_i2s, clk_tx;
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            rx_run <= 1'b0;
            i2s_run <= 1'b0;
            tx_run <= 1'b0;
        end else begin
            // During a duty-cycled off frame the CIC and FIR stop.
            // Bypass (block_pd[0]) keeps the clock so the bypass
            // register still passes samples. SPI is not gated.
            // clk_gate[0] is the CIC allow, [1] is the FIR allow.
            // They share one clock, so either bit stops the chain.
            rx_run <= clk_gate[0] && clk_gate[1] && rx_en && (block_pd[0] || !(ctrl[2] && blank));
            i2s_run <= clk_gate[3] && (rx_en || tx_en);
            tx_run <= clk_gate[4] && tx_en && !block_pd[4];
        end
    end
    clk_gate u_g_rx (.clk(clk), .en(rx_run), .gclk(clk_rx));
    clk_gate u_g_i2s (.clk(clk), .en(i2s_run), .gclk(clk_i2s));
    clk_gate u_g_tx (.clk(clk), .en(tx_run), .gclk(clk_tx));

    decim_chain u_decim (
        .clk(clk_rx), .rst_n(rst_n), .en(!block_pd[0]),
        .r1(r1), .r2(r2), .sh1(sh1), .sh2(sh2), .norm(norm),
        .valid_in(adc_valid && rx_en), .i_in(adc_i), .q_in(adc_q),
        .valid_out(decim_v), .i_out(decim_i), .q_out(decim_q)
    );

    dc_offset u_dc (
        .clk(clk_rx), .rst_n(rst_n), .en(!block_pd[1] && clk_gate[2]), .clear(dc_clear),
        .shift(dc_shift[2:0]), .valid_in(decim_v), .i_in(decim_i), .q_in(decim_q),
        .valid_out(dc_v), .i_out(dc_i), .q_out(dc_q)
    );

    iq_cal u_cal (
        .clk(clk_rx), .rst_n(rst_n), .en(!block_pd[2] && clk_gate[2]),
        .gain_i(gain_i), .gain_q(gain_q), .phase(phase),
        .valid_in(dc_v), .i_in(dc_i), .q_in(dc_q),
        .valid_out(cal_v), .i_out(cal_i), .q_out(cal_q)
    );

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            i_hold <= '0;
            q_hold <= '0;
            sample_valid <= 1'b0;
            relock_cnt <= '0;
            relock_busy <= 1'b0;
        end else begin
            if (band_write) begin
                relock_cnt <= 16'(RELOCK_CYCLES);
                relock_busy <= 1'b1;
            end else if (relock_cnt != 16'd0) begin
                relock_cnt <= relock_cnt - 16'd1;
                if (relock_cnt == 16'd1) relock_busy <= 1'b0;
            end
            if (!rx_en && !tx_en) sample_valid <= 1'b0;
            else if (cal_v) begin
                i_hold <= blank ? 16'sd0 : cal_i;
                q_hold <= blank ? 16'sd0 : cal_q;
                sample_valid <= !blank;
            end
        end
    end

    i2s_master u_master (
        .clk(clk_i2s), .rst_n(rst_n), .en(!slave_mode && !block_pd[3] && (rx_en || tx_en)),
        .slot_32(ctrl[3]), .frame_clks(frame_clks),
        .i_out(i_hold), .q_out(q_hold), .din(din),
        .bclk(m_bclk), .lrclk(m_lrclk), .dout(m_dout),
        .clk_error(clk_error), .frame_done(frame_done),
        .i_in(m_i_in), .q_in(m_q_in)
    );

    i2s_slave u_slave (
        .clk(clk), .rst_n(rst_n), .en(slave_mode && !block_pd[3] && (rx_en || tx_en)),
        .slot_32(ctrl[3]), .sample_valid(cal_v && !blank),
        .i_out(cal_i), .q_out(cal_q), .clr_flags(flag_clear),
        .bclk(bclk_i), .lrclk(lrclk_i), .din(din),
        .dout(s_dout), .overflow(fifo_over), .underflow(fifo_under),
        .i_in(s_i_in), .q_in(s_q_in)
    );

    tx_chain u_tx (
        .clk(clk_tx), .rst_n(rst_n), .en(tx_en && !blank && !block_pd[4]),
        .valid_in(dac_valid),
        .i_in(dac_i), .q_in(dac_q),
        .dc_i(tx_dc_i), .dc_q(tx_dc_q),
        .gain_i(tx_gain_i), .gain_q(tx_gain_q), .phase(tx_phase),
        .frame_clks(frame_clks),
        .dac_bit_i(dac_bit_i), .dac_bit_q(dac_bit_q), .dac_bit_valid(dac_bit_valid)
    );

endmodule
