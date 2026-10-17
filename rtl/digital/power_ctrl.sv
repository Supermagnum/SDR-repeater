`timescale 1ns/1ps
// Power mode and RX duty cycle.
// mode: 00 shutdown, 01 standby, 10 RX, 11 TX.
// Leaving shutdown or standby starts a wake count of wake_cycles
// output frames. valid_iq stays low until that count finishes.
// With duty_en in RX, the core then emits duty_on frames and blanks
// duty_off frames. Blanked frames still consume frame_tick.
// This count is the wake-up-to-valid-IQ figure. It is in frames, not seconds.

module power_ctrl (
    input  logic       clk,
    input  logic       rst_n,
    input  logic [1:0] mode,
    input  logic       duty_en,
    input  logic [7:0] duty_on,
    input  logic [7:0] duty_off,
    input  logic [7:0] wake_cycles,
    input  logic       frame_tick,
    output logic       rx_en,
    output logic       tx_en,
    output logic       blank,
    output logic [1:0] status_mode
);

    logic [1:0] mode_q;
    logic [7:0] wake_left;
    logic [7:0] phase_left;
    logic       in_off;
    logic       waking;

    assign status_mode = mode;
    assign rx_en = (mode == 2'b10);
    assign tx_en = (mode == 2'b11);
    assign waking = (wake_left != 8'd0);
    assign blank = (mode[1] == 1'b0) || waking || (rx_en && duty_en && in_off);

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            mode_q <= 2'b00;
            wake_left <= 8'd0;
            phase_left <= 8'd0;
            in_off <= 1'b0;
        end else begin
            if (mode != mode_q) begin
                mode_q <= mode;
                in_off <= 1'b0;
                phase_left <= 8'd0;
                if (mode[1]) wake_left <= wake_cycles;
                else wake_left <= 8'd0;
            end else if (frame_tick && mode[1]) begin
                if (wake_left != 8'd0) begin
                    wake_left <= wake_left - 8'd1;
                end else if (rx_en && duty_en) begin
                    if (phase_left == 8'd0) begin
                        if (!in_off) begin
                            if (duty_off != 8'd0) begin
                                in_off <= 1'b1;
                                phase_left <= duty_off - 8'd1;
                            end
                        end else begin
                            in_off <= 1'b0;
                            phase_left <= (duty_on == 8'd0) ? 8'd0 : duty_on - 8'd1;
                        end
                    end else begin
                        phase_left <= phase_left - 8'd1;
                    end
                end
            end
        end
    end

endmodule
