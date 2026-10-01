// Official testbench for ex02_detect_1101.
//
// NOT handed to the agent -- this is what decides L2.
//
// The stimulus deliberately includes an overlapping occurrence (1101101) and a
// mid-stream synchronous reset. A detector built on a counter instead of a
// shift register usually passes the first and fails the second.

`timescale 1ps/1ps

module tb();

  int errors = 0;
  int clocks = 0;

  reg clk = 0;
  initial forever #5 clk = ~clk;

  logic reset;
  logic in;
  logic detected_ref;
  logic detected_dut;

  RefModule good1 (.clk(clk), .reset(reset), .in(in), .detected(detected_ref));
  TopModule  dut1  (.clk(clk), .reset(reset), .in(in), .detected(detected_dut));

  wire tb_match = (detected_ref === (detected_ref ^ detected_dut ^ detected_ref));

  task drive(input bit r, input bit d);
    @(negedge clk) begin reset <= r; in <= d; end
  endtask

  initial begin
    reset = 1; in = 0;
    repeat (2) @(negedge clk);

    // Overlapping pattern: 1101101 must fire twice.
    drive(0,1); drive(0,1); drive(0,0); drive(0,1);
    drive(0,1); drive(0,0); drive(0,1);

    // Synchronous reset in the middle of a partial match.
    drive(0,1); drive(0,1); drive(1,0); drive(0,1);

    // Near misses: 1100, 0101, 1111.
    drive(0,1); drive(0,1); drive(0,0); drive(0,0);
    drive(0,0); drive(0,1); drive(0,0); drive(0,1);
    drive(0,1); drive(0,1); drive(0,1); drive(0,1);

    // Random tail.
    repeat (200) drive($random & 1, $random & 1);

    repeat (2) @(negedge clk);
    $finish;
  end

  always @(posedge clk) begin
    if ($time > 10) begin
      clocks++;
      if (!tb_match) errors++;
    end
  end

  final begin
    $display("Hint: Total mismatched samples is %1d out of %1d samples", errors, clocks);
    $display("Mismatches: %1d in %1d samples", errors, clocks);
  end

  initial begin
    #1000000;
    $display("TIMEOUT");
    $finish;
  end

endmodule
