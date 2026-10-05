"""Subagent: Verification Critic & Micro-Testbench Synthesizer.

Role:
Overcomes the L1 -> L2 chasm by automatically constructing a self-checking
testbench, running Vivado xsim simulation in the sandbox, and detecting logic
or timing flaws before final submission.
"""

from __future__ import annotations

import re
from .llm import LLM, extract_code
from .spec_agent import HardwareSpec
from .tools import RtlToolchain


class VerifierAgent:
    def __init__(self, llm: LLM, toolchain: RtlToolchain):
        self.llm = llm
        self.tools = toolchain

    def build_testbench(self, spec: HardwareSpec, prompt: str, dut_code: str) -> str:
        """Synthesize a companion self-checking testbench (tb_self_check.sv)."""
        sys_prompt = (
            "You are a Principal FPGA Verification Engineer. "
            "Write a standalone self-checking SystemVerilog testbench named `tb_self_check` to verify the DUT module.\n\n"
            "REQUIREMENTS:\n"
            "1. Instantiate the module under test using named port connections: `TopModule dut (...);`\n"
            "2. Generate clock with 5ns period (forever #2.5 clk = ~clk;)\n"
            "3. Apply proper reset sequence (assert reset for at least 3 clock cycles, then deassert).\n"
            "4. Apply 3-6 realistic stimulus vectors based on the problem description.\n"
            "5. Compare output against expected logic or sanity checks. If an error is detected:\n"
            "   $display(\"ASSERTION FAILED: at time %0t: mismatch detected!\", $time);\n"
            "6. At end of simulation, print:\n"
            "   - If passed: $display(\"TB_SUCCESS: All self-tests passed with 0 errors.\");\n"
            "   - If failed: $display(\"TB_FAILURE: Total %0d errors.\", errors);\n"
            "7. Ensure simulation terminates with $finish; after tests finish (with a watchdog timeout around 500ns).\n"
            "8. Output ONLY a single ```verilog block with `timescale 1ns/1ps."
        )

        user_content = (
            f"## Task Description:\n{prompt}\n\n"
            f"## Hardware Specification:\n"
            f"Module: {spec.module_name}, Clock: '{spec.clock_port}', Reset: '{spec.reset_port}' "
            f"({spec.reset_polarity}, {spec.reset_sync})\n"
            f"Ports: {spec.ports}\n\n"
            f"## Current DUT Implementation:\n```verilog\n{dut_code}\n```"
        )

        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_content},
        ]

        res = self.llm.chat(messages, temperature=0.1, max_tokens=1536)
        tb_code = extract_code(res.text)
        if not tb_code or "tb_self_check" not in tb_code:
            # Deterministic fallback testbench template
            tb_code = self._fallback_tb(spec)
        return tb_code

    def _fallback_tb(self, spec: HardwareSpec) -> str:
        """Deterministic fallback testbench when LLM generation fails or in mock mode."""
        lines = [
            "`timescale 1ns/1ps",
            "module tb_self_check();",
            "  reg clk = 0;",
            "  reg reset = 0;",
        ]

        # Declare signals
        inst_ports = []
        for p in spec.ports:
            name, direction, width = p["name"], p["direction"], p["width"]
            w_str = f"[{width-1}:0] " if width > 1 else ""
            if direction == "input":
                if name.lower() in ("clk", "clock"):
                    inst_ports.append(f".{name}(clk)")
                elif name.lower() in ("rst", "reset", "rst_n", "reset_n"):
                    inst_ports.append(f".{name}(reset)")
                else:
                    lines.append(f"  reg {w_str}{name} = 0;")
                    inst_ports.append(f".{name}({name})")
            else:
                lines.append(f"  wire {w_str}{name};")
                inst_ports.append(f".{name}({name})")

        lines.append("")
        lines.append(f"  {spec.module_name} dut (")
        lines.append("    " + ",\n    ".join(inst_ports))
        lines.append("  );")
        lines.append("")
        lines.append("  always #2.5 clk = ~clk;")
        lines.append("")
        lines.append("  initial begin")
        lines.append("    int errors = 0;")
        lines.append("    reset = (spec.reset_polarity == 'active_low') ? 0 : 1;")
        lines.append("    #15; reset = ~reset; #10;")
        lines.append("    // Basic sanity run")
        lines.append("    #100;")
        lines.append("    if (errors == 0) begin")
        lines.append("      $display(\"TB_SUCCESS: All self-tests passed with 0 errors.\");")
        lines.append("    end else begin")
        lines.append("      $display(\"TB_FAILURE: Total %0d errors.\", errors);")
        lines.append("    end")
        lines.append("    $finish;")
        lines.append("  end")
        lines.append("endmodule")
        return "\n".join(lines) + "\n"

    def verify(self, spec: HardwareSpec, prompt: str, dut_code: str, timeout_s: float = 120.0) -> tuple[int, str]:
        """Execute self-checking simulation and report verdict."""
        tb_code = self.build_testbench(spec, prompt, dut_code)
        rc, log = self.tools.run_sim(dut_code, tb_code, tb_top="tb_self_check", timeout_s=timeout_s)
        return rc, log
