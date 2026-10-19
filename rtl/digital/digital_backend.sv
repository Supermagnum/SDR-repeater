`timescale 1ns/1ps

// Phase 1 digital back end for one RX/TX chain.
// clk is the reference, 32 MHz or 36 MHz. It may be stopped in
// shutdown. SPI is clocked by SCLK and raises clk_req when a write
// selects standby, RX, or TX. The register map is not frozen:
// CTRL[3] is reserved and the I2S slot width comes from the rate.
// Three root clock gates (run, RX, TX). Blocks use clock enables.
// The library ICG cells stay dont_use.
// DC and IQ correction are done by the host since 2026-10-18 (area
// decision (a)); the RX word is the half-band (or decimator) output.
// SX1255 pin-out (Option P, 2026-10-19): ref_36 is the pin-11 strap and is
// latched while reset is active; ptt_pin (DIO3) gates TX when CTRL[3] is
// set; irq_n (DIO1) is low while an enabled condition holds. The active-high
// RESET pin, its pull-down and the power-on reset are at chip top and drive
// rst_n here.

module digital_backend #(
    parameter int RELOCK_CYCLES = 64
) (
    input  logic               clk,
    input  logic               rst_n,
    input  logic               ref_36,
    input  logic               ptt_pin,
    input  logic               pll_lock,
    output logic               irq_n,
    input  logic               sclk,
    // cs_n is both a synchronous frame qualifier and the asynchronous clear
    // of the SPI bit counter (aborted-frame recovery); timed against sclk in the SDC.
    /* verilator lint_off SYNCASYNCNET */
    input  logic               cs_n,
    /* verilator lint_on SYNCASYNCNET */
    input  logic               mosi,
    output logic               miso,
    output logic               clk_req,
    output logic               band_sel,
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
    input  logic               adc_bit_i,
    input  logic               adc_bit_q,
    // Used only while the decimator is powered down (block_pd[0]).
    input  logic        [15:0] adc_i,
    input  logic        [15:0] adc_q,
    output logic               dac_valid,
    output logic        [15:0] dac_i,
    output logic        [15:0] dac_q,
    output logic               dac_bit_i,
    output logic               dac_bit_q,
    output logic               dac_bit_valid
);

    /* verilator lint_off UNUSEDSIGNAL */
    logic [7:0] ctrl, duty_on, duty_off, rate;
    logic [7:0] block_pd, wake_cycles, band, status, clk_gate;
    /* verilator lint_on UNUSEDSIGNAL */
    logic flag_tog, band_tog, cfg_tog;
    logic rx_en, tx_en, blank;
    logic [1:0] status_mode;
    logic [10:0] frame_clks;
    logic [2:0] r0;
    logic [5:0] r1, r2, slot;
    logic [4:0] sh1, sh2;
    logic [5:0] bit_cell;
    logic rate_error;
    logic signed [15:0] norm;
    logic decim_v, rx_v;
    logic signed [15:0] decim_i, decim_q, rx_i, rx_q;
    logic signed [15:0] i_hold, q_hold;
    logic sample_valid;
    logic slave_mode;
    logic clk_error, frame_done;
    logic m_bclk, m_lrclk, m_dout;
    logic s_dout, fifo_over, fifo_under;
    logic signed [15:0] m_i_in, m_q_in, s_i_in, s_q_in;
    localparam int RW = $clog2(RELOCK_CYCLES + 1);
    logic [RW-1:0] relock_cnt;
    logic relock_busy;
    logic flag_clear, band_write;
    logic ref_36_l;
    logic ptt_s1, ptt_s, lock_s1, lock_s;
    logic [3:0] irq_en, irq_en_c;
    logic [1:0] mode_eff;
    logic flag_t1, flag_t2, band_t1, band_t2, cfg_t1, cfg_t2;
    // Register copies are full bytes; unused bits are reserved:
    // CTRL[7:5,3], RATE[7:3], BLOCK_PD[7:5,2:1], BAND[7:1],
    // CLK_GATE[7:5,2:1] (CLK_GATE[1] 'FIR allow' is reserved: the shared FIR
    // engine runs on the run clock; BLOCK_PD[2:1] and CLK_GATE[2] were the
    // DC loop and IQ cal, removed 2026-10-18).
    /* verilator lint_off UNUSEDSIGNAL */
    logic [7:0] ctrl_c, duty_on_c, duty_off_c, rate_c;
    logic [7:0] block_pd_c, wake_c, band_c, clk_gate_c;
    /* verilator lint_on UNUSEDSIGNAL */
    logic run_en, rx_run, tx_run;
    logic clk_run, clk_rx, clk_tx;
    logic front_v;
    logic signed [7:0] front_i, front_q;
    logic fir_v, tx_mac_v, tx_mac_done;
    logic signed [15:0] fir_i, fir_q, tx_mac_i, tx_mac_q;
    logic signed [15:0] ye_i, yo_i, ye_q, yo_q;
    logic signed [27:0] ta0, tb0, ta1, tb1, ta2, tb2, ta3, tb3;
    logic signed [27:0] ts0, ts1, ts2, ts3;
    wire filt_rx = !block_pd_c[0] && !tx_en;

    assign slave_mode = ctrl_c[4];
    // LO divider select for the analogue block: 0 = /8 (70 cm), 1 = /24 (2 m).
    assign band_sel = band_c[0];
    assign status = {relock_busy, clk_error, fifo_under, fifo_over, sample_valid, blank, status_mode};
    // PTT gate: with CTRL[3] set, TX mode runs only while ptt_pin is high;
    // otherwise the core holds standby (reference and SPI stay up).
    assign mode_eff = (ctrl_c[1:0] == 2'b11 && ctrl_c[3] && !ptt_s) ? 2'b01 : ctrl_c[1:0];
    assign valid_iq = sample_valid;
    assign bclk_oe = !slave_mode && (rx_en || tx_en);
    assign lrclk_oe = bclk_oe;
    assign bclk_o = bclk_oe ? m_bclk : 1'b0;
    assign lrclk_o = bclk_oe ? m_lrclk : 1'b0;
    assign dout = slave_mode ? s_dout : m_dout;
    assign dac_valid = (slave_mode ? 1'b0 : frame_done) && tx_en && !blank;
    assign dac_i = slave_mode ? s_i_in : m_i_in;
    assign dac_q = slave_mode ? s_q_in : m_q_in;

    // Reset synchroniser: rst_n asserts asynchronously and is released
    // two clk cycles after it rises, so all clk-domain flops leave reset
    // on the same edge. SPI (SCLK domain) keeps the raw rst_n: SCLK must
    // stay idle for at least 1 us after rst_n rises (board requirement).
    logic rst_s1, rst_core_n;
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            rst_s1 <= 1'b0;
            rst_core_n <= 1'b0;
        end else begin
            rst_s1 <= 1'b1;
            rst_core_n <= rst_s1;
        end
    end

    // ref_36 strap: sampled on every clk edge while the reset synchroniser
    // is in reset (rst_s1 low), held from one clk before the core is released.
    // A change needs a reset (static false path in SDC). No reset on this flop:
    // its value is defined by the clk edges during reset.
    always_ff @(posedge clk) begin
        if (!rst_s1) ref_36_l <= ref_36;
    end

    // PTT pin and PLL lock are asynchronous: two-flop synchronisers.
    always_ff @(posedge clk or negedge rst_core_n) begin
        if (!rst_core_n) begin
            ptt_s1 <= 1'b0; ptt_s <= 1'b0;
            lock_s1 <= 1'b0; lock_s <= 1'b0;
            irq_n <= 1'b1;
        end else begin
            ptt_s1 <= ptt_pin; ptt_s <= ptt_s1;
            lock_s1 <= pll_lock; lock_s <= lock_s1;
            // IRQ_EN: [0] FIFO overflow, [1] FIFO underflow, [2] clk_error,
            // [3] PLL not locked. Level: low while an enabled condition holds.
            irq_n <= !(|(irq_en_c & {!lock_s, clk_error, fifo_under, fifo_over}));
        end
    end

    spi_regs u_spi (
        .sclk(sclk), .rst_n(rst_n), .cs_n(cs_n), .mosi(mosi), .miso(miso),
        .status(status), .info({lock_s, ptt_s, ref_36_l}), .ctrl(ctrl), .duty_on(duty_on), .duty_off(duty_off),
        .rate(rate), .block_pd(block_pd), .wake_cycles(wake_cycles), .band(band),
        .flag_tog(flag_tog), .band_tog(band_tog), .cfg_tog(cfg_tog),
        .clk_gate(clk_gate), .irq_en(irq_en),
        .clk_req(clk_req)
    );

    // Bundled-data copy. The toggle is synchronized, then the bytes,
    // which have been stable since that same SCLK edge, are sampled.
    always_ff @(posedge clk or negedge rst_core_n) begin
        if (!rst_core_n) begin
            cfg_t1 <= 1'b0; cfg_t2 <= 1'b0;
            flag_t1 <= 1'b0; flag_t2 <= 1'b0;
            band_t1 <= 1'b0; band_t2 <= 1'b0;
            flag_clear <= 1'b0;
            band_write <= 1'b0;
            ctrl_c <= 8'h00;
            duty_on_c <= 8'd1;
            duty_off_c <= 8'd0;
            rate_c <= 8'd4;
            block_pd_c <= 8'd0;
            wake_c <= 8'd0;
            band_c <= 8'd0;
            clk_gate_c <= 8'h1F;
            irq_en_c <= 4'h0;
        end else begin
            cfg_t1 <= cfg_tog; cfg_t2 <= cfg_t1;
            flag_t1 <= flag_tog; flag_t2 <= flag_t1;
            band_t1 <= band_tog; band_t2 <= band_t1;
            flag_clear <= flag_t2 ^ flag_t1;
            band_write <= band_t2 ^ band_t1;
            if (cfg_t2 != cfg_t1) begin
                ctrl_c <= ctrl;
                duty_on_c <= duty_on;
                duty_off_c <= duty_off;
                rate_c <= rate;
                block_pd_c <= block_pd;
                wake_c <= wake_cycles;
                band_c <= band;
                clk_gate_c <= clk_gate;
                irq_en_c <= irq_en;
            end
        end
    end

    rate_table u_rate (
        .ref_36(ref_36_l), .rate(rate_c[2:0]), .frame_clks(frame_clks),
        .r0(r0), .r1(r1), .r2(r2), .sh1(sh1), .sh2(sh2), .norm(norm),
        .slot(slot), .bit_cell(bit_cell), .clk_error(rate_error)
    );

    // Gate enables are flopped on the free-running reference so the
    // latch samples them while clk is low. One gate per running mode.
    always_ff @(posedge clk or negedge rst_core_n) begin
        if (!rst_core_n) begin
            run_en <= 1'b0;
            rx_run <= 1'b0;
            tx_run <= 1'b0;
        end else begin
            run_en <= mode_eff != 2'b00;
            rx_run <= clk_gate_c[0] && rx_en && (block_pd_c[0] || !(ctrl_c[2] && blank));
            tx_run <= clk_gate_c[4] && tx_en && !block_pd_c[4];
        end
    end
    clk_gate u_g_run (.clk(clk), .en(run_en), .gclk(clk_run));
    clk_gate u_g_rx (.clk(clk), .en(rx_run), .gclk(clk_rx));
    clk_gate u_g_tx (.clk(clk), .en(tx_run), .gclk(clk_tx));

    power_ctrl u_pwr (
        .clk(clk_run), .rst_n(rst_core_n), .mode(mode_eff), .duty_en(ctrl_c[2]),
        .duty_on(duty_on_c), .duty_off(duty_off_c), .wake_cycles(wake_c),
        .frame_tick(slave_mode ? rx_v : frame_done),
        .rx_en(rx_en), .tx_en(tx_en), .blank(blank),
        .status_mode(status_mode)
    );

    bit_front u_front (
        .clk(clk_rx), .rst_n(rst_core_n), .en(!block_pd_c[0] && rx_en),
        .ratio(r0), .valid_in(adc_valid), .bit_i(adc_bit_i), .bit_q(adc_bit_q),
        .valid_out(front_v), .i_out(front_i), .q_out(front_q)
    );

    decim_chain u_decim (
        .clk(clk_rx), .rst_n(rst_core_n), .en(!block_pd_c[0]),
        .r1(r1), .r2(r2), .sh1(sh1), .sh2(sh2),
        .valid_in(block_pd_c[0] ? adc_valid : front_v),
        .i_in(block_pd_c[0] ? adc_i : 16'(front_i)),
        .q_in(block_pd_c[0] ? adc_q : 16'(front_q)),
        .valid_out(decim_v), .i_out(decim_i), .q_out(decim_q),
        .alt(tx_en),
        .a0(ta0), .b0(tb0), .a1(ta1), .b1(tb1),
        .a2(ta2), .b2(tb2), .a3(ta3), .b3(tb3),
        .s0(ts0), .s1(ts1), .s2(ts2), .s3(ts3)
    );

    // One multiplier and one delay memory for RX and TX.
    // clk_run is open in both modes; the RX and TX gates are not.
    fir_seq u_fir (
        .clk(clk_run), .rst_n(rst_core_n),
        .en((rx_en && !block_pd_c[0]) || tx_en),
        .tx_mode(tx_en),
        .valid_in(tx_en ? tx_mac_v : decim_v),
        .i_in(tx_en ? tx_mac_i : decim_i),
        .q_in(tx_en ? tx_mac_q : decim_q),
        .norm(norm),
        .valid_out(fir_v), .i_out(fir_i), .q_out(fir_q),
        .tx_done(tx_mac_done),
        .ye_i(ye_i), .yo_i(yo_i), .ye_q(ye_q), .yo_q(yo_q)
    );

    // RX output word: the half-band when the filters run, otherwise the
    // decimator (or its bypass). DC and IQ correction are in the host.
    assign rx_v = filt_rx ? fir_v : decim_v;
    assign rx_i = filt_rx ? fir_i : decim_i;
    assign rx_q = filt_rx ? fir_q : decim_q;

    always_ff @(posedge clk or negedge rst_core_n) begin
        if (!rst_core_n) begin
            relock_cnt <= '0;
            relock_busy <= 1'b0;
        end else if (band_write) begin
            relock_cnt <= RW'(RELOCK_CYCLES);
            relock_busy <= 1'b1;
        end else if (relock_cnt != '0) begin
            relock_cnt <= relock_cnt - 1'b1;
            if (relock_cnt == RW'(1)) relock_busy <= 1'b0;
        end
    end

    always_ff @(posedge clk_run or negedge rst_core_n) begin
        if (!rst_core_n) begin
            i_hold <= '0;
            q_hold <= '0;
            sample_valid <= 1'b0;
        end else if (!rx_en && !tx_en) begin
            sample_valid <= 1'b0;
        end else if (rx_v) begin
            i_hold <= blank ? 16'sd0 : rx_i;
            q_hold <= blank ? 16'sd0 : rx_q;
            sample_valid <= !blank;
        end
    end

    i2s_master u_master (
        .clk(clk_run), .rst_n(rst_core_n),
        .en(!slave_mode && !block_pd_c[3] && clk_gate_c[3] && (rx_en || tx_en)),
        .slot(slot), .bit_cell(bit_cell), .frame_clks(frame_clks), .clk_bad(rate_error),
        .i_out(i_hold), .q_out(q_hold), .din(din),
        .bclk(m_bclk), .lrclk(m_lrclk), .dout(m_dout),
        .clk_error(clk_error), .frame_done(frame_done),
        .i_in(m_i_in), .q_in(m_q_in)
    );

    i2s_slave u_slave (
        .clk(clk_run), .rst_n(rst_core_n),
        .en(slave_mode && !block_pd_c[3] && (rx_en || tx_en)),
        .slot(slot), .sample_valid(rx_v && !blank),
        .i_out(rx_i), .q_out(rx_q), .clr_flags(flag_clear),
        .bclk(bclk_i), .lrclk(lrclk_i), .din(din),
        .dout(s_dout), .overflow(fifo_over), .underflow(fifo_under),
        .i_in(s_i_in), .q_in(s_q_in)
    );

    tx_chain u_tx (
        .clk(clk_tx), .rst_n(rst_core_n), .en(tx_en && !blank && !block_pd_c[4]),
        .valid_in(dac_valid),
        .i_in(dac_i), .q_in(dac_q),
        .frame_clks(frame_clks),
        .mac_done(tx_mac_done),
        .ye_i(ye_i), .yo_i(yo_i), .ye_q(ye_q), .yo_q(yo_q),
        .s0(ts0), .s1(ts1), .s2(ts2), .s3(ts3),
        .mac_valid(tx_mac_v), .mac_i(tx_mac_i), .mac_q(tx_mac_q),
        .a0(ta0), .b0(tb0), .a1(ta1), .b1(tb1),
        .a2(ta2), .b2(tb2), .a3(ta3), .b3(tb3),
        .dac_bit_i(dac_bit_i), .dac_bit_q(dac_bit_q), .dac_bit_valid(dac_bit_valid)
    );

endmodule
