// Multi-modulus feedback divider of the PLL (P2.5 step 2b, spec/pll-topology.md §2 item 5, D16).
//
// Pulse-swallow divider: a divide-by-4/5 prescaler built from two divide-by-2/3 cells (the step-1 cell), and
// a program counter and a swallow counter clocked by the prescaler output (<= 550 MHz, standard cells).
// Division ratio N = 4 * Pc + S with Pc = n[6:2], S = n[1:0]: the prescaler divides by 5 for the first S of
// the Pc prescaler cycles and by 4 for the rest. Any N from 16 to 127; in use 23-73 (D16).
//
// Why not a full Vaucher chain of six 2/3 cells with range extension (first version): with a new ratio every
// cycle, the last active cell makes its decision for the next cycle before the first cell has made its
// decision for the current one, and where that falls relative to the output pulse moves with N and with the
// chain length; the cells then mixed program bits of two different ratios (tested: about a third of the
// periods wrong). The counters here load the whole ratio at one instant per cycle, so every cycle uses
// exactly one ratio. In the two-cell prescaler the second cell's bit is fixed (0), so the early decision of
// the last cell does not matter.
//
// The Sigma-Delta modulator (clocked by div_out) gives a new n every cycle; n is loaded at the end of the
// next cycle (latency one cycle).
`timescale 1ns / 1ps

module mmd_cell (
    input  wire fin,     // input clock
    input  wire rst_n,
    input  wire modin,   // from the next (slower) cell; 1 = this output period may be stretched
    input  wire p,       // program bit
    output reg  fo,      // output clock to the next cell: one fin period high per output period
    output reg  modout   // to the previous (faster) cell: high during the last fin period of an active period
);
    reg [1:0] k;         // fin period within the current output period
    reg       act, l3;   // modin seen at the start of this period; period lengthened to 3
    wire      last = (k == (l3 ? 2'd2 : 2'd1));

    always @(posedge fin or negedge rst_n) begin
        if (!rst_n) begin
            k <= 2'd1; act <= 1'b0; l3 <= 1'b0; fo <= 1'b0; modout <= 1'b0;
        end else if (last) begin             // a new output period starts
            k <= 2'd0; act <= modin; l3 <= modin & p; fo <= 1'b1; modout <= 1'b0;
        end else begin
            k <= k + 2'd1; fo <= 1'b0;
            modout <= act & ((k + 2'd1) == (l3 ? 2'd2 : 2'd1));
        end
    end
endmodule

module mmd (
    input  wire       fin,     // from the LO chain's first divider stage (D16), up to 2.2 GHz
    input  wire       rst_n,
    input  wire [6:0] n,       // division ratio 16 .. 127
    output reg        div_out  // one prescaler-output period high every N fin periods (div_clk after retiming)
);
    wire       f1, f2;         // prescaler cell outputs; f2 = prescaler output
    wire       mo0, mo1;
    reg        mc;             // 1 = this prescaler cycle divides by 5
    reg  [4:0] pc;             // prescaler cycles left in this division cycle
    reg  [1:0] sc;             // divide-by-5 cycles left

    // divide-by-4/5 prescaler: two 2/3 cells, the second with its bit fixed at 0
    mmd_cell u_c0 (.fin(fin), .rst_n(rst_n), .modin(mo1), .p(mc), .fo(f1), .modout(mo0));
    mmd_cell u_c1 (.fin(f1), .rst_n(rst_n), .modin(1'b1), .p(1'b0), .fo(f2), .modout(mo1));

    // Counters on the prescaler output. mc is set at the start of each prescaler cycle and is read by the
    // first cell near the end of that cycle.
    always @(posedge f2 or negedge rst_n) begin
        if (!rst_n) begin
            pc <= 5'd1; sc <= 2'd0; mc <= 1'b0; div_out <= 1'b0;
        end else if (pc == 5'd1) begin       // last prescaler cycle: load the next ratio
            pc <= n[6:2]; sc <= n[1:0]; mc <= (n[1:0] != 2'd0); div_out <= 1'b1;
        end else begin
            pc <= pc - 5'd1; div_out <= 1'b0;
            if (sc != 2'd0) sc <= sc - 2'd1;
            mc <= (sc > 2'd1);
        end
    end
endmodule
