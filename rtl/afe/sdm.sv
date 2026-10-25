// Sigma-Delta modulator of the fractional-N PLL (P2.5 step 2c, spec/pll-topology.md §2 item 6, D3, D16).
//
// MASH 1-1-1, 24-bit accumulators, 1-bit LFSR dither on the LSB. Clocked by div_clk (the MMD output), one
// new divider ratio per reference cycle.
//
// The MMD is clocked after the LO chain's first divider stage, which divides by P = 2 (UHF) or 3 (VHF) (D16),
// so the MMD has to divide by M = N / P, where N = N_INT + N_FRAC / 2^24 = f_VCO / f_ref. On each load the
// 32-bit word {N_INT, N_FRAC} is divided by P with a 32-cycle restoring divider (exact up to 2^-24 of M,
// i.e. < 0.3 Hz at RF); the old M is used until the new one is ready, then the accumulators restart.
//
// div_n = M_int + y, y = c1 + (c2 - c2[-1]) + (c3 - 2 c3[-1] + c3[-2]) in -3 .. +4.
// m_full (M in 7.24 fixed point) also goes to the band calibration as its target.
`timescale 1ns / 1ps

module sdm (
    input  wire        clk,        // div_clk
    input  wire        rst_n,
    input  wire        load,       // one clk pulse: take n_int, n_frac, p3 (synchronised commit, §5.2)
    input  wire [7:0]  n_int,      // N_INT, 86 .. 131 in use
    input  wire [23:0] n_frac,     // N_FRAC
    input  wire        p3,         // 1 = VHF (P = 3), 0 = UHF (P = 2)
    input  wire        en_mash,    // PLL_CTRL[1]: 0 = integer-N (div_n = M_int)
    input  wire        en_dither,  // PLL_CTRL[2]
    output reg  [6:0]  div_n,      // to the MMD
    output reg  [30:0] m_full,     // M = N / P, 7.24 fixed point
    output wire        busy        // division in progress
);
    // ---------------------------------------------------------------- divide {N_INT, N_FRAC} by P
    reg  [31:0] dq;                // dividend shifting out / quotient shifting in
    reg  [1:0]  rem;               // remainder (< 3)
    reg  [5:0]  cnt;               // bits left
    reg         p3r;
    assign busy = (cnt != 6'd0);
    wire [2:0]  trial = {rem, dq[31]};
    wire [1:0]  dvs   = p3r ? 2'd3 : 2'd2;
    wire        ge    = (trial >= {1'b0, dvs});

    // ---------------------------------------------------------------- MASH 1-1-1
    reg  [23:0] a1, a2, a3;
    reg         c2d, c3d, c3dd;
    reg  [22:0] lfsr;
    wire        dith  = en_dither & lfsr[0];
    wire [24:0] s1 = {1'b0, a1} + {1'b0, m_full[23:0]} + {24'd0, dith};
    wire [24:0] s2 = {1'b0, a2} + {1'b0, s1[23:0]};
    wire [24:0] s3 = {1'b0, a3} + {1'b0, s2[23:0]};
    wire        c1 = s1[24], c2 = s2[24], c3 = s3[24];
    wire signed [3:0] y = $signed({3'd0, c1}) + $signed({3'd0, c2}) - $signed({3'd0, c2d})
                        + $signed({3'd0, c3}) - $signed({2'd0, c3d, 1'b0}) + $signed({3'd0, c3dd});

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            dq <= 32'd0; rem <= 2'd0; cnt <= 6'd0; p3r <= 1'b0; m_full <= 31'd0;
            a1 <= 24'd0; a2 <= 24'd0; a3 <= 24'd0; c2d <= 1'b0; c3d <= 1'b0; c3dd <= 1'b0;
            lfsr <= 23'h5A5A5; div_n <= 7'd0;
        end else begin
            if (load) begin
                dq <= {n_int, n_frac}; rem <= 2'd0; cnt <= 6'd32; p3r <= p3;
            end else if (busy) begin
                rem <= ge ? (trial - {1'b0, dvs}) : trial[1:0];
                dq  <= {dq[30:0], ge};
                cnt <= cnt - 6'd1;
                if (cnt == 6'd1) begin
                    m_full <= {dq[29:0], ge};          // quotient complete (fits 31 bits: M < 128)
                    a1 <= 24'd0; a2 <= 24'd0; a3 <= 24'd0; c2d <= 1'b0; c3d <= 1'b0; c3dd <= 1'b0;
                    lfsr <= 23'h5A5A5;
                end
            end
            if (!(busy && cnt == 6'd1)) begin
                a1 <= s1[23:0]; a2 <= s2[23:0]; a3 <= s3[23:0];
                c2d <= c2; c3d <= c3; c3dd <= c3d;
                lfsr <= {lfsr[0] ^ lfsr[5], lfsr[22:1]};   // x^23 + x^18 + 1
            end
            div_n <= en_mash ? (m_full[30:24] + {{3{y[3]}}, y}) : m_full[30:24];
        end
    end
endmodule
