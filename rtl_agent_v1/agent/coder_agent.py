"""Subagent: RTL Coder.

Role:
Translates the formal hardware specification into synthesizable Verilog/SystemVerilog
that strictly conforms to Vivado rules and the AMD target part (xczu3eg-sbva484-1-e).
"""

from __future__ import annotations

from .llm import LLM, extract_code
from .skills import Skill
from .spec_agent import HardwareSpec


class CoderAgent:
    def __init__(self, llm: LLM):
        self.llm = llm

    def generate(self, spec: HardwareSpec, prompt: str, injected_skills: list[Skill] | None = None) -> str:
        """Draft synthesizable RTL implementation conforming to spec."""
        sys_prompt = (
            "You are a Senior Digital ASIC/FPGA Front-End Design Engineer. "
            "Implement a clean, synthesizable Verilog/SystemVerilog module for AMD Vivado (target xczu3eg-sbva484-1-e, 5ns clock).\n\n"
            "CRITICAL DESIGN RULES:\n"
            "1. Module name and port list MUST exactly match the Hardware Specification. Do NOT rename, omit, or add ports.\n"
            "2. Do NOT write testbench code, initial blocks with delays (#), or $finish.\n"
            "3. Sequential logic must use non-blocking assignments (<=). Combinational logic must use blocking assignments (=).\n"
            "4. For combinational always @(*), ensure all branches and signals have default assignments to prevent unintended latches.\n"
            "5. Respect reset semantics: synchronicity (sync vs async) and polarity (active-high vs active-low).\n"
            "6. Output ONLY a single ```verilog code block. No explanations or prose outside the code block."
        )

        spec_summary = (
            f"Module Name: {spec.module_name}\n"
            f"Ports: {spec.ports}\n"
            f"Sequential: {spec.is_sequential} (Clock: '{spec.clock_port}', Reset: '{spec.reset_port}', "
            f"Polarity: {spec.reset_polarity}, Sync: {spec.reset_sync}, Reset Value: {spec.reset_value})\n"
            f"Core Logic: {spec.core_logic_summary}\n"
        )

        user_content = f"## Original Task Description:\n{prompt}\n\n## Formal Hardware Specification:\n{spec_summary}\n"

        messages = [{"role": "system", "content": sys_prompt}]

        if injected_skills:
            skill_text = "\n\n".join(s.render(2500) for s in injected_skills)
            messages.append({
                "role": "system",
                "content": f"Apply the following hardware engineering domain skills:\n\n{skill_text}"
            })

        messages.append({"role": "user", "content": user_content})

        res = self.llm.chat(messages, temperature=0.2, max_tokens=2048)
        code = extract_code(res.text)
        return code
