`timescale 1ns/1ps
// SPI register file for the digital back end.
// Mode 0, host is master. One CS assertion carries 16 bits:
//   [15]    1 = write, 0 = read
//   [14:8]  register address
//   [7:0]   write data, ignored on a read
// MISO returns the addressed register during the data byte, before a write commits.
// The write commits on CS rising. sclk is oversampled by clk. sclk must stay
// slower than clk/4.

module spi_regs (
    input  logic       clk,
    input  logic       rst_n,
    input  logic       sclk,
    input  logic       cs_n,
    input  logic       mosi,
    output logic       miso,
    input  logic [7:0] status,
    output logic [7:0] ctrl,
    output logic [7:0] duty_on,
    output logic [7:0] duty_off,
    output logic [7:0] rate,
    output logic [7:0] dc_shift,
    output logic [7:0] gain_i,
    output logic [7:0] gain_q,
    output logic [7:0] phase,
    output logic [7:0] block_pd,
    output logic [7:0] wake_cycles,
    output logic [7:0] band,
    output logic       flag_clear,
    output logic       dc_clear,
    output logic       band_write,
    output logic [7:0] tx_dc_i,
    output logic [7:0] tx_dc_q,
    output logic [7:0] tx_gain_i,
    output logic [7:0] tx_gain_q,
    output logic [7:0] tx_phase,
    output logic [7:0] clk_gate
);

    localparam logic [7:0] CTRL_RST = 8'h00;
    localparam logic [7:0] GAIN_RST = 8'd128;

    logic [7:0] ctrl_q, duty_on_q, duty_off_q, rate_q, dc_shift_q;
    logic [7:0] gain_i_q, gain_q_q, phase_q, block_pd_q, wake_cycles_q, band_q;
    logic [7:0] tx_dc_i_q, tx_dc_q_q, tx_gain_i_q, tx_gain_q_q, tx_phase_q, clk_gate_q;

    logic sclk_q, cs_q;
    logic [15:0] shreg;
    logic [4:0] nbits;
    logic [7:0] rd_byte;

    assign ctrl = ctrl_q;
    assign duty_on = duty_on_q;
    assign duty_off = duty_off_q;
    assign rate = rate_q;
    assign band = band_q;
    assign dc_shift = dc_shift_q;
    assign gain_i = gain_i_q;
    assign gain_q = gain_q_q;
    assign phase = phase_q;
    assign block_pd = block_pd_q;
    assign wake_cycles = wake_cycles_q;
    assign tx_dc_i = tx_dc_i_q;
    assign tx_dc_q = tx_dc_q_q;
    assign tx_gain_i = tx_gain_i_q;
    assign tx_gain_q = tx_gain_q_q;
    assign tx_phase = tx_phase_q;
    assign clk_gate = clk_gate_q;

    function automatic logic [7:0] read_reg(input logic [6:0] addr);
        case (addr)
            7'h00: read_reg = ctrl_q;
            7'h01: read_reg = duty_on_q;
            7'h02: read_reg = duty_off_q;
            7'h03: read_reg = rate_q;
            7'h04: read_reg = dc_shift_q;
            7'h05: read_reg = gain_i_q;
            7'h06: read_reg = gain_q_q;
            7'h07: read_reg = phase_q;
            7'h08: read_reg = block_pd_q;
            7'h09: read_reg = wake_cycles_q;
            7'h0A: read_reg = status;
            7'h0B: read_reg = 8'h11;
            7'h0C: read_reg = band_q;
            7'h0D: read_reg = 8'h00;
            7'h0E: read_reg = tx_dc_i_q;
            7'h0F: read_reg = tx_dc_q_q;
            7'h10: read_reg = tx_gain_i_q;
            7'h11: read_reg = tx_gain_q_q;
            7'h12: read_reg = tx_phase_q;
            7'h13: read_reg = clk_gate_q;
            default: read_reg = 8'h00;
        endcase
    endfunction

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            sclk_q <= 1'b0;
            cs_q <= 1'b1;
            shreg <= 16'h0000;
            nbits <= 5'd0;
            rd_byte <= 8'h00;
            miso <= 1'b0;
            ctrl_q <= CTRL_RST;
            duty_on_q <= 8'd1;
            duty_off_q <= 8'd0;
            rate_q <= 8'd4;
            band_q <= 8'd0;
            flag_clear <= 1'b0;
            dc_clear <= 1'b0;
            band_write <= 1'b0;
            dc_shift_q <= 8'd4;
            gain_i_q <= GAIN_RST;
            gain_q_q <= GAIN_RST;
            phase_q <= 8'd0;
            block_pd_q <= 8'd0;
            wake_cycles_q <= 8'd0;
            tx_dc_i_q <= 8'd0;
            tx_dc_q_q <= 8'd0;
            tx_gain_i_q <= GAIN_RST;
            tx_gain_q_q <= GAIN_RST;
            tx_phase_q <= 8'd0;
            // 1 = clock allowed. Mode and block power-down still gate.
            clk_gate_q <= 8'h1F;
        end else begin
            sclk_q <= sclk;
            cs_q <= cs_n;
            flag_clear <= 1'b0;
            dc_clear <= 1'b0;
            band_write <= 1'b0;
            if (cs_n) begin
                nbits <= 5'd0;
                miso <= 1'b0;
                if (!cs_q && shreg[15] && nbits == 5'd16) begin
                    case (shreg[14:8])
                        7'h00: begin
                            ctrl_q <= {1'b0, shreg[6:0]};
                            flag_clear <= shreg[7];
                        end
                        7'h01: duty_on_q <= shreg[7:0];
                        7'h02: duty_off_q <= shreg[7:0];
                        7'h03: rate_q <= shreg[7:0];
                        7'h04: dc_shift_q <= shreg[7:0];
                        7'h05: gain_i_q <= shreg[7:0];
                        7'h06: gain_q_q <= shreg[7:0];
                        7'h07: phase_q <= shreg[7:0];
                        7'h08: block_pd_q <= shreg[7:0];
                        7'h09: wake_cycles_q <= shreg[7:0];
                        7'h0C: begin
                            band_q <= {7'b0, shreg[0]};
                            band_write <= 1'b1;
                        end
                        7'h0D: dc_clear <= shreg[0];
                        7'h0E: tx_dc_i_q <= shreg[7:0];
                        7'h0F: tx_dc_q_q <= shreg[7:0];
                        7'h10: tx_gain_i_q <= shreg[7:0];
                        7'h11: tx_gain_q_q <= shreg[7:0];
                        7'h12: tx_phase_q <= shreg[7:0];
                        7'h13: clk_gate_q <= shreg[7:0];
                        default: ;
                    endcase
                end
            end else if (sclk && !sclk_q) begin
                shreg <= {shreg[14:0], mosi};
                nbits <= nbits + 5'd1;
                if (nbits == 5'd7) begin
                    // After seven bits, shreg[6] is R/W and shreg[5:0] is
                    // the top of the address. mosi is address bit 0.
                    rd_byte <= read_reg({shreg[5:0], mosi});
                end
                if (nbits >= 5'd8 && nbits < 5'd16) begin
                    miso <= rd_byte[7];
                    rd_byte <= {rd_byte[6:0], 1'b0};
                end
            end
        end
    end

endmodule
