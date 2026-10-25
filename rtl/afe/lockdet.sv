// PLL lock detector (P2.5 step 2c, two-sided since step 4; spec/pll-topology.md §2 item 7, §12).
//
// Locked, the PFD gives an UP pulse of about 2.7-3.1 ns every reference cycle (the D18 offset current) plus the
// Sigma-Delta wander (1.2-4.4 ns in all), and a DN pulse of only the reset width. Two strobes from identical
// analogue delay cells (window t_w about 7 ns, 5-12 ns allowed):
//   clk_su = reference edge + t_w: UP still high  -> the divider is more than t_w late
//   clk_sd = divider edge   + t_w: DN still high  -> the divider is more than t_w early
// (Step 2c sampled UP and DN on clk_su only; a DN pulse ends at the reference edge, so an early divider was
// seen only when it led by more than T_ref - t_w, about 21 ns.) Both samples pass a two-flop synchroniser into
// the clk_su domain; NLOCK good cycles in a row set lock, NUNLOCK bad cycles in a row clear it.
`timescale 1ns / 1ps

module lockdet #(
    parameter NLOCK   = 64,
    parameter NUNLOCK = 4
) (
    input  wire clk_su,  // reference delayed by the window
    input  wire clk_sd,  // divider output delayed by the window
    input  wire rst_n,
    input  wire en,
    input  wire up,
    input  wire dn,
    output reg  lock
);
    reg dq;                        // DN sampled in the divider domain
    always @(posedge clk_sd or negedge rst_n)
        if (!rst_n) dq <= 1'b1; else dq <= dn;

    reg u1, u2, d1, d2;            // synchronisers into the clk_su domain
    reg [6:0] good;
    reg [2:0] bad;
    always @(posedge clk_su or negedge rst_n) begin
        if (!rst_n) begin
            u1 <= 1'b1; u2 <= 1'b1; d1 <= 1'b1; d2 <= 1'b1; good <= 7'd0; bad <= 3'd0; lock <= 1'b0;
        end else begin
            u1 <= up; u2 <= u1;
            d1 <= dq; d2 <= d1;
            if (!en) begin
                good <= 7'd0; bad <= 3'd0; lock <= 1'b0;
            end else if (!(u2 | d2)) begin             // inside the window on both sides
                bad <= 3'd0;
                if (good != NLOCK[6:0]) good <= good + 7'd1;
                if (good == NLOCK[6:0] - 7'd1) lock <= 1'b1;
            end else begin
                good <= 7'd0;
                if (bad != NUNLOCK[2:0]) bad <= bad + 3'd1;
                if (bad == NUNLOCK[2:0] - 3'd1) lock <= 1'b0;
            end
        end
    end
endmodule
