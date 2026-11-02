// VCO band + amplitude calibration (D20 + D22).
// Order: amp SAR (mid band) → 8-bit band SAR + nearest → amp touch-up SAR.
// Bypass stays closed while busy (afe_seq.cal_busy).
// Amp: 5-bit VCO_BIAS; amp_high=1 means Amp > 1.25 V (clear trial bit).
// Band cycles 1398; amp 2×5×AMP_SETTLE (AMP_SETTLE=36) = 360; total ≈ 1758 ≈ 48.8 µs @ 36 MHz.
`timescale 1ns / 1ps

module bandcal #(
    parameter K_LOG2 = 7,
    parameter SETTLE = 16,
    parameter SETTLE0 = 64,
    parameter AMP_SETTLE = 36
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        start,
    input  wire        f1,
    input  wire [30:0] m_full,
    input  wire        amp_high,
    input  wire        amp_manual,
    output reg  [7:0]  band,
    output reg  [4:0]  vco_bias,
    output reg         target_nr,
    output reg         busy,
    output reg         done,
    output reg         hold,
    output reg         fail
);
    localparam S_IDLE = 4'd0, S_ASETTLE = 4'd1, S_AREAD = 4'd2,
               S_SETTLE = 4'd3, S_MEAS = 4'd4, S_READ = 4'd5, S_LAST = 4'd6;
    reg  [3:0]  st;
    reg  [2:0]  bitn;
    reg  [7:0]  code;
    reg  [7:0]  t;
    reg         gate, clr, extra;
    reg  [15:0] cnt_a;
    reg  [7:0]  code_a;
    reg  [2:0]  abit;
    reg  [4:0]  acode;
    reg         aphase;          // 0 pre-band, 1 touch-up
    wire [15:0] target = m_full >> (24 - K_LOG2);

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
    wire [7:0]  c_end = keep ? band : code;
    wire [15:0] cc0 = (code_a == code) ? cnt_a : cnt;
    wire [15:0] cc1 = (code_a == code) ? cnt : cnt_a;
    wire [15:0] d0 = (cc0 >= target) ? cc0 - target : target - cc0;
    wire [15:0] d1 = (cc1 >= target) ? cc1 - target : target - cc1;

    wire [4:0]  a_trial = acode | (5'd1 << abit);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= S_IDLE; bitn <= 3'd0; code <= 8'd0; t <= 8'd0; gate <= 0; clr <= 0; extra <= 0;
            band <= 8'd128; busy <= 0; done <= 0; hold <= 0; fail <= 0; cnt_a <= 16'd0; code_a <= 8'd0;
            vco_bias <= 5'd16; target_nr <= 0; abit <= 3'd4; acode <= 5'd0; aphase <= 0;
        end else case (st)
            S_IDLE: if (start) begin
                busy <= 1; done <= 0; fail <= 0; hold <= 1; extra <= 0; target_nr <= 0;
                code <= 8'd0; bitn <= 3'd7; band <= 8'd128; t <= 8'd0; clr <= 1; aphase <= 0;
                if (amp_manual) st <= S_SETTLE;
                else begin acode <= 5'd0; abit <= 3'd4; vco_bias <= 5'd16; st <= S_ASETTLE; end
            end
            S_ASETTLE: begin
                vco_bias <= a_trial;
                t <= t + 8'd1;
                if (t == AMP_SETTLE - 1) begin t <= 8'd0; st <= S_AREAD; end
            end
            S_AREAD: begin
                // Keep bit if Amp is not above target
                if (!amp_high) acode <= a_trial;
                if (abit == 3'd0) begin
                    vco_bias <= amp_high ? acode : a_trial;
                    if (!amp_high) acode <= a_trial;
                    if (!aphase) begin
                        aphase <= 1;
                        code <= 8'd0; bitn <= 3'd7; band <= 8'd128; clr <= 1; t <= 8'd0;
                        st <= S_SETTLE;
                    end else begin
                        // touch-up done: target_nr if still below target at code 31
                        if ((amp_high ? acode : a_trial) == 5'd31 && !amp_high)
                            target_nr <= 1'b1;
                        busy <= 0; done <= 1; hold <= 0; st <= S_IDLE;
                    end
                end else begin
                    abit <= abit - 3'd1;
                    t <= 8'd0; st <= S_ASETTLE;
                end
            end
            S_SETTLE: begin
                t <= t + 8'd1;
                if (t == ((bitn == 3'd7 && !extra) ? SETTLE0 : SETTLE) - 1) begin
                    clr <= 0; gate <= 1; t <= 8'd0; st <= S_MEAS;
                end
            end
            S_MEAS: begin
                t <= t + 8'd1;
                if (t == (1 << K_LOG2) - 1) begin gate <= 0; t <= 8'd0; st <= extra ? S_LAST : S_READ; end
            end
            S_READ: begin
                t <= t + 8'd1;
                if (t == 8'd5) begin
                    t <= 8'd0;
                    if (keep) code <= band;
                    if (bitn == 3'd0) begin
                        cnt_a <= cnt; code_a <= band;
                        if (c_end == 8'd255) begin
                            band <= c_end; fail <= 1;
                            if (amp_manual) begin busy <= 0; done <= 1; hold <= 0; st <= S_IDLE; end
                            else begin acode <= 5'd0; abit <= 3'd4; vco_bias <= 5'd16; t <= 8'd0; st <= S_ASETTLE; end
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
            S_LAST: begin
                t <= t + 8'd1;
                if (t == 8'd5) begin
                    t <= 8'd0;
                    band <= (d1 < d0) ? code + 8'd1 : code;
                    fail <= (code == 8'd0);
                    extra <= 0;
                    if (amp_manual) begin busy <= 0; done <= 1; hold <= 0; st <= S_IDLE; end
                    else begin acode <= 5'd0; abit <= 3'd4; vco_bias <= 5'd16; t <= 8'd0; st <= S_ASETTLE; end
                end
            end
            default: st <= S_IDLE;
        endcase
    end
endmodule
