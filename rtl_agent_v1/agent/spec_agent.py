"""Subagent: Spec Architect.

Role:
Parses informal problem descriptions and interface declarations into a formal,
unambiguous hardware specification and verification plan.
"""

from __future__ import annotations

import json
from .llm import LLM, extract_json
from .tools import ports_from_prompt


class HardwareSpec:
    def __init__(self, data: dict):
        self.module_name = data.get("module_name", "TopModule")
        self.ports = data.get("ports", [])
        self.is_sequential = data.get("is_sequential", False)
        self.clock_port = data.get("clock_port", "clk" if self.is_sequential else "")
        self.reset_port = data.get("reset_port", "reset" if self.is_sequential else "")
        self.reset_polarity = data.get("reset_polarity", "active_high")
        self.reset_sync = data.get("reset_sync", "sync")
        self.reset_value = data.get("reset_value", "0")
        self.core_logic_summary = data.get("core_logic_summary", "")
        self.test_scenarios = data.get("test_scenarios", [])

    def to_dict(self) -> dict:
        return {
            "module_name": self.module_name,
            "ports": self.ports,
            "is_sequential": self.is_sequential,
            "clock_port": self.clock_port,
            "reset_port": self.reset_port,
            "reset_polarity": self.reset_polarity,
            "reset_sync": self.reset_sync,
            "reset_value": self.reset_value,
            "core_logic_summary": self.core_logic_summary,
            "test_scenarios": self.test_scenarios,
        }


class SpecAgent:
    def __init__(self, llm: LLM):
        self.llm = llm

    def analyze(self, prompt: str, interface: str) -> HardwareSpec:
        """Derive hardware contract and verification test plan from task input."""
        # 1. Deterministic port baseline extraction
        fallback_top, fallback_ports = ports_from_prompt(prompt)
        fb_port_list = [{"name": n, "direction": d, "width": w} for d, w, n in fallback_ports]

        sys_prompt = (
            "You are an expert Digital Hardware System Architect. "
            "Analyze the given FPGA design task and produce a strict, formal JSON specification.\n\n"
            "Output MUST be a single ```json block with the following keys:\n"
            "- module_name: exact top module name\n"
            "- ports: list of {name: str, direction: 'input'|'output', width: int}\n"
            "- is_sequential: bool (false if purely combinational)\n"
            "- clock_port: name of clock port (empty if combinational)\n"
            "- reset_port: name of reset port (empty if none)\n"
            "- reset_polarity: 'active_high' or 'active_low'\n"
            "- reset_sync: 'sync' or 'async'\n"
            "- reset_value: value upon reset\n"
            "- core_logic_summary: concise description of FSM, counters, or operations\n"
            "- test_scenarios: list of 3-5 key test stimulus vectors with expected outputs\n"
        )

        user_content = f"## Problem Description:\n{prompt}\n\n## Interface:\n{interface or '(No interface.txt provided)'}"

        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_content},
        ]

        res = self.llm.chat(messages, temperature=0.1, max_tokens=1024)
        parsed = extract_json(res.text)

        if not parsed or not parsed.get("ports"):
            # Fallback to deterministic extraction
            parsed = {
                "module_name": fallback_top,
                "ports": fb_port_list or [{"name": "clk", "direction": "input", "width": 1},
                                          {"name": "q", "direction": "output", "width": 8}],
                "is_sequential": any("clk" in p["name"].lower() for p in fb_port_list),
                "clock_port": "clk" if any("clk" in p["name"].lower() for p in fb_port_list) else "",
                "reset_port": "reset" if any("reset" in p["name"].lower() or "rst" in p["name"].lower() for p in fb_port_list) else "",
                "reset_polarity": "active_low" if any("rst_n" in p["name"].lower() or "reset_n" in p["name"].lower() for p in fb_port_list) else "active_high",
                "reset_sync": "async" if "asynchronous" in prompt.lower() else "sync",
                "core_logic_summary": "Extracted via fallback deterministic parser",
                "test_scenarios": []
            }

        # Force module name and ports consistency
        if fallback_top and parsed.get("module_name") != fallback_top:
            parsed["module_name"] = fallback_top

        return HardwareSpec(parsed)
