`timescale 1ns/1ps
// One multiplier and one 64x16 SRAM for the RX compensation filter,
// the RX half-band, and the TX half-band. The chain is half-duplex.
// I ages 0..30 are words 0..30. Q ages 0..30 are words 32..62.
// TX uses the same map with length 16.
//
// A read presented on one edge is valid two edges later. Pairs are
// issued on consecutive clocks and multiplied on the second data
// beat, so each pair costs two clocks. A keep sample is the
// compensation filter, two writes, and both channels. That is 48
// clocks, inside the 64-clock output period at 32 MHz / 500 kHz.
// The other CIC sample in that period is the discarded half-band
// input: compensation filter and two writes, 6 clocks, queued so
// it does not collide with the keep sample.

module fir_seq (
    input  logic               clk,
    input  logic               rst_n,
    input  logic               en,
    input  logic               tx_mode,
    input  logic               valid_in,
    input  logic signed [15:0] i_in,
    input  logic signed [15:0] q_in,
    input  logic signed [15:0] norm,
    output logic               valid_out,
    output logic signed [15:0] i_out,
    output logic signed [15:0] q_out,
    output logic               tx_done,
    output logic signed [15:0] ye_i,
    output logic signed [15:0] yo_i,
    output logic signed [15:0] ye_q,
    output logic signed [15:0] yo_q
);

    logic signed [15:0] cf_i0, cf_i1, cf_i2;
    logic signed [15:0] cf_q0, cf_q1, cf_q2;
    logic [4:0] wp;
    logic signed [15:0] yi, yq_w;
    // Only acc_i[17:0] feeds the multiplier (norm step). The full-scale
    // half-band output is at most 28,437 < 2^17 (see rate_table.sv).
    /* verilator lint_off UNUSEDSIGNAL */
    logic signed [39:0] acc, acc_i;
    /* verilator lint_on UNUSEDSIGNAL */
    logic [5:0] step;
    logic active, keep, hb_phase;
    logic pend;
    logic signed [15:0] pend_i, pend_q;
    logic mac_first;
    logic [5:0] ram_addr;
    logic ram_men, ram_wen, ram_ren;
    logic [15:0] ram_din;
    logic [15:0] ram_dout;
    logic signed [15:0] sample_a;

    logic signed [17:0] op_a;
    logic signed [15:0] op_b;
    wire signed [35:0] prod = op_a * op_b;

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

    function automatic logic [5:0] haddr(input logic qch, input logic [4:0] age);
        logic [5:0] sum;
        logic [4:0] idx;
        if (tx_mode) begin
            sum = {2'b0, wp[3:0]} + {2'b0, age[3:0]};
            idx = {1'b0, sum[3:0]};
        end else begin
            sum = {1'b0, wp} + {1'b0, age};
            if (sum >= 6'd31) sum = sum - 6'd31;
            idx = sum[4:0];
        end
        haddr = qch ? {1'b1, idx} : {1'b0, idx};
    endfunction

    function automatic logic [4:0] newest;
        if (tx_mode) newest = (wp[3:0] == 4'd0) ? 5'd15 : {1'b0, wp[3:0] - 4'd1};
        else newest = (wp == 5'd0) ? 5'd30 : (wp - 5'd1);
    endfunction

    function automatic logic [4:0] age_lo(input logic [3:0] p);
        if (tx_mode) age_lo = {1'b0, p};
        else age_lo = {p[3:0], 1'b0};
    endfunction

    function automatic logic [4:0] age_hi(input logic [3:0] p);
        if (tx_mode) age_hi = 5'd15 - {1'b0, p};
        else age_hi = 5'd30 - {p[3:0], 1'b0};
    endfunction

    hb_sram u_ram (
        .clk(clk), .men(ram_men), .wen(ram_wen), .ren(ram_ren),
        .addr(ram_addr), .din(ram_din), .dout(ram_dout)
    );

    // step 20 starts the half-band. Each channel is 19 clocks:
    // eight pairs at two clocks, then the center on clock 18.
    wire [5:0] hb = step - 6'd20;
    wire ch_now = hb >= 6'd19;
    wire [5:0] loc = ch_now ? (hb - 6'd19) : hb;
    wire [3:0] ipair = loc[4:1];
    wire [3:0] mpair = 4'((loc - 6'd3) >> 1);
    wire mac_pair = loc[0] && (loc >= 6'd3) && (loc <= 6'd17);
    wire mac_center = (loc == 6'd18);

    always_comb begin
        op_a = '0;
        op_b = '0;
        if (!tx_mode && active && step < 6'd4) begin
            case (step[2:0])
                3'd0: begin op_a = 18'(cf_i0) + 18'(cf_i2); op_b = -16'sd5006; end
                3'd1: begin op_a = 18'(cf_i1); op_b = 16'sd32767; end
                3'd2: begin op_a = 18'(cf_q0) + 18'(cf_q2); op_b = -16'sd5006; end
                3'd3: begin op_a = 18'(cf_q1); op_b = 16'sd32767; end
                default: ;
            endcase
        end
        if (active && step >= 6'd20 && mac_pair) begin
            op_a = 18'(sample_a) + 18'($signed(ram_dout));
            op_b = hb_c(mpair);
        end
        if (active && step >= 6'd20 && mac_center) begin
            op_a = 18'($signed(ram_dout));
            op_b = 16'sd32767;
        end
        if (active && step == 6'd60) begin
            op_a = acc_i[17:0];
            op_b = norm;
        end
        if (active && step == 6'd61) begin
            op_a = acc[17:0];
            op_b = norm;
        end
    end

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            cf_i0 <= '0; cf_i1 <= '0; cf_i2 <= '0;
            cf_q0 <= '0; cf_q1 <= '0; cf_q2 <= '0;
            yi <= '0; yq_w <= '0;
            acc <= '0; acc_i <= '0;
            step <= '0;
            active <= 1'b0;
            keep <= 1'b0;
            hb_phase <= 1'b0;
            wp <= '0;
            pend <= 1'b0;
            pend_i <= '0; pend_q <= '0;
            mac_first <= 1'b0;
            ram_addr <= '0; ram_men <= 1'b0; ram_wen <= 1'b0; ram_ren <= 1'b0;
            ram_din <= '0;
            sample_a <= '0;
            valid_out <= 1'b0;
            i_out <= '0; q_out <= '0;
            tx_done <= 1'b0;
            ye_i <= '0; yo_i <= '0; ye_q <= '0; yo_q <= '0;
        end else begin
            valid_out <= 1'b0;
            tx_done <= 1'b0;
            ram_men <= 1'b0;
            ram_wen <= 1'b0;
            ram_ren <= 1'b0;
            if (!en) begin
                active <= 1'b0;
                hb_phase <= 1'b0;
                step <= '0;
                pend <= 1'b0;
            end else if (!active) begin
                if (valid_in || pend) begin
                    if (tx_mode) begin
                        yi <= pend ? pend_i : i_in;
                        yq_w <= pend ? pend_q : q_in;
                        pend <= 1'b0;
                        active <= 1'b1;
                        step <= 6'd10;
                    end else begin
                        cf_i0 <= pend ? pend_i : i_in;
                        cf_i1 <= cf_i0;
                        cf_i2 <= cf_i1;
                        cf_q0 <= pend ? pend_q : q_in;
                        cf_q1 <= cf_q0;
                        cf_q2 <= cf_q1;
                        keep <= (hb_phase == 1'b0);
                        hb_phase <= ~hb_phase;
                        pend <= 1'b0;
                        active <= 1'b1;
                        step <= 6'd0;
                    end
                end
            end else if (valid_in) begin
                pend <= 1'b1;
                pend_i <= i_in;
                pend_q <= q_in;
            end
            if (en && active) begin
                if (step < 6'd4) begin
                    if (step == 6'd0) acc <= 40'(prod);
                    else if (step == 6'd1) acc <= acc + 40'(prod);
                    else if (step == 6'd2) begin
                        yi <= sat16(acc >>> 15);
                        acc <= 40'(prod);
                    end else begin
                        yq_w <= sat16((acc + 40'(prod)) >>> 15);
                    end
                    step <= step + 6'd1;
                end else if (step == 6'd4 || step == 6'd10) begin
                    ram_men <= 1'b1;
                    ram_wen <= 1'b1;
                    ram_addr <= haddr(1'b0, tx_mode ? 5'd15 : 5'd30);
                    ram_din <= yi;
                    step <= step + 6'd1;
                end else if (step == 6'd5 || step == 6'd11) begin
                    ram_men <= 1'b1;
                    ram_wen <= 1'b1;
                    ram_addr <= haddr(1'b1, tx_mode ? 5'd15 : 5'd30);
                    ram_din <= yq_w;
                    wp <= newest();
                    if (!tx_mode && !keep) active <= 1'b0;
                    else begin
                        step <= 6'd20;
                        mac_first <= 1'b1;
                    end
                end else if (step >= 6'd20 && step <= 6'd57) begin
                    // Low address on an even local cycle, high on the
                    // next. The word is valid two cycles after the issue.
                    if (loc < 6'd16 && !loc[0]) begin
                        ram_men <= 1'b1;
                        ram_ren <= 1'b1;
                        ram_addr <= haddr(ch_now, age_lo(ipair));
                    end else if (loc < 6'd16 && loc[0]) begin
                        ram_men <= 1'b1;
                        ram_ren <= 1'b1;
                        ram_addr <= haddr(ch_now, age_hi(ipair));
                    end else if (loc == 6'd16) begin
                        ram_men <= 1'b1;
                        ram_ren <= 1'b1;
                        ram_addr <= haddr(ch_now, tx_mode ? 5'd7 : 5'd15);
                    end
                    if (loc >= 6'd2 && !loc[0] && loc <= 6'd16)
                        sample_a <= $signed(ram_dout);
                    if (mac_pair || mac_center) begin
                        if (tx_mode && mac_center) begin
                            if (!ch_now) yo_i <= sat16(40'(prod) >>> 15);
                            else yo_q <= sat16(40'(prod) >>> 15);
                        end else if (tx_mode && mac_pair && mpair == 4'd7) begin
                            if (!ch_now) ye_i <= sat16((mac_first ? 40'(prod) : acc + 40'(prod)) >>> 15);
                            else ye_q <= sat16((mac_first ? 40'(prod) : acc + 40'(prod)) >>> 15);
                        end else if (!tx_mode && mac_center && !ch_now) begin
                            acc_i <= (mac_first ? 40'(prod) : acc + 40'(prod)) >>> 15;
                        end else if (!tx_mode && mac_center && ch_now) begin
                            acc <= (mac_first ? 40'(prod) : acc + 40'(prod)) >>> 15;
                        end else if (mac_first) acc <= 40'(prod);
                        else acc <= acc + 40'(prod);
                        mac_first <= mac_center;
                        if (mac_center && ch_now) begin
                            if (tx_mode) begin
                                tx_done <= 1'b1;
                                active <= 1'b0;
                            end else step <= 6'd60;
                        end else step <= step + 6'd1;
                    end else step <= step + 6'd1;
                end else if (step == 6'd60) begin
                    i_out <= sat16(40'(prod) >>> 15);
                    step <= 6'd61;
                end else if (step == 6'd61) begin
                    q_out <= sat16(40'(prod) >>> 15);
                    valid_out <= 1'b1;
                    active <= 1'b0;
                end else active <= 1'b0;
            end
        end
    end

endmodule
