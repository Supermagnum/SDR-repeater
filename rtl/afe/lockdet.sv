// PLL lock detector (P2.5 step 2c, spec/pll-topology.md §2 item 7).
//
// Locked, the PFD gives an UP pulse of about 2.9-4 ns every reference cycle (the D18 offset current) plus the
// Sigma-Delta wander of about +-1 ns. clk_s is the reference delayed by the window t_w (about 6-7 ns, an
// analogue delay cell); at each clk_s edge UP and DN are sampled (two-flop synchroniser): both low means the
// phase error is inside the window. NLOCK good cycles in a row set lock; NUNLOCK bad cycles in a row clear it.
`timescale 1ns / 1ps

module lockdet #(
    parameter NLOCK   = 64,
    parameter NUNLOCK = 4
) (
    input  wire clk_s,   // reference delayed by the window
    input  wire rst_n,
    input  wire en,
    input  wire up,
    input  wire dn,
    output reg  lock
);
    reg s1, s2;                    // synchroniser for (UP or DN)
    reg [6:0] good;
    reg [2:0] bad;
    always @(posedge clk_s or negedge rst_n) begin
        if (!rst_n) begin
            s1 <= 1'b1; s2 <= 1'b1; good <= 7'd0; bad <= 3'd0; lock <= 1'b0;
        end else begin
            s1 <= up | dn;
            s2 <= s1;
            if (!en) begin
                good <= 7'd0; bad <= 3'd0; lock <= 1'b0;
            end else if (!s2) begin                    // inside the window
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
