// Reference solution for ex03_lfsr8.
//
// Only purpose: proving the judging pipeline reaches L3 on a known-good input.
// Do not feed it to your agent.

module TopModule (
  input            clk,
  input            reset,
  input            load,
  input      [7:0] data,
  output reg [7:0] q
);

  always @(posedge clk) begin
    if (reset)
      q <= 8'h01;
    else if (load)
      q <= data;
    else
      q <= {q[6:0], q[7] ^ q[5] ^ q[4] ^ q[3]};
  end

endmodule
