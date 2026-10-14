// SPDX-License-Identifier: BSD-3-Clause
// Arithmetic behavior follows MAME k054000.cpp (BSD-3-Clause),
// copyright holders David Haywood and Angelo Salese. See
// docs/BUCKY_INTEGRATION.md for the exact source pin and boundary choices.
// Standalone prerequisite; not connected to the Moo-only machine yet.
`default_nettype none
module k054000 (
    input  logic       clk,
    input  logic       rst,
    input  logic       we,
    input  logic [4:0] addr,       // word offset of the low-byte CPU window
    input  logic [7:0] d,
    output logic [7:0] q
);
    logic [7:0] regs [32];
    logic signed [31:0] ax, ay, bx, by;
    always_comb begin
        // A correction is signed, but the 24-bit raw center is unsigned.
        // Keep 32-bit intermediates: 0xffffff + 127 must not wrap to 24 bits.
        ax = $signed({8'd0, regs[1], regs[2], regs[3]}) +
             32'($signed(regs[4]));
        ay = $signed({8'd0, regs[9], regs[10], regs[11]}) +
             32'($signed(regs[12]));
        bx = $signed({8'd0, regs[21], regs[22], regs[23]});
        by = $signed({8'd0, regs[17], regs[18], regs[19]});
    end

    function automatic logic separated(
        input logic signed [31:0] ac, bc,
        input logic [7:0] aa, ba
    );
        logic signed [31:0] delta;
        logic [31:0] magnitude;
        logic [8:0] extent;
        delta = ac - bc;
        magnitude = (delta < 0) ? 32'(-delta) : 32'(delta);
        extent = {1'b0, aa} + {1'b0, ba};
        separated = (delta > 32'sd511) || (delta <= -32'sd1024) ||
                    (magnitude[8:0] > extent);
    endfunction

    assign q = (addr == 5'h18) ?
               {7'd0, separated(ax, bx, regs[6], regs[14]) |
                      separated(ay, by, regs[7], regs[15])} : 8'd0;

    always_ff @(posedge clk) begin
        if (rst) begin
            for (int i = 0; i < 32; i++) regs[i] <= 8'd0;
            regs[6] <= 8'd1;
            regs[7] <= 8'd1;
            regs[14] <= 8'd1;
            regs[15] <= 8'd1;
        end else if (we) begin
            case (addr)
                5'h01, 5'h02, 5'h03, 5'h04, 5'h06, 5'h07,
                5'h09, 5'h0a, 5'h0b, 5'h0c, 5'h0e, 5'h0f,
                5'h11, 5'h12, 5'h13, 5'h15, 5'h16, 5'h17:
                    regs[addr] <= d;
                default: ;
            endcase
        end
    end
endmodule
`default_nettype wire
