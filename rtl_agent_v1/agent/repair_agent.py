"""Subagent: Diagnostic & Surgical Repairer.

Role:
Pinpoints root causes from tool diagnostics (syntax, elaboration, simulation assertion,
or synthesis latch errors), loads relevant Skill Pack rules, and executes targeted repairs.
"""

from __future__ import annotations

from .llm import LLM, extract_code
from .skills import Skill
from .spec_agent import HardwareSpec


class RepairAgent:
    def __init__(self, llm: LLM):
        self.llm = llm

    def repair(
        self,
        spec: HardwareSpec,
        broken_code: str,
        stage: str,
        error_log: str,
        skills: list[Skill] | None = None,
    ) -> str:
        """Apply targeted surgical repair based on toolchain diagnostics and skills."""
        sys_prompt = (
            "You are a Principal RTL Debugging and Optimization Specialist. "
            "Your job is to perform a SURGICAL FIX on the given Verilog implementation that failed verification.\n\n"
            "REPAIR GUIDELINES:\n"
            "1. Focus strictly on the root cause indicated in the tool log. Do NOT rewrite parts of the module that already work.\n"
            "2. Ensure the module header exactly preserves the required ports and module name: "
            f"module {spec.module_name} with ports {spec.ports}.\n"
            "3. If fixing syntax (VRFC 10-*): check missing semicolons, vector indices, begin/end block balance.\n"
            "4. If fixing logic mismatch: re-check reset priority, state machine transition conditions, or bitwise operators.\n"
            "5. If fixing synthesis latches (Synth 8-327): ensure all combinational always @(*) blocks assign default values to all outputs.\n"
            "6. Output ONLY the complete repaired module inside a single ```verilog block."
        )

        user_content = (
            f"## Verification Failure Stage: {stage.upper()}\n\n"
            f"## Tool Diagnostics / Error Excerpt:\n```\n{error_log}\n```\n\n"
            f"## Current RTL Code:\n```verilog\n{broken_code}\n```\n"
        )

        messages = [{"role": "system", "content": sys_prompt}]

        if skills:
            skill_text = "\n\n".join(s.render(2500) for s in skills)
            messages.append({
                "role": "system",
                "content": f"Apply the following expert repair skills:\n\n{skill_text}"
            })

        messages.append({"role": "user", "content": user_content})

        res = self.llm.chat(messages, temperature=0.0, max_tokens=2048)
        fixed_code = extract_code(res.text)
        return fixed_code or broken_code
