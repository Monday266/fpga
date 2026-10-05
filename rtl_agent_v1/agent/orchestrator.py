"""Multi-Agent Orchestration Engine for RTL Agent V1.

Coordinates:
- Spec Architect (SpecAgent)
- RTL Coder (CoderAgent)
- Verification Critic (VerifierAgent)
- Diagnostic Repairer (RepairAgent)
- Vivado EDA tool ladder (Interface -> Lint -> Simulation -> Synthesis)
"""

from __future__ import annotations

import json
import os
import time

from .coder_agent import CoderAgent
from .llm import LLM
from .repair_agent import RepairAgent
from .skills import Skill, load_skills, select_skills
from .spec_agent import SpecAgent
from .tools import RtlToolchain, check_and_patch_interface
from .verifier_agent import VerifierAgent

MAX_ROUNDS = int(os.environ.get("AGENT_MAX_ROUNDS", "4"))
DEADLINE_S = float(os.environ.get("AGENT_DEADLINE_S", "360"))
RESERVE_S = float(os.environ.get("AGENT_RESERVE_S", "20"))


class TraceLogger:
    def __init__(self, path: str):
        self.path = path
        self._fh = open(path, "w", encoding="utf-8")

    def log(self, **fields) -> None:
        fields.setdefault("ts", round(time.time(), 3))
        self._fh.write(json.dumps(fields, ensure_ascii=False) + "\n")
        self._fh.flush()

    def close(self) -> None:
        try:
            self._fh.close()
        except OSError:
            pass


class MultiAgentOrchestrator:
    def __init__(self, skill_dir: str):
        self.llm = LLM()
        self.tools = RtlToolchain()
        self.skills = load_skills(skill_dir)

        # Initialize subagents
        self.spec_agent = SpecAgent(self.llm)
        self.coder_agent = CoderAgent(self.llm)
        self.verifier_agent = VerifierAgent(self.llm, self.tools)
        self.repair_agent = RepairAgent(self.llm)

    def solve(self, prompt: str, interface: str, trace: TraceLogger) -> str:
        started = time.time()

        trace.log(
            tool="agent", event="start", architecture="multi_agent_v1",
            llm=self.llm.describe(), vivado_available=self.tools.available,
            skills_loaded=[s.name for s in self.skills]
        )

        # ------------------------------------------------ Phase 1: Spec Architect
        t0 = time.time()
        spec = self.spec_agent.analyze(prompt, interface)
        trace.log(
            tool="spec_architect", event="spec_derived",
            spec=spec.to_dict(), elapsed_s=round(time.time() - t0, 3)
        )

        # ------------------------------------------------ Phase 2: RTL Coder (Initial Draft)
        t0 = time.time()
        initial_skills = select_skills(self.skills, "initial", prompt)
        code = self.coder_agent.generate(spec, prompt, initial_skills)
        trace.log(
            tool="rtl_coder", round=1, event="code_generated",
            code_len=len(code), elapsed_s=round(time.time() - t0, 3)
        )

        current_code = code
        best_code = code

        # ------------------------------------------------ Multi-Agent Iterative Testing Loop
        for rnd in range(1, MAX_ROUNDS + 1):
            remaining = DEADLINE_S - (time.time() - started) - RESERVE_S
            if remaining <= 0:
                trace.log(tool="orchestrator", event="deadline_abort", round=rnd)
                break

            # Step 1: Zero-cost interface check & auto-patch
            rc_if, msg_if, patched_code = check_and_patch_interface(current_code, interface, prompt)
            trace.log(tool="check_interface", round=rnd, rc=rc_if, excerpt=msg_if[:400])
            current_code = patched_code
            best_code = current_code

            if rc_if != 0:
                # Urgent interface repair
                matched_skills = select_skills(self.skills, msg_if, "VRFC 10-3180")
                current_code = self.repair_agent.repair(spec, current_code, "interface", msg_if, matched_skills)
                continue

            # If Vivado toolchain is not available, we have achieved maximum possible verification
            if not self.tools.available:
                trace.log(tool="orchestrator", event="accept", reason="no_toolchain_available", round=rnd)
                return current_code

            # Step 2: L1 - xvlog + xelab single-module lint
            remaining = DEADLINE_S - (time.time() - started) - RESERVE_S
            rc_lint, log_lint = self.tools.lint(current_code, spec.module_name, timeout_s=min(remaining, 60))
            trace.log(tool="lint", round=rnd, rc=rc_lint, excerpt=log_lint[:1000])

            if rc_lint > 0:
                # Syntax or Elaboration failure
                matched_skills = select_skills(self.skills, log_lint)
                current_code = self.repair_agent.repair(spec, current_code, "lint", log_lint, matched_skills)
                continue

            # Step 3: L2 - Self-Checking Testbench Simulation (Verifier Critic)
            remaining = DEADLINE_S - (time.time() - started) - RESERVE_S
            t0 = time.time()
            rc_sim, log_sim = self.verifier_agent.verify(spec, prompt, current_code, timeout_s=min(remaining, 90))
            trace.log(
                tool="verifier_critic", round=rnd, rc=rc_sim,
                excerpt=log_sim[:1000], elapsed_s=round(time.time() - t0, 3)
            )

            if rc_sim > 0:
                # Simulation mismatch detected
                matched_skills = select_skills(self.skills, log_sim, "Mismatches", "ASSERTION")
                current_code = self.repair_agent.repair(spec, current_code, "simulation", log_sim, matched_skills)
                continue

            # Step 4: L3 - Vivado out-of-context synthesis
            remaining = DEADLINE_S - (time.time() - started) - RESERVE_S
            t0 = time.time()
            rc_synth, log_synth = self.tools.synth(current_code, spec.module_name, timeout_s=min(remaining, 120))
            trace.log(
                tool="synth", round=rnd, rc=rc_synth,
                excerpt=log_synth[:1000], elapsed_s=round(time.time() - t0, 3)
            )

            if rc_synth == 0:
                trace.log(tool="orchestrator", event="accept", status="L3_SYNTHESIS_SUCCESS", round=rnd)
                return current_code

            # Synthesis failure (latches, multi-driven nets, etc.)
            matched_skills = select_skills(self.skills, log_synth, "Synth 8-327", "inferring latch")
            current_code = self.repair_agent.repair(spec, current_code, "synthesis", log_synth, matched_skills)

        trace.log(tool="orchestrator", event="finished_max_rounds", bytes=len(best_code))
        return best_code
