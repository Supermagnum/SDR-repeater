`timescale 1ns/1ps
// SPI register file. The shift register and the registers are clocked
// by SCLK, so the reference can be stopped in shutdown. Mode 0, 16 bits:
//   [15] write, [14:8] address, [7:0] data.
// MISO returns the addressed byte during the data half. The write
// commits on the 16th rising SCLK, while CS is still low.
// CTRL[3] is reserved. The slot width comes from the rate table.
// An SPI write of a non-shutdown mode raises clk_req in this domain,
// which is how the host is asked to start the reference.

module spi_regs (
    input  logic       sclk,
    input  logic       rst_n,
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
    output logic       flag_tog,
    output logic       dc_tog,
    output logic       band_tog,
    output logic       cfg_tog,
    output logic [7:0] tx_dc_i,
    output logic [7:0] tx_dc_q,
    output logic [7:0] tx_gain_i,
    output logic [7:0] tx_gain_q,
    output logic [7:0] tx_phase,
    output logic [7:0] clk_gate,
    output logic       clk_req
);

    localparam logic [7:0] CTRL_RST = 8'h00;
    localparam logic [7:0] GAIN_RST = 8'd128;

    logic [7:0] ctrl_q, duty_on_q, duty_off_q, rate_q, dc_shift_q;
    logic [7:0] gain_i_q, gain_q_q, phase_q, block_pd_q, wake_cycles_q, band_q;
    logic [7:0] tx_dc_i_q, tx_dc_q_q, tx_gain_i_q, tx_gain_q_q, tx_phase_q, clk_gate_q;
    logic [7:0] status_s1, status_s2;
    // shreg[15] is never read: the 16th bit arrives on mosi itself.
    /* verilator lint_off UNUSEDSIGNAL */
    logic [15:0] shreg;
    /* verilator lint_on UNUSEDSIGNAL */
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
    assign clk_req = ctrl_q[1:0] != 2'b00;

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
            7'h0A: read_reg = status_s2;
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

    // Bit counter. CS high clears it asynchronously, so an aborted frame
    // (CS raised mid-frame, no further SCLK) cannot misalign the next one.
    // Only this counter uses CS as a reset; the register file does not
    // (that mapping caused a combinational loop earlier). A complete frame
    // wraps to 0 on the 16th SCLK edge.
    always_ff @(posedge sclk or posedge cs_n) begin
        if (cs_n) nbits <= 5'd0;
        else if (nbits == 5'd15) nbits <= 5'd0;
        else nbits <= nbits + 5'd1;
    end

    // SPI mode 0: the host samples MISO on the SCLK rising edge, so the
    // chip changes MISO on the falling edge. Bit 7 goes out on the falling
    // edge after the last address bit (nbits == 8), bit 0 at nbits == 15.
    logic [7:0] rd_sh;
    always_ff @(negedge sclk or negedge rst_n) begin
        if (!rst_n) begin
            miso <= 1'b0;
            rd_sh <= 8'h00;
        end else if (cs_n) begin
            miso <= 1'b0;
        end else if (nbits == 5'd8) begin
            miso <= rd_byte[7];
            rd_sh <= {rd_byte[6:0], 1'b0};
        end else if (nbits > 5'd8 && nbits < 5'd16) begin
            miso <= rd_sh[7];
            rd_sh <= {rd_sh[6:0], 1'b0};
        end
    end

    // A finished frame returns nbits to 0 on the 16th SCLK, while CS
    // is still low. An SCLK edge with CS high also clears the shifter,
    // so an aborted frame does not run into the next one. CS is not an
    // asynchronous reset: that mapping produced a combinational loop
    // in the reset mux.
    always_ff @(posedge sclk or negedge rst_n) begin
        if (!rst_n) begin
            shreg <= 16'h0000;
            rd_byte <= 8'h00;
            status_s1 <= 8'h00;
            status_s2 <= 8'h00;
            ctrl_q <= CTRL_RST;
            duty_on_q <= 8'd1;
            duty_off_q <= 8'd0;
            rate_q <= 8'd4;
            band_q <= 8'd0;
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
            clk_gate_q <= 8'h1F;
            flag_tog <= 1'b0;
            dc_tog <= 1'b0;
            band_tog <= 1'b0;
            cfg_tog <= 1'b0;
        end else if (cs_n) begin
            // CS high: hold. The bit counter is cleared by its own process.
        end else begin
            status_s1 <= status;
            status_s2 <= status_s1;
            shreg <= {shreg[14:0], mosi};
            if (nbits == 5'd7)
                rd_byte <= read_reg({shreg[5:0], mosi});
            if (nbits == 5'd15) begin
                if (shreg[14]) begin
                    cfg_tog <= ~cfg_tog;
                    case (shreg[13:7])
                        7'h00: begin
                            ctrl_q <= {1'b0, shreg[5:3], 1'b0, shreg[1:0], mosi};
                            if (shreg[6]) flag_tog <= ~flag_tog;
                        end
                        7'h01: duty_on_q <= {shreg[6:0], mosi};
                        7'h02: duty_off_q <= {shreg[6:0], mosi};
                        7'h03: rate_q <= {shreg[6:0], mosi};
                        7'h04: dc_shift_q <= {shreg[6:0], mosi};
                        7'h05: gain_i_q <= {shreg[6:0], mosi};
                        7'h06: gain_q_q <= {shreg[6:0], mosi};
                        7'h07: phase_q <= {shreg[6:0], mosi};
                        7'h08: block_pd_q <= {shreg[6:0], mosi};
                        7'h09: wake_cycles_q <= {shreg[6:0], mosi};
                        7'h0C: begin
                            band_q <= {7'b0, mosi};
                            band_tog <= ~band_tog;
                        end
                        7'h0D: if (mosi) dc_tog <= ~dc_tog;
                        7'h0E: tx_dc_i_q <= {shreg[6:0], mosi};
                        7'h0F: tx_dc_q_q <= {shreg[6:0], mosi};
                        7'h10: tx_gain_i_q <= {shreg[6:0], mosi};
                        7'h11: tx_gain_q_q <= {shreg[6:0], mosi};
                        7'h12: tx_phase_q <= {shreg[6:0], mosi};
                        7'h13: clk_gate_q <= {shreg[6:0], mosi};
                        default: ;
                    endcase
                end
            end
        end
    end

endmodule
