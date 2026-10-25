// VCO band calibration (P2.5 step 2c, spec/analog-digital-interface.md §7 item 4, D8).
//
// Successive approximation over the 7-bit capacitor bank, V_tune held at mid-window (hold = 1 drives the
// calibration switch). For each trial code the VCO settles for SETTLE reference cycles, then the prescaler
// output (f2 = f_VCO / (4 P), <= 550 MHz) is counted for K reference cycles. Target count = K * M / 4 with
// M = N / P from the Sigma-Delta (m_full, 7.24 fixed point). The bank code rises as the frequency falls; the
// search keeps a bit when the trial frequency is still at or above the target, so it ends on the highest code
// whose frequency is >= target (VCO just above the wanted frequency at mid V_tune).
// K = 128: about 1600 counts, resolution about 0.06 % (one bank step is 0.2-0.5 %). The first trial settles for
// SETTLE0 = 64 cycles (step 4): the hold switch brings the loop filter from anywhere in 0-1.2 V to mid-window
// (time constant about 0.4 us); later trials only change the bank. 64 + 6 x 16 + 7 x (128 + 6) reference cycles
// = 30.5 us at 36 MHz.
`timescale 1ns / 1ps

module bandcal #(
    parameter K_LOG2 = 7,          // K = 128 reference cycles per measurement
    parameter SETTLE = 16,
    parameter SETTLE0 = 64         // first trial: loop filter settles to the hold voltage
) (
    input  wire        clk,        // reference clock
    input  wire        rst_n,
    input  wire        start,      // one clk pulse (PLL_CTRL[6])
    input  wire        f2,         // prescaler output clock (MMD), counted
    input  wire [30:0] m_full,     // target ratio M = N / P (7.24)
    output reg  [6:0]  band,
    output reg         busy,
    output reg         done,
    output reg         hold,
    output reg         fail
);
    localparam S_IDLE = 2'd0, S_SETTLE = 2'd1, S_MEAS = 2'd2, S_READ = 2'd3;
    reg  [1:0]  st;
    reg  [2:0]  bitn;              // bit under trial
    reg  [6:0]  code;              // bits decided so far
    reg  [7:0]  t;                 // reference-cycle timer
    reg         gate, clr;
    wire [15:0] target = m_full >> (26 - K_LOG2);   // K * M / 4

    // f2-domain counter, gate and clear synchronised into the f2 domain
    reg g1, g2, k1, k2;
    reg [15:0] cnt;
    always @(posedge f2 or negedge rst_n) begin
        if (!rst_n) begin g1 <= 0; g2 <= 0; k1 <= 0; k2 <= 0; cnt <= 16'd0; end
        else begin
            g1 <= gate; g2 <= g1; k1 <= clr; k2 <= k1;
            if (k2) cnt <= 16'd0;
            else if (g2) cnt <= cnt + 16'd1;
        end
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= S_IDLE; bitn <= 3'd0; code <= 7'd0; t <= 8'd0; gate <= 0; clr <= 0;
            band <= 7'd64; busy <= 0; done <= 0; hold <= 0; fail <= 0;
        end else case (st)
            S_IDLE: if (start) begin
                busy <= 1; done <= 0; fail <= 0; hold <= 1;
                code <= 7'd0; bitn <= 3'd6; band <= 7'd64; t <= 8'd0; clr <= 1; st <= S_SETTLE;
            end
            S_SETTLE: begin                               // new code settles; counter cleared
                t <= t + 8'd1;
                if (t == ((bitn == 3'd6) ? SETTLE0 : SETTLE) - 1) begin clr <= 0; gate <= 1; t <= 8'd0; st <= S_MEAS; end
            end
            S_MEAS: begin                                 // count for K reference cycles
                t <= t + 8'd1;
                if (t == (1 << K_LOG2) - 1) begin gate <= 0; t <= 8'd0; st <= S_READ; end
            end
            S_READ: begin                                 // let the gate close in the f2 domain, then decide
                t <= t + 8'd1;
                if (t == 8'd5) begin
                    if (cnt >= target) code <= band;      // still at or above target: keep the bit
                    t <= 8'd0;
                    if (bitn == 3'd0) begin
                        band <= (cnt >= target) ? band : code;
                        // ended at either end of the bank: the wanted frequency may be outside the range
                        fail <= (((cnt >= target) ? band : code) == 7'd0) || (((cnt >= target) ? band : code) == 7'd127);
                        busy <= 0; done <= 1; hold <= 0; st <= S_IDLE;
                    end else begin
                        band <= ((cnt >= target) ? band : code) | (7'd1 << (bitn - 3'd1));
                        bitn <= bitn - 3'd1; clr <= 1; st <= S_SETTLE;
                    end
                end
            end
        endcase
    end
endmodule
