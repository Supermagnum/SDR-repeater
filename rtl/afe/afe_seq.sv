// AFE / LO enable sequencer — VCO bias start-up bypass and D15 divider enable
// (P2.6 open point 2, spec/analog-digital-interface.md §6).
//
// Timing parameters must match analog/pll/p26/wake_timing.py:
//   BYPASS_CYCLES = 36      → ≥ 0.4 µs bias-bypass closed at wake (1.00 µs at 36 MHz)
//   LODIV_DELAY_CYCLES = 48 → en_lodiv after bypass opens (1.33 µs at 36 MHz, D15)
`timescale 1ns / 1ps

module afe_seq #(
    parameter int BYPASS_CYCLES      = 36,
    parameter int LODIV_DELAY_CYCLES = 48
) (
    input  wire clk,
    input  wire rst_n,
    input  wire pll_on,
    output reg  en_vco,
    output reg  en_vco_bias_bp,
    output reg  en_lodiv
);
    localparam int CNT_W = 8;
    reg [CNT_W-1:0] cnt;

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
            en_vco_bias_bp <= (cnt < BYPASS_CYCLES);
            en_lodiv       <= (cnt >= LODIV_DELAY_CYCLES);
            if (cnt != {CNT_W{1'b1}})
                cnt <= cnt + 1'b1;
        end
    end
endmodule
