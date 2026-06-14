`default_nettype none

// Sequences through RAM read addresses at a fixed rate. `raddr`
// advances by one every CLK_FREQ/PLAY_RATE_HZ clock cycles and wraps
// from RAM_DEPTH-1 back to 0. `advance` pulses high for one cycle on
// each step.
//
// NOTE: RAM_DEPTH defaults to 32 to match ram_256x8.v.
module pattern_player #(
    parameter CLK_FREQ     = 10_000_000,
    parameter PLAY_RATE_HZ = 1000,
    parameter RAM_DEPTH    = 32
)(
    input  wire       clk,
    input  wire       rst_n,
    output reg  [7:0] raddr,
    output reg        advance
);

    localparam DIVISOR = CLK_FREQ / PLAY_RATE_HZ;
    localparam CNT_W   = $clog2(DIVISOR);

    reg [CNT_W-1:0] tick_cnt;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            tick_cnt <= {CNT_W{1'b0}};
            raddr    <= 8'd0;
            advance  <= 1'b0;
        end else begin
            advance <= 1'b0;
            if (tick_cnt == DIVISOR - 1) begin
                tick_cnt <= {CNT_W{1'b0}};
                advance  <= 1'b1;
                if (raddr == RAM_DEPTH - 1) begin
                    raddr <= 8'd0;
                end else begin
                    raddr <= raddr + 1'b1;
                end
            end else begin
                tick_cnt <= tick_cnt + 1'b1;
            end
        end
    end

endmodule
