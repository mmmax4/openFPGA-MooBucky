//------------------------------------------------------------------------------
// K053251 priority, K054338 mixing and the palette: one pixel per dot, from
// the tile and sprite line buffers (docs/core-design.md 6; the reference is
// tools/moo_render.py render).
//
// Per pixel, as MAME's screen_update composes it:
//   background colour; the three sorted layers B/C/D back to front, each
//   opaque pen tagging the pixel 1, 2, 4 (the back one only when its
//   priority is below CI1's; the front one mixed per tile, below); the claiming sprite if its class lets it in front of the tag,
//   else the recorded shadow if its class does; layer A on top of all.
//
// Mixing, the board's rule and not MAME's: the two low bits of a tile's colour
// (which MAME's tile callback drops) are its K054338 mix code.  0 is solid;
// 1..3 select a PBLEND level as set_alpha_level(m) reads it, and a level of 0
// leaves the pixel out.  MAME instead blends the whole front layer at level 1
// while MIXPRI is set, which leaves the last boss's fog solid after the game
// fades it and clears MIXPRI, and hides the intro's ground (docs/hardware.md
// 7.3).  Only the front layer is mixed, as in MAME.
//
// The work for pixel h starts at the dot enable where hpos becomes h and the
// colour is registered on `rgb` at the next one: one dot of latency, which
// moo_video adds to the syncs.
//------------------------------------------------------------------------------
`default_nettype none

module moo_mixer (
    input  logic        clk,
    input  logic        rst,
    input  logic        bucky,
    input  logic        cen_pix,
    input  logic  [8:0] hpos,           // bitmap x of the dot being started
    input  logic        lbuf,           // line buffer half being shown
    input  logic        visible,        // this dot is in the 384 x 224 window

    // K053251, low byte, 16 registers of 6 bits
    input  logic        k251_we,
    input  logic  [3:0] k251_addr,
    input  logic  [5:0] k251_d,
    output logic  [6:0] spr_colorbase,
    output logic  [5:0] lp0, lp1, lp2,

    // K054338, 16 words
    input  logic        k338_we,
    input  logic  [3:0] k338_addr,
    input  logic [15:0] k338_d,
    input  logic  [1:0] k338_be,        // {upper, lower} byte enables

    // palette RAM, CPU side: word address (0..4095), one clock latency
    input  logic        pal_we,
    input  logic [12:0] pal_addr,
    input  logic [15:0] pal_d,
    input  logic  [1:0] pal_be,
    output logic [15:0] pal_q,

    // tile line buffer read: {buf, x} -> 4 x {mix, colour, pen}, one clock latency
    output logic  [9:0] tl_addr,
    input  logic [43:0] tl_q,
    input  logic  [3:0] tl_valid,       // layers built for the shown line

    // sprite line buffer read (moo_sprites mixer port)
    output logic        sp_buf,
    output logic  [8:0] sp_x,
    input  logic        sp_claim,
    input  logic [12:0] sp_cdata,
    input  logic        sp_shadow,
    input  logic  [3:0] sp_sdata,

    output logic [23:0] rgb,

    // for a frozen-state bench: what the pixel was made of
    output logic [10:0] dbg_index,      // palette index on top (0x7FF: background)
    output logic        dbg_alpha,
    output logic        dbg_shadow
);
    // ------------------------------------------------------------ K053251
    logic [5:0] r251 [16];
    always_ff @(posedge clk) begin
        if (rst) for (int i = 0; i < 16; i++) r251[i] <= 6'd0;
        else if (k251_we) r251[k251_addr] <= k251_d;
    end
    // palette bases, in 16-colour units (reset_indexes)
    wire [6:0] cb_ci0 = {r251[9][1:0], 5'd0};
    wire [6:0] cb_ci2 = {r251[9][5:4], 5'd0};
    wire [6:0] cb_ci3 = {r251[10][2:0], 4'd0};
    wire [6:0] cb_ci4 = {r251[10][5:3], 4'd0};
    assign spr_colorbase = cb_ci0;

    // konami_sortlayers3 on layers 1..3 by CI2..CI4 priority, largest first:
    // compare-and-swap (0,1), (0,2), (1,2), swapping when less
    logic [1:0] ord [3];
    logic [5:0] opr [3];
    always_comb begin
        logic [1:0] tl; logic [5:0] tp;
        tl = 2'd0; tp = 6'd0;
        ord[0] = 2'd1; ord[1] = 2'd2; ord[2] = 2'd3;
        opr[0] = r251[2]; opr[1] = r251[3]; opr[2] = r251[4];
        if (opr[0] < opr[1]) begin tp = opr[0]; opr[0] = opr[1]; opr[1] = tp; tl = ord[0]; ord[0] = ord[1]; ord[1] = tl; end
        if (opr[0] < opr[2]) begin tp = opr[0]; opr[0] = opr[2]; opr[2] = tp; tl = ord[0]; ord[0] = ord[2]; ord[2] = tl; end
        if (opr[1] < opr[2]) begin tp = opr[1]; opr[1] = opr[2]; opr[2] = tp; tl = ord[1]; ord[1] = ord[2]; ord[2] = tl; end
    end
    assign lp0 = opr[0];
    assign lp1 = opr[1];
    assign lp2 = opr[2];
    wire back_drawn = (opr[0] < r251[1]);

    function automatic [6:0] lbase(input [1:0] l);
        case (l)
            2'd0: lbase = 7'h70;
            2'd1: lbase = cb_ci2;
            2'd2: lbase = cb_ci3;
            default: lbase = cb_ci4;
        endcase
    endfunction

    // ------------------------------------------------------------ K054338
    logic [15:0] r338 [16];
    always_ff @(posedge clk) begin
        if (rst) for (int i = 0; i < 16; i++) r338[i] <= 16'd0;
        else if (k338_we) begin
            if (k338_be[1]) r338[k338_addr][15:8] <= k338_d[15:8];
            if (k338_be[0]) r338[k338_addr][7:0]  <= k338_d[7:0];
        end
    end
    wire [23:0] bg     = {r338[0][7:0], r338[1]};
    wire        noclip = r338[15][5];
    // set_alpha_level(m), m = 1..3: PBLEND word 13 low byte, word 14 high
    // byte, word 14 low byte; 5 bits expanded to 8.  Registered.
    logic [7:0] lv [4];
    always_ff @(posedge clk) begin
        lv[0] <= 8'hFF;
        lv[1] <= {r338[13][4:0],  r338[13][4:2]};
        lv[2] <= {r338[14][12:8], r338[14][12:10]};
        lv[3] <= {r338[14][4:0],  r338[14][4:2]};
    end
    logic [7:0] alpha;                  // the front layer's, for the pixel in hand

    // ------------------------------------------------------------ palette
    // 2048 x 32, xRGB_888: word 2i = {x, R}, word 2i+1 = {G, B}
    (* ramstyle = "no_rw_check" *) logic [3:0][7:0] pal [4096];
    logic [31:0] pq_cpu, pq_vid;
    logic [10:0] pv_addr;
    // byte enables: word 2i is bytes 1:0 of entry i, word 2i+1 bytes 3:2
    wire [3:0] p_be = pal_we ? (pal_addr[0] ? {pal_be, 2'b00} : {2'b00, pal_be}) : 4'b0000;
    always_ff @(posedge clk) begin
        if (p_be[3]) pal[pal_addr[12:1]][3] <= pal_d[15:8];
        if (p_be[2]) pal[pal_addr[12:1]][2] <= pal_d[7:0];
        if (p_be[1]) pal[pal_addr[12:1]][1] <= pal_d[15:8];
        if (p_be[0]) pal[pal_addr[12:1]][0] <= pal_d[7:0];
        pq_cpu <= pal[pal_addr[12:1]];
    end
    always_ff @(posedge clk) pq_vid <= pal[{1'b0, pv_addr}];
    logic cpu_half;
    always_ff @(posedge clk) cpu_half <= pal_addr[0];
    // word 2i sits in bytes 1:0 of entry i, word 2i+1 in bytes 3:2
    assign pal_q = cpu_half ? pq_cpu[31:16] : pq_cpu[15:0];
    function automatic [23:0] pen_rgb(input [31:0] e);
        pen_rgb = {e[7:0], e[31:16]};           // R from word 0's low byte, then G, B
    endfunction

    // ------------------------------------------------------------ helpers
    function automatic [7:0] shade(input [7:0] c, input [8:0] d9, input nc);
        // shadow_table[rgb15]: 5 bits kept, expanded, the delta added (clamped
        // to +-255 by set_shadow_dRGB32), then clipped or wrapped
        logic signed [10:0] v, d;
        d = 11'($signed(d9));
        if (d < -11'sd255) d = -11'sd255;
        v = 11'({c[7:3], c[7:5]}) + d;
        if (nc) shade = v[7:0];
        else shade = (v < 0) ? 8'd0 : (v > 11'sd255) ? 8'hFF : v[7:0];
    endfunction

    // ------------------------------------------------------------ pipeline
    logic [3:0]  ph;                    // 0..11 within the dot
    // Snapshot sorted pixel order before decoding the returned line-buffer
    // word. Sprite-engine priorities stay combinational and unchanged.
    logic [1:0] pixel_ord [3];
    logic pixel_back_drawn;
    logic        vis_q, vis_d;
    logic        opA, opF, opM, opB, sprv, shdv, need2;
    logic [10:0] iA, iF, iM, iB, iS;
    logic [10:0] src1, src2;
    logic        s1bg, s2bg, useblend;
    logic [1:0]  preset;
    logic [23:0] c1, c2, px;

    // Split alpha products and addition across spare dot phases. Output still
    // arrives at the next dot enable; arithmetic matches alpha_blend_r32.
    logic [15:0] blend_s [3];
    logic [16:0] blend_d [3];
    wire [8:0] inv_alpha = 9'd256 - {1'b0, alpha};
    wire [16:0] blend_r = {1'b0, blend_s[2]} + blend_d[2];
    wire [16:0] blend_g = {1'b0, blend_s[1]} + blend_d[1];
    wire [16:0] blend_b = {1'b0, blend_s[0]} + blend_d[0];
    // the final colour: products at ph 9, blend at ph 10, shadow at ph 11
    logic [23:0] base;
    logic [23:0] n_px;
    always_comb begin
        logic [3:0] si;
        si = 4'd2 + {preset, 1'b0} + {2'd0, preset};         // SHAD1R + 3 * preset
        if (opA || sprv) n_px = c1;
        else if (shdv && preset != 2'd3)
            n_px = {shade(base[23:16], r338[si][8:0], noclip),
                    shade(base[15:8],  r338[si + 4'd1][8:0], noclip),
                    shade(base[7:0],   r338[si + 4'd2][8:0], noclip)};
        else n_px = base;
    end

    function automatic [10:0] lidx(input [7:0] e, input [1:0] l);
        logic [6:0] c;
        c = lbase(l) | {3'd0, e[7:4]};
        lidx = {c, e[3:0]};
    endfunction

    // what the pixel is made of, from the line buffers (latched at ph 2)
    logic        n_opA, n_opB, n_opM, n_opF, n_sprv, n_shdv;
    logic [10:0] n_iA, n_iB, n_iM, n_iF;
    logic  [7:0] n_aF;
    // Decode the physical lanes before the sorted-layer mux. In particular,
    // don't put the tile mux, alpha-level mux and opacity check in series.
    logic [7:0] lane_alpha [4];
    logic [10:0] lane_index [4];
    logic [3:0] lane_opaque, lane_front_opaque;
    function automatic [7:0] sorted_alpha(input [1:0] l);
        case (l)
            2'd1: sorted_alpha = lane_alpha[1];
            2'd2: sorted_alpha = lane_alpha[2];
            default: sorted_alpha = lane_alpha[3];
        endcase
    endfunction
    function automatic [10:0] sorted_index(input [1:0] l);
        case (l)
            2'd1: sorted_index = lane_index[1];
            2'd2: sorted_index = lane_index[2];
            default: sorted_index = lane_index[3];
        endcase
    endfunction
    function automatic sorted_opaque(input [3:0] opaque, input [1:0] l);
        case (l)
            2'd1: sorted_opaque = opaque[1];
            2'd2: sorted_opaque = opaque[2];
            default: sorted_opaque = opaque[3];
        endcase
    endfunction
    logic claim_q, shadow_q;
    logic [1:0] claim_class, shadow_class;
    function automatic class_visible(input [1:0] c, input f, m, b);
        case (c)
            2'd0: class_visible = 1'b1;
            2'd1: class_visible = !f;
            2'd2: class_visible = !(f || m);
            default: class_visible = !(f || m || b);
        endcase
    endfunction
    always_comb begin
        for (int l = 0; l < 4; l++) begin
            // Moo mixes per tile; Bucky uses MIXPRI/PBLEND1 on the front.
            lane_alpha[l] = bucky ? (r338[15][1] ? lv[1] : 8'hff)
                                  : lv[tl_q[11*l+8 +: 2]];
            lane_opaque[l] = tl_valid[l] && tl_q[11*l +: 4] != 4'd0;
            lane_front_opaque[l] = lane_opaque[l] && lane_alpha[l] != 8'd0;
            lane_index[l] = lidx(tl_q[11*l +: 8], tl_q[11*l+10] ? 2'd0 : 2'(l));
        end
        n_aF = sorted_alpha(pixel_ord[2]);
        n_opA = lane_opaque[0];
        n_opB = sorted_opaque(lane_opaque, pixel_ord[0]) && pixel_back_drawn;
        n_opM = sorted_opaque(lane_opaque, pixel_ord[1]);
        n_opF = sorted_opaque(lane_front_opaque, pixel_ord[2]);
        n_iA = lane_index[0];
        n_iB = sorted_index(pixel_ord[0]);
        n_iM = sorted_index(pixel_ord[1]);
        n_iF = sorted_index(pixel_ord[2]);
    end
    // The opacity tag is already registered at phase 2. Resolve the sprite
    // masks from it in phase 3, alongside source selection, not after all
    // tile/alpha decoding on the phase-2 critical path.
    always_comb begin
        n_sprv = claim_q && class_visible(claim_class, opF, opM, opB);
        n_shdv = shadow_q && class_visible(shadow_class, opF, opM, opB);
    end

    always_ff @(posedge clk) begin
        if (cen_pix) ph <= 4'd1; else if (ph != 4'd0 && ph != 4'd15) ph <= ph + 4'd1;
        if (cen_pix) begin
            rgb     <= vis_d ? px : 24'd0;
            tl_addr <= {lbuf, hpos};
            sp_buf  <= lbuf;
            sp_x    <= hpos;
            vis_q   <= visible;
        end
        if (ph == 4'd1) begin
            for (int i = 0; i < 3; i++) pixel_ord[i] <= ord[i];
            pixel_back_drawn <= back_drawn;
        end
        if (ph == 4'd2) begin
            opA <= n_opA; opB <= n_opB; opM <= n_opM; opF <= n_opF; alpha <= n_aF;
            iA <= n_iA; iB <= n_iB; iM <= n_iM; iF <= n_iF; iS <= sp_cdata[12:2];
            claim_q <= sp_claim; shadow_q <= sp_shadow;
            claim_class <= sp_cdata[1:0]; shadow_class <= sp_sdata[1:0];
            preset <= sp_sdata[3:2];
        end
        if (ph == 4'd3) begin
            sprv <= n_sprv; shdv <= n_shdv;
            // first colour: what is on top; second: what the front layer blends over
            useblend <= 1'b0; s2bg <= 1'b1; s1bg <= 1'b0; need2 <= 1'b0;
            if (opA)       src1 <= iA;
            else if (n_sprv) src1 <= iS;
            else if (opF) begin
                src1 <= iF;
                if (alpha != 8'hFF) begin
                    useblend <= 1'b1; need2 <= 1'b1;
                    if (opM)      begin src2 <= iM; s2bg <= 1'b0; end
                    else if (opB) begin src2 <= iB; s2bg <= 1'b0; end
                end
            end
            else if (opM)  src1 <= iM;
            else if (opB)  src1 <= iB;
            else           s1bg <= 1'b1;
        end
        if (ph == 4'd4) pv_addr <= src1;
        if (ph == 4'd6) begin c1 <= s1bg ? bg : pen_rgb(pq_vid); pv_addr <= src2; end
        if (ph == 4'd8) c2 <= s2bg ? bg : pen_rgb(pq_vid);
        if (ph == 4'd9) begin
            for (int i = 0; i < 3; i++) begin
                blend_s[i] <= 16'(c1[8*i +: 8]) * 16'(alpha);
                blend_d[i] <= 17'(c2[8*i +: 8]) * 17'(inv_alpha);
            end
        end
        if (ph == 4'd10) base <= useblend ? {blend_r[15:8], blend_g[15:8], blend_b[15:8]} : c1;
        if (ph == 4'd11) begin
            px         <= n_px;
            vis_d      <= vis_q;
            dbg_index  <= (opA || sprv || opF || opM || opB) ? src1 : 11'h7FF;
            dbg_alpha  <= useblend && !(opA || sprv);
            dbg_shadow <= shdv && !(opA || sprv);
        end
        if (rst) ph <= 4'd0;
    end
    wire _unused = &{1'b0, need2, 1'b0};
endmodule

`default_nettype wire
