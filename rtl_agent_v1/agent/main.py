"""Top-level CLI entry point for RTL Agent V1."""

from __future__ import annotations

import argparse
import os
import sys

from .orchestrator import MultiAgentOrchestrator, TraceLogger

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SKILL_DIR = os.path.join(ROOT, "skill")


def read_task(input_dir: str) -> tuple[str, str]:
    def _read(fname: str) -> str:
        p = os.path.join(input_dir, fname)
        if os.path.isfile(p):
            with open(p, encoding="utf-8") as fh:
                return fh.read().strip()
        return ""
    return _read("prompt.txt"), _read("interface.txt")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="AMD FPGA 2026 - RTL Multi-Agent V1")
    ap.add_argument("--input", required=True, help="Directory containing prompt.txt and optional interface.txt")
    ap.add_argument("--output", required=True, help="Directory to emit solution.v and trace.jsonl")
    ap.add_argument("--top", default="", help="Optional top module override")
    args = ap.parse_args(argv)

    os.makedirs(args.output, exist_ok=True)
    sol_path = os.path.join(args.output, "solution.v")
    trace_path = os.path.join(args.output, "trace.jsonl")

    trace = TraceLogger(trace_path)
    code = ""

    try:
        prompt, interface = read_task(args.input)
        orchestrator = MultiAgentOrchestrator(SKILL_DIR)
        code = orchestrator.solve(prompt, interface, trace)
    except Exception as exc:
        trace.log(tool="agent", event="exception", error=f"{type(exc).__name__}: {exc}"[:400])
        print(f"RTL Agent Error: {type(exc).__name__}: {exc}", file=sys.stderr)
    finally:
        with open(sol_path, "w", encoding="utf-8") as fh:
            fh.write(code or "")
        trace.log(tool="agent", event="done", bytes=len(code or ""))
        trace.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
