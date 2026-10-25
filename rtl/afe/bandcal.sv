// VCO band calibration (P2.5 step 2c; 8 bits, finer counter and nearest-code rule since P2.6 step 1, D20;
// spec/analog-digital-interface.md §7 item 4, spec/pll-topology.md §13).
//
// Successive approximation over the 8-bit capacitor bank with V_tune held at mid-window (hold = 1 drives the
// hold switch and keeps the PFD in reset and the MMD stopped). For each trial code the VCO settles for SETTLE
// reference cycles (SETTLE0 = 64 for the first trial, while the hold switch brings the loop filter to its
// voltage), then the first LO-stage output f1 = f_VCO / P (<= 1.92 GHz) is counted for K reference cycles.
// Target count = K * M with M = N / P from the Sigma-Delta (m_full, 7.24 fixed point). The bank code rises as
// the frequency falls. The SAR ends on the highest code c whose count is >= target; one more trial then
// measures the other one of c and c + 1 (the SAR's last trial measured one of them), and the code whose count
// is closer to the target is kept, so V_tune lands within about half a band step of the hold voltage.
// K = 128: 3700-6400 counts (resolution 0.016-0.027 %; one band step is 0.1-0.25 % with 8 bits).
// 64 + 7 x 16 + 8 x (128 + 6) + (16 + 128 + 6) = 1398 reference cycles = 38.8 us at 36 MHz.
//
// Silicon: the two lowest counter bits are TSPC ripple stages on f1 (the MMD input, which keeps running while
// the MMD counters are stopped); the rest of the counter runs on their carry at f1 / 4 in standard cells. Here
// the whole counter is written as one counter on f1, which counts the same.
`timescale 1ns / 1ps

module bandcal #(
    parameter K_LOG2 = 7,          // K = 128 reference cycles per measurement
    parameter SETTLE = 16,
    parameter SETTLE0 = 64         // first trial: loop filter settles to the hold voltage
) (
    input  wire        clk,        // reference clock
    input  wire        rst_n,
    input  wire        start,      // one clk pulse (PLL_CTRL[6])
    input  wire        f1,         // first LO-stage output f_VCO / P, counted
    input  wire [30:0] m_full,     // target ratio M = N / P (7.24)
    output reg  [7:0]  band,
    output reg         busy,
    output reg         done,
    output reg         hold,       // hold switch on, PFD in reset, MMD stopped (mmd.run = !hold)
    output reg         fail
);
    localparam S_IDLE = 3'd0, S_SETTLE = 3'd1, S_MEAS = 3'd2, S_READ = 3'd3, S_LAST = 3'd4;
    reg  [2:0]  st;
    reg  [2:0]  bitn;              // bit under trial
    reg  [7:0]  code;              // bits decided so far
    reg  [7:0]  t;                 // reference-cycle timer
    reg         gate, clr, extra;  // extra = the nearest-code trial
    reg  [15:0] cnt_a;             // count of the SAR's last trial
    reg  [7:0]  code_a;            // its code
    wire [15:0] target = m_full >> (24 - K_LOG2);   // K * M

    // f1-domain counter, gate and clear synchronised into the f1 domain
    reg g1, g2, k1, k2;
    reg [15:0] cnt;
    always @(posedge f1 or negedge rst_n) begin
        if (!rst_n) begin g1 <= 0; g2 <= 0; k1 <= 0; k2 <= 0; cnt <= 16'd0; end
        else begin
            g1 <= gate; g2 <= g1; k1 <= clr; k2 <= k1;
            if (k2) cnt <= 16'd0;
            else if (g2) cnt <= cnt + 16'd1;
        end
    end

    wire        keep = (cnt >= target);
    wire [7:0]  c_end = keep ? band : code;        // SAR result after the bit-0 trial
    // nearest-code decision (state S_LAST, where 'code' holds the SAR result c): counts of c and c + 1, one from
    // the SAR's last trial (cnt_a, code_a), one from the extra trial (cnt); counts fall as codes rise
    wire [15:0] cc0 = (code_a == code) ? cnt_a : cnt;
    wire [15:0] cc1 = (code_a == code) ? cnt : cnt_a;
    wire [15:0] d0 = (cc0 >= target) ? cc0 - target : target - cc0;
    wire [15:0] d1 = (cc1 >= target) ? cc1 - target : target - cc1;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= S_IDLE; bitn <= 3'd0; code <= 8'd0; t <= 8'd0; gate <= 0; clr <= 0; extra <= 0;
            band <= 8'd128; busy <= 0; done <= 0; hold <= 0; fail <= 0; cnt_a <= 16'd0; code_a <= 8'd0;
        end else case (st)
            S_IDLE: if (start) begin
                busy <= 1; done <= 0; fail <= 0; hold <= 1; extra <= 0;
                code <= 8'd0; bitn <= 3'd7; band <= 8'd128; t <= 8'd0; clr <= 1; st <= S_SETTLE;
            end
            S_SETTLE: begin                               // new code settles; counter cleared
                t <= t + 8'd1;
                if (t == ((bitn == 3'd7 && !extra) ? SETTLE0 : SETTLE) - 1) begin
                    clr <= 0; gate <= 1; t <= 8'd0; st <= S_MEAS;
                end
            end
            S_MEAS: begin                                 // count for K reference cycles
                t <= t + 8'd1;
                if (t == (1 << K_LOG2) - 1) begin gate <= 0; t <= 8'd0; st <= extra ? S_LAST : S_READ; end
            end
            S_READ: begin                                 // let the gate close in the f1 domain, then decide
                t <= t + 8'd1;
                if (t == 8'd5) begin
                    t <= 8'd0;
                    if (keep) code <= band;               // still at or above target: keep the bit
                    if (bitn == 3'd0) begin
                        // SAR done on c_end; measure the other one of c_end and c_end + 1
                        cnt_a <= cnt; code_a <= band;
                        if (c_end == 8'd255) begin        // no c_end + 1
                            band <= c_end; fail <= 1; busy <= 0; done <= 1; hold <= 0; st <= S_IDLE;
                        end else begin
                            band <= (band == c_end) ? c_end + 8'd1 : c_end;
                            code <= c_end; extra <= 1; clr <= 1; st <= S_SETTLE;
                        end
                    end else begin
                        band <= c_end | (8'd1 << (bitn - 3'd1));
                        bitn <= bitn - 3'd1; clr <= 1; st <= S_SETTLE;
                    end
                end
            end
            S_LAST: begin                                 // nearest-code decision
                t <= t + 8'd1;
                if (t == 8'd5) begin
                    t <= 8'd0;
                    band <= (d1 < d0) ? code + 8'd1 : code;
                    // ended at an end of the bank: the wanted frequency may be outside the range
                    fail <= (code == 8'd0);
                    busy <= 0; done <= 1; hold <= 0; extra <= 0; st <= S_IDLE;
                end
            end
            default: st <= S_IDLE;
        endcase
    end
endmodule
