// AFE / LO enable sequencer — VCO bias start-up bypass, D15 divider enable, D22 cal_busy
// (spec/analog-digital-interface.md §6; analog/pll/p26/wake_timing.py).
//
//   BYPASS_CYCLES = 36      → ≥ 0.4 µs bias-bypass at wake (1.00 µs at 36 MHz)
//   LODIV_DELAY_CYCLES = 48 → en_lodiv after bypass would open (D15)
//   cal_busy                → keep bypass closed for whole band+amp calibration (D22)
`timescale 1ns / 1ps

module afe_seq #(
    parameter int BYPASS_CYCLES      = 36,
    parameter int LODIV_DELAY_CYCLES = 48
) (
    input  wire clk,
    input  wire rst_n,
    input  wire pll_on,
    input  wire cal_busy,
    output reg  en_vco,
    output reg  en_vco_bias_bp,
    output reg  en_lodiv
);
    localparam int CNT_W = 8;
    reg [CNT_W-1:0] cnt;

    wire bypass_wake = (cnt < BYPASS_CYCLES);
    wire bypass_on   = bypass_wake | cal_busy;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            en_vco         <= 1'b0;
            en_vco_bias_bp <= 1'b0;
            en_lodiv       <= 1'b0;
            cnt            <= '0;
        end else if (!pll_on) begin
            en_vco         <= 1'b0;
            en_vco_bias_bp <= 1'b0;
            en_lodiv       <= 1'b0;
            cnt            <= '0;
        end else begin
            en_vco         <= 1'b1;
            en_vco_bias_bp <= bypass_on;
            // D15: lodiv only after bypass is open (wake count past delay and not held by cal)
            en_lodiv       <= (!bypass_on) && (cnt >= LODIV_DELAY_CYCLES);
            if (cnt != {CNT_W{1'b1}})
                cnt <= cnt + 1'b1;
        end
    end
endmodule
