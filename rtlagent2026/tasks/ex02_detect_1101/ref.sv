module RefModule (
  input  clk,
  input  reset,
  input  in,
  output reg detected
);

  reg [3:0] sr;

  always @(posedge clk) begin
    if (reset) begin
      sr       <= 4'b0000;
      detected <= 1'b0;
    end else begin
      sr       <= {sr[2:0], in};
      detected <= ({sr[2:0], in} == 4'b1101);
    end
  end

endmodule
