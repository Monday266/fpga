// Reference solution for ex02_detect_1101.
//
// Only purpose: proving the judging pipeline reaches L3 on a known-good input.
// Do not feed it to your agent.
//
// Written as an explicit FSM rather than a shift-register compare, so it is not
// a character-for-character copy of RefModule -- the point is to exercise the
// judge, not to check that two identical files match.

module TopModule (
  input  clk,
  input  reset,
  input  in,
  output reg detected
);

  localparam S_IDLE = 3'd0,  // nothing matched yet
             S_1    = 3'd1,  // seen 1
             S_11   = 3'd2,  // seen 11
             S_110  = 3'd3;  // seen 110

  reg [2:0] state;

  always @(posedge clk) begin
    if (reset) begin
      state    <= S_IDLE;
      detected <= 1'b0;
    end else begin
      detected <= (state == S_110) && in;
      case (state)
        S_IDLE : state <= in ? S_1    : S_IDLE;
        S_1    : state <= in ? S_11   : S_IDLE;
        S_11   : state <= in ? S_11   : S_110;
        S_110  : state <= in ? S_1    : S_IDLE;
        default: state <= S_IDLE;
      endcase
    end
  end

endmodule
