// Private asset identity gate. The exact EAB images are checked by the host
// builders (CRC32+SHA1 per member and final SHA256); the hardware additionally
// requires an ordered, complete download and its known CRC32 before reset exit.
`default_nettype none
module konami_rom_profile (
    input logic clk,
    input logic dl_we,
    input logic [24:0] dl_addr,
    input logic [7:0] dl_data,
    output logic bucky,
    output logic valid
);
    logic we_d;
    logic [31:0] crc;
    logic [24:0] next_addr;
    logic ordered;
    initial begin
        bucky = 1'b0; valid = 1'b0; we_d = 1'b0;
        crc = 32'hffffffff; next_addr = 25'd0; ordered = 1'b0;
    end
    function automatic [31:0] advance(input [31:0] c, input [7:0] d);
        logic [31:0] v;
        v = c ^ {24'd0, d};
        for (int i = 0; i < 8; i++)
            v = (v >> 1) ^ (v[0] ? 32'hedb88320 : 32'd0);
        advance = v;
    endfunction
    always_ff @(posedge clk) begin
        we_d <= dl_we;
        if (dl_we && !we_d) begin
            if (dl_addr == 25'd0) begin
                crc <= advance(32'hffffffff, dl_data);
                next_addr <= 25'd1;
                ordered <= 1'b1;
                bucky <= 1'b0;
                valid <= 1'b0;
            end else begin
                crc <= advance(crc, dl_data);
                next_addr <= dl_addr + 25'd1;
                if (dl_addr != next_addr) ordered <= 1'b0;
                // The longer Bucky image reaches its main program here;
                // select before its default EEPROM arrives. Final CRC gates use.
                if (dl_addr == 25'h0e00000) bucky <= 1'b1;
                valid <= ordered && dl_addr == next_addr &&
                    ((!bucky && dl_addr == 25'h0d4007f &&
                      ~advance(crc, dl_data) == 32'h77d55c6a) ||
                     (bucky && dl_addr == 25'h0f4007f &&
                      ~advance(crc, dl_data) == 32'h424601ae));
            end
        end
    end
endmodule
`default_nettype wire
