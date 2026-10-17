`timescale 1ns/1ps
// Time-multiplexed symmetric FIR for the compensation filter and the
// half-band. One multiplier serves both channels. A new CIC sample
// every 32 reference clocks is the tightest rate (32 MHz, 500 kHz),
// and this schedule finishes in 27 clocks.
// Coefficients match the parallel design. The accumulator is shifted
// by 15. `norm` is a Q15 scale applied after the half-band so every
// reference/rate pair has the same DC gain.

module fir_seq (
    input  logic               clk,
    input  logic               rst_n,
    input  logic               en,
    input  logic               valid_in,
    input  logic signed [15:0] i_in,
    input  logic signed [15:0] q_in,
    input  logic signed [15:0] norm,
    output logic               valid_out,
    output logic signed [15:0] i_out,
    output logic signed [15:0] q_out
);

    logic signed [15:0] cf_i0, cf_i1, cf_i2;
    logic signed [15:0] cf_q0, cf_q1, cf_q2;
    logic signed [15:0] hb_i [0:30];
    logic signed [15:0] hb_q [0:30];
    logic signed [15:0] yi, yq;
    logic signed [39:0] acc, acc_i, acc_q;
    logic [4:0] step;
    logic active, keep, hb_phase;
    integer k;

    function automatic logic signed [15:0] sat16(input logic signed [39:0] v);
        if (v > 40'sd32767) sat16 = 16'sd32767;
        else if (v < -40'sd32768) sat16 = -16'sd32768;
        else sat16 = v[15:0];
    endfunction

    function automatic logic signed [15:0] hb_c(input logic [3:0] idx);
        case (idx)
            4'd0: hb_c = -16'sd138;
            4'd1: hb_c = 16'sd305;
            4'd2: hb_c = -16'sd617;
            4'd3: hb_c = 16'sd1128;
            4'd4: hb_c = -16'sd1952;
            4'd5: hb_c = 16'sd3376;
            4'd6: hb_c = -16'sd6450;
            4'd7: hb_c = 16'sd20688;
            default: hb_c = 16'sd32767;
        endcase
    endfunction

    // Pair sum for half-band tap `idx` (0..7), center is idx 8.
    function automatic logic signed [16:0] pair_i(input logic [3:0] idx);
        if (idx == 4'd8) pair_i = {hb_i[15][15], hb_i[15]};
        else pair_i = {hb_i[2*idx][15], hb_i[2*idx]} + {hb_i[30-2*idx][15], hb_i[30-2*idx]};
    endfunction

    function automatic logic signed [16:0] pair_q(input logic [3:0] idx);
        if (idx == 4'd8) pair_q = {hb_q[15][15], hb_q[15]};
        else pair_q = {hb_q[2*idx][15], hb_q[2*idx]} + {hb_q[30-2*idx][15], hb_q[30-2*idx]};
    endfunction

    logic signed [17:0] op_a;
    logic signed [15:0] op_b;
    wire signed [35:0] prod = op_a * op_b;

    // One multiplier. The step counter picks the operands.
    always_comb begin
        op_a = '0;
        op_b = '0;
        case (step)
            5'd0: begin op_a = 18'(cf_i0) + 18'(cf_i2); op_b = -16'sd5006; end
            5'd1: begin op_a = 18'(cf_i1); op_b = 16'sd32767; end
            5'd2: begin op_a = 18'(cf_q0) + 18'(cf_q2); op_b = -16'sd5006; end
            5'd3: begin op_a = 18'(cf_q1); op_b = 16'sd32767; end
            5'd5: begin op_a = 18'(pair_i(4'd0)); op_b = hb_c(4'd0); end
            5'd6: begin op_a = 18'(pair_i(4'd1)); op_b = hb_c(4'd1); end
            5'd7: begin op_a = 18'(pair_i(4'd2)); op_b = hb_c(4'd2); end
            5'd8: begin op_a = 18'(pair_i(4'd3)); op_b = hb_c(4'd3); end
            5'd9: begin op_a = 18'(pair_i(4'd4)); op_b = hb_c(4'd4); end
            5'd10: begin op_a = 18'(pair_i(4'd5)); op_b = hb_c(4'd5); end
            5'd11: begin op_a = 18'(pair_i(4'd6)); op_b = hb_c(4'd6); end
            5'd12: begin op_a = 18'(pair_i(4'd7)); op_b = hb_c(4'd7); end
            5'd13: begin op_a = 18'(pair_i(4'd8)); op_b = hb_c(4'd8); end
            5'd14: begin op_a = 18'(pair_q(4'd0)); op_b = hb_c(4'd0); end
            5'd15: begin op_a = 18'(pair_q(4'd1)); op_b = hb_c(4'd1); end
            5'd16: begin op_a = 18'(pair_q(4'd2)); op_b = hb_c(4'd2); end
            5'd17: begin op_a = 18'(pair_q(4'd3)); op_b = hb_c(4'd3); end
            5'd18: begin op_a = 18'(pair_q(4'd4)); op_b = hb_c(4'd4); end
            5'd19: begin op_a = 18'(pair_q(4'd5)); op_b = hb_c(4'd5); end
            5'd20: begin op_a = 18'(pair_q(4'd6)); op_b = hb_c(4'd6); end
            5'd21: begin op_a = 18'(pair_q(4'd7)); op_b = hb_c(4'd7); end
            5'd22: begin op_a = 18'(pair_q(4'd8)); op_b = hb_c(4'd8); end
            5'd23: begin op_a = acc_i[17:0]; op_b = norm; end
            5'd24: begin op_a = acc_q[17:0]; op_b = norm; end
            default: begin op_a = '0; op_b = '0; end
        endcase
    end

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            cf_i0 <= '0; cf_i1 <= '0; cf_i2 <= '0;
            cf_q0 <= '0; cf_q1 <= '0; cf_q2 <= '0;
            for (k = 0; k < 31; k = k + 1) begin
                hb_i[k] <= '0;
                hb_q[k] <= '0;
            end
            yi <= '0; yq <= '0;
            acc <= '0; acc_i <= '0; acc_q <= '0;
            step <= '0;
            active <= 1'b0;
            keep <= 1'b0;
            hb_phase <= 1'b0;
            valid_out <= 1'b0;
            i_out <= '0;
            q_out <= '0;
        end else begin
            valid_out <= 1'b0;
            if (!en) begin
                active <= 1'b0;
                hb_phase <= 1'b0;
                step <= '0;
            end else if (!active) begin
                if (valid_in) begin
                    cf_i0 <= i_in; cf_i1 <= cf_i0; cf_i2 <= cf_i1;
                    cf_q0 <= q_in; cf_q1 <= cf_q0; cf_q2 <= cf_q1;
                    keep <= (hb_phase == 1'b0);
                    hb_phase <= ~hb_phase;
                    active <= 1'b1;
                    step <= 5'd0;
                end
            end else begin
                case (step)
                    5'd0: acc <= 40'(prod);
                    5'd1: acc <= acc + 40'(prod);
                    5'd2: begin
                        yi <= sat16(acc >>> 15);
                        acc <= 40'(prod);
                    end
                    5'd3: acc <= acc + 40'(prod);
                    5'd4: begin
                        yq <= sat16(acc >>> 15);
                        for (k = 30; k > 0; k = k - 1) begin
                            hb_i[k] <= hb_i[k-1];
                            hb_q[k] <= hb_q[k-1];
                        end
                        hb_i[0] <= yi;
                        hb_q[0] <= sat16(acc >>> 15);
                    end
                    5'd5: begin
                        if (!keep) active <= 1'b0;
                        else acc <= 40'(prod);
                    end
                    5'd6: acc <= acc + 40'(prod);
                    5'd7: acc <= acc + 40'(prod);
                    5'd8: acc <= acc + 40'(prod);
                    5'd9: acc <= acc + 40'(prod);
                    5'd10: acc <= acc + 40'(prod);
                    5'd11: acc <= acc + 40'(prod);
                    5'd12: acc <= acc + 40'(prod);
                    5'd13: acc <= acc + 40'(prod);
                    5'd14: begin
                        acc_i <= acc >>> 15;
                        acc <= 40'(prod);
                    end
                    5'd15: acc <= acc + 40'(prod);
                    5'd16: acc <= acc + 40'(prod);
                    5'd17: acc <= acc + 40'(prod);
                    5'd18: acc <= acc + 40'(prod);
                    5'd19: acc <= acc + 40'(prod);
                    5'd20: acc <= acc + 40'(prod);
                    5'd21: acc <= acc + 40'(prod);
                    5'd22: acc <= acc + 40'(prod);
                    5'd23: begin
                        acc_q <= acc >>> 15;
                        acc <= 40'(prod);
                    end
                    5'd24: begin
                        i_out <= sat16(acc >>> 15);
                        acc <= 40'(prod);
                    end
                    default: begin
                        q_out <= sat16(acc >>> 15);
                        valid_out <= 1'b1;
                        active <= 1'b0;
                    end
                endcase
                if (step != 5'd5 || keep) begin
                    if (step != 5'd25) step <= step + 5'd1;
                end
            end
        end
    end

endmodule
