// AFE / LO enable sequencer — VCO bias start-up bypass, D15 divider enable, D22 cal_busy,
// D24 CP offset off during V_tune hold
// (spec/analog-digital-interface.md §6; analog/pll/p26/wake_timing.py).
//
//   BYPASS_CYCLES = 36      → ≥ 0.4 µs all-resistor bias-bypass at wake (1.00 µs at 36 MHz)
//   LODIV_DELAY_CYCLES = 48 → en_lodiv after wake all-bypass would open (D15)
//   cal_busy                → en_vco_tail_bp only (tail filter); bank/var stay open (D22 step 1c)
//   hold (bandcal)          → en_cp_offset low (D18 offset off so hold sits near mid-window)
`timescale 1ns / 1ps

module afe_seq #(
    parameter int BYPASS_CYCLES      = 36,
    parameter int LODIV_DELAY_CYCLES = 48
) (
    input  wire clk,
    input  wire rst_n,
    input  wire pll_on,
    input  wire cal_busy,
    input  wire hold,             // bandcal V_tune hold (D24)
    output reg  en_vco,
    output reg  en_vco_bias_bp,   // wake: all bias resistors (tail+bank+var), 36 cycles only
    output reg  en_vco_tail_bp,   // wake OR search: tail-filter bypass only
    output reg  en_lodiv,
    output reg  en_cp_offset      // D18 offset current enable; low while hold
);
    localparam int CNT_W = 8;
    reg [CNT_W-1:0] cnt;

    wire bypass_wake = (cnt < BYPASS_CYCLES);
    // lodiv stays off while wake all-bypass or cal is active
    wire lodiv_block = bypass_wake | cal_busy;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            en_vco         <= 1'b0;
            en_vco_bias_bp <= 1'b0;
            en_vco_tail_bp <= 1'b0;
            en_lodiv       <= 1'b0;
            en_cp_offset   <= 1'b0;
            cnt            <= '0;
        end else if (!pll_on) begin
            en_vco         <= 1'b0;
            en_vco_bias_bp <= 1'b0;
            en_vco_tail_bp <= 1'b0;
            en_lodiv       <= 1'b0;
            en_cp_offset   <= 1'b0;
            cnt            <= '0;
        end else begin
            en_vco         <= 1'b1;
            // Wake: close every bias bypass for BYPASS_CYCLES (unchanged 36).
            en_vco_bias_bp <= bypass_wake;
            // Tail filter: closed at wake and for the whole amplitude/band search.
            en_vco_tail_bp <= bypass_wake | cal_busy;
            // D15: lodiv only after wake all-bypass opens and cal is idle
            en_lodiv       <= (!lodiv_block) && (cnt >= LODIV_DELAY_CYCLES);
            // D24: D18 offset off while V_tune is held for band calibration.
            en_cp_offset   <= ~hold;
            if (cnt != {CNT_W{1'b1}})
                cnt <= cnt + 1'b1;
        end
    end
endmodule
