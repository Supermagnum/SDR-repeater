`timescale 1ns/1ps
// One RM_IHPSG13_1P_64x16_c2 for both half-band delay lines.
// I ages 0..30 use words 0..30. Q ages 0..30 use words 32..62.
// The TX line is shorter and uses the same map while TX is the
// active mode. A_DLY is tied high, which is what the model requires.
// Simulation uses the same cycle: the read data is valid after the
// clock that presented the address. Synthesis keeps the PDK cell.

module hb_sram (
    input  logic        clk,
    input  logic        men,
    input  logic        wen,
    input  logic        ren,
    input  logic [5:0]  addr,
    input  logic [15:0] din,
    output logic [15:0] dout
);

`ifdef SYNTHESIS
    RM_IHPSG13_1P_64x16_c2 u_ram (
        .A_CLK(clk),
        .A_MEN(men),
        .A_WEN(wen),
        .A_REN(ren),
        .A_ADDR(addr),
        .A_DIN(din),
        .A_DLY(1'b1),
        .A_DOUT(dout)
    );
`else
    logic [15:0] mem [0:63];
    integer ri;
    initial begin
        dout = '0;
        for (ri = 0; ri < 64; ri = ri + 1) mem[ri] = '0;
    end
    always @(posedge clk) begin
        if (men && wen) mem[addr] <= din;
        else if (men && ren) dout <= mem[addr];
    end
`endif

endmodule

`ifdef SYNTHESIS
(* blackbox *)
module RM_IHPSG13_1P_64x16_c2 (
    input  A_CLK,
    input  A_MEN,
    input  A_WEN,
    input  A_REN,
    input  [5:0] A_ADDR,
    input  [15:0] A_DIN,
    input  A_DLY,
    output [15:0] A_DOUT
);
endmodule
`endif
