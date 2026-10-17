`timescale 1ns/1ps
// TX path. An I2S sample at fs is DC-corrected and IQ-corrected,
// interpolated by the half-band (polyphase, same coefficients as
// the receiver) and an order-2 CIC, then modulated by a 2nd-order
// 1-bit sigma-delta on I and on Q.
// TX_DC_* and TX_PHASE are signed 8-bit. PHASE LSB is 1/128 rad.
// TX_GAIN 128 means 1.0.

module tx_chain (
    input  logic               clk,
    input  logic               rst_n,
    input  logic               en,
    input  logic               valid_in,
    input  logic signed [15:0] i_in,
    input  logic signed [15:0] q_in,
    input  logic signed [7:0]  dc_i,
    input  logic signed [7:0]  dc_q,
    input  logic [7:0]         gain_i,
    input  logic [7:0]         gain_q,
    input  logic signed [7:0]  phase,
    input  logic [10:0]        frame_clks,
    output logic               dac_bit_i,
    output logic               dac_bit_q,
    output logic               dac_bit_valid
);

    function automatic logic signed [15:0] sat16(input logic signed [24:0] v);
        if (v > 25'sd32767) sat16 = 16'sd32767;
        else if (v < -25'sd32768) sat16 = -16'sd32768;
        else sat16 = v[15:0];
    endfunction

    function automatic logic signed [15:0] hb_c(input logic [2:0] idx);
        case (idx)
            3'd0: hb_c = -16'sd138;
            3'd1: hb_c = 16'sd305;
            3'd2: hb_c = -16'sd617;
            3'd3: hb_c = 16'sd1128;
            3'd4: hb_c = -16'sd1952;
            3'd5: hb_c = 16'sd3376;
            3'd6: hb_c = -16'sd6450;
            default: hb_c = 16'sd20688;
        endcase
    endfunction

    function automatic logic [4:0] flog(input logic [10:0] v);
        if (v >= 11'd512) flog = 5'd9;
        else if (v >= 11'd256) flog = 5'd8;
        else if (v >= 11'd128) flog = 5'd7;
        else if (v >= 11'd64) flog = 5'd6;
        else if (v >= 11'd32) flog = 5'd5;
        else if (v >= 11'd16) flog = 5'd4;
        else flog = 5'd3;
    endfunction

    logic signed [15:0] di [0:15];
    logic signed [15:0] dq [0:15];
    logic signed [15:0] ye_i, yo_i, ye_q, yo_q;
    logic signed [15:0] hold_ei, hold_oi, hold_eq, hold_oq;
    logic signed [15:0] lat_oi, lat_oq;
    logic signed [39:0] acc;
    logic [4:0] step;
    logic active;
    logic signed [15:0] cal_i, cal_q;
    logic [10:0] gap;
    logic odd_ph;
    logic signed [15:0] inj_i, inj_q;
    logic inject;
    logic signed [39:0] ci0, ci1, cq0, cq1;
    logic signed [39:0] xi_d, xq_d, ci_d, cq_d;
    logic signed [39:0] comb_i, comb_q;
    logic signed [24:0] si1, si2, sq1, sq2;
    logic bi, bq;
    integer t;

    wire [10:0] half = (frame_clks < 11'd2) ? 11'd1 : (frame_clks >> 1);
    wire [4:0] sh = flog(half);

    logic signed [17:0] op_a;
    logic signed [15:0] op_b;
    wire signed [35:0] prod = op_a * op_b;

    always_comb begin
        op_a = '0;
        op_b = '0;
        case (step)
            5'd2: begin op_a = 18'(di[0]) + 18'(di[15]); op_b = hb_c(3'd0); end
            5'd3: begin op_a = 18'(di[1]) + 18'(di[14]); op_b = hb_c(3'd1); end
            5'd4: begin op_a = 18'(di[2]) + 18'(di[13]); op_b = hb_c(3'd2); end
            5'd5: begin op_a = 18'(di[3]) + 18'(di[12]); op_b = hb_c(3'd3); end
            5'd6: begin op_a = 18'(di[4]) + 18'(di[11]); op_b = hb_c(3'd4); end
            5'd7: begin op_a = 18'(di[5]) + 18'(di[10]); op_b = hb_c(3'd5); end
            5'd8: begin op_a = 18'(di[6]) + 18'(di[9]); op_b = hb_c(3'd6); end
            5'd9: begin op_a = 18'(di[7]) + 18'(di[8]); op_b = hb_c(3'd7); end
            5'd10: begin op_a = 18'(di[7]); op_b = 16'sd32767; end
            5'd11: begin op_a = 18'(dq[0]) + 18'(dq[15]); op_b = hb_c(3'd0); end
            5'd12: begin op_a = 18'(dq[1]) + 18'(dq[14]); op_b = hb_c(3'd1); end
            5'd13: begin op_a = 18'(dq[2]) + 18'(dq[13]); op_b = hb_c(3'd2); end
            5'd14: begin op_a = 18'(dq[3]) + 18'(dq[12]); op_b = hb_c(3'd3); end
            5'd15: begin op_a = 18'(dq[4]) + 18'(dq[11]); op_b = hb_c(3'd4); end
            5'd16: begin op_a = 18'(dq[5]) + 18'(dq[10]); op_b = hb_c(3'd5); end
            5'd17: begin op_a = 18'(dq[6]) + 18'(dq[9]); op_b = hb_c(3'd6); end
            5'd18: begin op_a = 18'(dq[7]) + 18'(dq[8]); op_b = hb_c(3'd7); end
            5'd19: begin op_a = 18'(dq[7]); op_b = 16'sd32767; end
            default: begin op_a = '0; op_b = '0; end
        endcase
    end

    logic signed [24:0] n1i, n2i, n1q, n2q;
    logic signed [15:0] xi16, xq16;
    logic signed [39:0] ys_i, ys_q;

    always_comb begin
        ys_i = ci1 >>> sh;
        ys_q = cq1 >>> sh;
        if (ys_i > 40'sd32767) xi16 = 16'sd32767;
        else if (ys_i < -40'sd32768) xi16 = -16'sd32768;
        else xi16 = ys_i[15:0];
        if (ys_q > 40'sd32767) xq16 = 16'sd32767;
        else if (ys_q < -40'sd32768) xq16 = -16'sd32768;
        else xq16 = ys_q[15:0];
        n1i = si1 + 25'(xi16) - (bi ? 25'sd32767 : -25'sd32767);
        n2i = si2 + n1i - (bi ? 25'sd32767 : -25'sd32767);
        n1q = sq1 + 25'(xq16) - (bq ? 25'sd32767 : -25'sd32767);
        n2q = sq2 + n1q - (bq ? 25'sd32767 : -25'sd32767);
        comb_i = 40'(inj_i) - xi_d - ci_d;
        comb_q = 40'(inj_q) - xq_d - cq_d;
    end

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (t = 0; t < 16; t = t + 1) begin
                di[t] <= '0;
                dq[t] <= '0;
            end
            ye_i <= '0; yo_i <= '0; ye_q <= '0; yo_q <= '0;
            hold_ei <= '0; hold_oi <= '0; hold_eq <= '0; hold_oq <= '0;
            lat_oi <= '0; lat_oq <= '0;
            acc <= '0; step <= '0; active <= 1'b0;
            cal_i <= '0; cal_q <= '0;
            gap <= '0; odd_ph <= 1'b0;
            inj_i <= '0; inj_q <= '0; inject <= 1'b0;
            ci0 <= '0; ci1 <= '0; cq0 <= '0; cq1 <= '0;
            xi_d <= '0; xq_d <= '0; ci_d <= '0; cq_d <= '0;
            si1 <= '0; si2 <= '0; sq1 <= '0; sq2 <= '0;
            bi <= 1'b0; bq <= 1'b0;
            dac_bit_i <= 1'b0; dac_bit_q <= 1'b0; dac_bit_valid <= 1'b0;
        end else if (!en) begin
            active <= 1'b0;
            inject <= 1'b0;
            dac_bit_valid <= 1'b0;
            gap <= '0;
            odd_ph <= 1'b0;
            bi <= 1'b0;
            bq <= 1'b0;
        end else begin
            dac_bit_valid <= 1'b1;
            if (!active && valid_in) begin
                cal_i <= sat16(25'(i_in) - 25'(dc_i));
                cal_q <= sat16(25'(q_in) - 25'(dc_q));
                active <= 1'b1;
                step <= 5'd0;
            end else if (active && step == 5'd0) begin
                cal_i <= sat16((25'(cal_i) * $signed({1'b0, gain_i}) + 25'(cal_q) * phase) >>> 7);
                cal_q <= sat16((25'(cal_q) * $signed({1'b0, gain_q})) >>> 7);
                step <= 5'd1;
            end else if (active && step == 5'd1) begin
                for (t = 15; t > 0; t = t - 1) begin
                    di[t] <= di[t-1];
                    dq[t] <= dq[t-1];
                end
                di[0] <= cal_i;
                dq[0] <= cal_q;
                step <= 5'd2;
            end else if (active && step == 5'd2) begin
                acc <= 40'(prod);
                step <= 5'd3;
            end else if (active && step >= 5'd3 && step <= 5'd8) begin
                case (step)
                    5'd3: acc <= acc + 40'(prod);
                    5'd4: acc <= acc + 40'(prod);
                    5'd5: acc <= acc + 40'(prod);
                    5'd6: acc <= acc + 40'(prod);
                    5'd7: acc <= acc + 40'(prod);
                    default: acc <= acc + 40'(prod);
                endcase
                step <= step + 5'd1;
            end else if (active && step == 5'd9) begin
                acc <= acc + 40'(prod);
                step <= 5'd10;
            end else if (active && step == 5'd10) begin
                ye_i <= sat16(acc >>> 15);
                acc <= 40'(prod);
                step <= 5'd11;
            end else if (active && step == 5'd11) begin
                yo_i <= sat16(acc >>> 15);
                acc <= 40'(prod);
                step <= 5'd12;
            end else if (active && step >= 5'd12 && step <= 5'd17) begin
                case (step)
                    5'd12: acc <= acc + 40'(prod);
                    5'd13: acc <= acc + 40'(prod);
                    5'd14: acc <= acc + 40'(prod);
                    5'd15: acc <= acc + 40'(prod);
                    5'd16: acc <= acc + 40'(prod);
                    default: acc <= acc + 40'(prod);
                endcase
                step <= step + 5'd1;
            end else if (active && step == 5'd18) begin
                acc <= acc + 40'(prod);
                step <= 5'd19;
            end else if (active && step == 5'd19) begin
                ye_q <= sat16(acc >>> 15);
                acc <= 40'(prod);
                step <= 5'd20;
            end else if (active && step == 5'd20) begin
                yo_q <= sat16(acc >>> 15);
                step <= 5'd21;
            end else if (active) begin
                hold_ei <= ye_i;
                hold_oi <= yo_i;
                hold_eq <= ye_q;
                hold_oq <= yo_q;
                active <= 1'b0;
            end

            if (gap == 11'd0) begin
                gap <= half - 11'd1;
                // Take even and odd from the same MAC result. Latching
                // the odd sample here keeps the pair together if the
                // next MAC result lands between the two half-frames.
                if (!odd_ph) begin
                    inj_i <= hold_ei;
                    inj_q <= hold_eq;
                    lat_oi <= hold_oi;
                    lat_oq <= hold_oq;
                end else begin
                    inj_i <= lat_oi;
                    inj_q <= lat_oq;
                end
                odd_ph <= ~odd_ph;
                inject <= 1'b1;
            end else begin
                gap <= gap - 11'd1;
                inject <= 1'b0;
            end

            if (inject) begin
                xi_d <= 40'(inj_i);
                xq_d <= 40'(inj_q);
                ci_d <= 40'(inj_i) - xi_d;
                cq_d <= 40'(inj_q) - xq_d;
                ci0 <= ci0 + comb_i;
                cq0 <= cq0 + comb_q;
            end
            ci1 <= ci1 + ci0;
            cq1 <= cq1 + cq0;

            si1 <= n1i;
            si2 <= n2i;
            sq1 <= n1q;
            sq2 <= n2q;
            bi <= ~n2i[24];
            bq <= ~n2q[24];
            dac_bit_i <= ~n2i[24];
            dac_bit_q <= ~n2q[24];
        end
    end

endmodule
