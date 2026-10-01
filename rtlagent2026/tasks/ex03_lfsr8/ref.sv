module RefModule (
  input            clk,
  input            reset,
  input            load,
  input      [7:0] data,
  output reg [7:0] q
);

  wire feedback = q[7] ^ q[5] ^ q[4] ^ q[3];

  always @(posedge clk) begin
    if (reset)      q <= 8'h01;
    else if (load)  q <= data;
    else            q <= {q[6:0], feedback};
  end

endmodule
