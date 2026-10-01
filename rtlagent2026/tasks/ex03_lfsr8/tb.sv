// Official testbench for ex03_lfsr8.
//
// NOT handed to the agent -- this is what decides L2.
//
// Drives reset and load simultaneously on purpose. Reset has priority; an
// implementation that writes the priority the other way round runs correctly
// for hundreds of cycles and fails only on those samples.

`timescale 1ps/1ps

module tb();

  int errors = 0;
  int clocks = 0;

  reg clk = 0;
  initial forever #5 clk = ~clk;

  logic       reset;
  logic       load;
  logic [7:0] data;
  logic [7:0] q_ref;
  logic [7:0] q_dut;

  RefModule good1 (.clk(clk), .reset(reset), .load(load), .data(data), .q(q_ref));
  TopModule  dut1  (.clk(clk), .reset(reset), .load(load), .data(data), .q(q_dut));

  wire tb_match = (q_ref === (q_ref ^ q_dut ^ q_ref));

  task drive(input bit r, input bit l, input [7:0] d);
    @(negedge clk) begin reset <= r; load <= l; data <= d; end
  endtask

  initial begin
    reset = 1; load = 0; data = 8'h00;
    repeat (2) @(negedge clk);

    // Free-run from the reset state.
    repeat (40) drive(0, 0, 8'h00);

    // Load a known seed, then free-run.
    drive(0, 1, 8'hA5);
    repeat (20) drive(0, 0, 8'h00);

    // reset and load asserted together -- reset must win.
    drive(1, 1, 8'h3C);
    repeat (4) drive(0, 0, 8'h00);

    // Loading all zeros: a real LFSR locks up here. That is correct behaviour
    // and the reference does it too; a "helpfully" reseeding DUT fails.
    drive(0, 1, 8'h00);
    repeat (8) drive(0, 0, 8'h00);

    drive(1, 0, 8'h00);
    repeat (150) drive(0, ($random & 15) == 0, $random);

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
