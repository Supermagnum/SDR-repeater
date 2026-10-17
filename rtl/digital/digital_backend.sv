`timescale 1ns/1ps

// Phase 1 digital back end for one RX/TX chain.
// The ADC and DAC sample ports are the boundary toward the analog blocks,
// which are not in this phase. SPI and I2S face the host.
// Tank Q is not an input to this logic.

module digital_backend (
    input  logic               clk,
    input  logic               rst_n,
    input  logic               sclk,
    input  logic               cs_n,
    input  logic               mosi,
    output logic               miso,
    input  logic               bclk,
    input  logic               lrclk,
    input  logic               din,
    output logic               dout,
    output logic               valid_iq,
    input  logic               adc_valid,
    input  logic signed [15:0] adc_i,
    input  logic signed [15:0] adc_q,
    output logic               dac_valid,
    output logic signed [15:0] dac_i,
    output logic signed [15:0] dac_q
);

    logic [7:0] ctrl, duty_on, duty_off, decim, dc_shift;
    logic [7:0] gain_i, gain_q, phase, block_pd, wake_cycles, status;
    logic rx_en, tx_en, blank;
    logic [1:0] status_mode;
    logic decim_v, dc_v, cal_v;
    logic signed [15:0] decim_i, decim_q, dc_i, dc_q, cal_i, cal_q;
    logic signed [15:0] i_hold, q_hold;
    logic sample_valid;
    logic frame_done;
    logic signed [15:0] i_from_host, q_from_host;

    assign status = {4'b0, sample_valid, blank, status_mode};
    assign valid_iq = sample_valid;

    spi_regs u_spi (
        .clk(clk),
        .rst_n(rst_n),
        .sclk(sclk),
        .cs_n(cs_n),
        .mosi(mosi),
        .miso(miso),
        .status(status),
        .ctrl(ctrl),
        .duty_on(duty_on),
        .duty_off(duty_off),
        .decim(decim),
        .dc_shift(dc_shift),
        .gain_i(gain_i),
        .gain_q(gain_q),
        .phase(phase),
        .block_pd(block_pd),
        .wake_cycles(wake_cycles)
    );

    power_ctrl u_pwr (
        .clk(clk),
        .rst_n(rst_n),
        .mode(ctrl[1:0]),
        .duty_en(ctrl[2]),
        .duty_on(duty_on),
        .duty_off(duty_off),
        .wake_cycles(wake_cycles),
        .frame_tick(cal_v),
        .rx_en(rx_en),
        .tx_en(tx_en),
        .blank(blank),
        .status_mode(status_mode)
    );

    decim_iq u_decim (
        .clk(clk),
        .rst_n(rst_n),
        .en(rx_en && !block_pd[0]),
        .ratio_sel(decim[1:0]),
        .valid_in(adc_valid && rx_en),
        .i_in(adc_i),
        .q_in(adc_q),
        .valid_out(decim_v),
        .i_out(decim_i),
        .q_out(decim_q)
    );

    dc_offset u_dc (
        .clk(clk),
        .rst_n(rst_n),
        .en(rx_en && !block_pd[1]),
        .shift(dc_shift[2:0]),
        .valid_in(decim_v),
        .i_in(decim_i),
        .q_in(decim_q),
        .valid_out(dc_v),
        .i_out(dc_i),
        .q_out(dc_q)
    );

    iq_cal u_cal (
        .clk(clk),
        .rst_n(rst_n),
        .en(rx_en && !block_pd[2]),
        .gain_i(gain_i),
        .gain_q(gain_q),
        .phase(phase),
        .valid_in(dc_v),
        .i_in(dc_i),
        .q_in(dc_q),
        .valid_out(cal_v),
        .i_out(cal_i),
        .q_out(cal_q)
    );

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            i_hold <= 16'sd0;
            q_hold <= 16'sd0;
            sample_valid <= 1'b0;
        end else if (!rx_en && !tx_en) begin
            sample_valid <= 1'b0;
        end else if (cal_v) begin
            i_hold <= blank ? 16'sd0 : cal_i;
            q_hold <= blank ? 16'sd0 : cal_q;
            sample_valid <= !blank;
        end
    end

    i2s_port u_i2s (
        .clk(clk),
        .rst_n(rst_n),
        .en(!block_pd[3] && (rx_en || tx_en)),
        .slot_32(ctrl[3]),
        .bclk(bclk),
        .lrclk(lrclk),
        .din(din),
        .i_out(i_hold),
        .q_out(q_hold),
        .dout(dout),
        .frame_done(frame_done),
        .i_in(i_from_host),
        .q_in(q_from_host)
    );

    assign dac_valid = frame_done && tx_en && !blank;
    assign dac_i = i_from_host;
    assign dac_q = q_from_host;

endmodule
