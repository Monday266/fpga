"""Toolchain interface and deterministic verification utilities for RTL Agent V1.

Provides:
- Interface verification and auto-patching
- xvlog + xelab single module linting (L1)
- xsim self-checking testbench simulation (L2 bridge)
- Vivado synth_design out-of-context synthesis (L3)
- Structured diagnostic log summarizer
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import textwrap

PART = os.environ.get("RTL_PART", "xczu3eg-sbva484-1-e")


def _scratch_dir() -> str | None:
    d = os.environ.get("AGENT_SCRATCH")
    if d:
        os.makedirs(d, exist_ok=True)
        return d
    return None


def _run(cmd: list[str], cwd: str, timeout_s: float) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout_s,
            check=False,
            text=True,
            errors="replace",
        )
        return proc.returncode, proc.stdout
    except subprocess.TimeoutExpired:
        return 124, f"command timed out after {timeout_s:.1f}s: {' '.join(cmd)}"
    except FileNotFoundError as exc:
        return 127, f"command not found: {exc}"


class RtlToolchain:
    def __init__(self) -> None:
        self.xvlog = shutil.which("xvlog")
        self.xelab = shutil.which("xelab")
        self.xsim = shutil.which("xsim")
        self.vivado = shutil.which("vivado")
        self.reason = ""

        missing = [n for n, p in (("xvlog", self.xvlog), ("xelab", self.xelab),
                                  ("xsim", self.xsim), ("vivado", self.vivado)) if not p]
        if missing:
            self.reason = f"not on PATH: {', '.join(missing)}; source your Vivado settings64.sh"

    @property
    def available(self) -> bool:
        return not self.reason

    # ------------------------------------------------------------- L1: lint
    def lint(self, source: str, top: str, timeout_s: float = 120.0) -> tuple[int, str]:
        """Verify DUT parses and elaborates without testbench."""
        if not self.available:
            return -1, f"vivado unavailable: {self.reason}"

        work = tempfile.mkdtemp(prefix="agent_lint_", dir=_scratch_dir())
        try:
            src = os.path.join(work, "solution.sv")
            with open(src, "w", encoding="utf-8") as fh:
                fh.write(source)

            rc, out = _run([self.xvlog or "xvlog", "--sv", "solution.sv"], work, timeout_s)
            if rc != 0:
                return 1, summarize_log(out)

            rc, out2 = _run([self.xelab or "xelab", top, "-s", "dut_snapshot"], work, timeout_s)
            return (0 if rc == 0 else 1), summarize_log(out + "\n" + out2)
        finally:
            if os.environ.get("AGENT_KEEP_WORK") != "1":
                shutil.rmtree(work, ignore_errors=True)

    # ---------------------------------------------------- L2: self-simulation
    def run_sim(self, dut_source: str, tb_source: str, tb_top: str = "tb_self_check",
                timeout_s: float = 180.0) -> tuple[int, str]:
        """Run self-checking simulation on DUT + synthesized Testbench."""
        if not self.available:
            return -1, f"vivado unavailable: {self.reason}"

        work = tempfile.mkdtemp(prefix="agent_sim_", dir=_scratch_dir())
        try:
            with open(os.path.join(work, "dut.sv"), "w", encoding="utf-8") as fh:
                fh.write(dut_source)
            with open(os.path.join(work, "tb.sv"), "w", encoding="utf-8") as fh:
                fh.write(tb_source)

            # 1. Compile both
            rc, out1 = _run([self.xvlog or "xvlog", "--sv", "dut.sv", "tb.sv"], work, timeout_s / 3)
            if rc != 0:
                return 1, "TB compilation failed:\n" + summarize_log(out1)

            # 2. Elaborate
            rc, out2 = _run([self.xelab or "xelab", tb_top, "-s", "sim_snap", "-R"], work, timeout_s / 3)
            full_log = out1 + "\n" + out2

            # Check outputs
            if "TB_SUCCESS" in out2:
                return 0, "Self-checking testbench passed successfully."
            if "TB_FAILURE" in out2 or "ASSERTION FAILED" in out2 or "Mismatches" in out2:
                return 1, "Self-checking testbench reported mismatch:\n" + summarize_log(out2)

            return (0 if rc == 0 else 1), summarize_log(full_log)
        finally:
            if os.environ.get("AGENT_KEEP_WORK") != "1":
                shutil.rmtree(work, ignore_errors=True)

    # ----------------------------------------------------------- L3: synth
    def synth(self, source: str, top: str, timeout_s: float = 240.0) -> tuple[int, str]:
        """Run out-of-context synthesis targeting ZU3EG."""
        if not self.available:
            return -1, f"vivado unavailable: {self.reason}"

        work = tempfile.mkdtemp(prefix="agent_synth_", dir=_scratch_dir())
        try:
            with open(os.path.join(work, "solution.sv"), "w", encoding="utf-8") as fh:
                fh.write(source)
            with open(os.path.join(work, "synth.tcl"), "w", encoding="utf-8") as fh:
                fh.write(
                    textwrap.dedent(
                        f"""\
                        read_verilog -sv solution.sv
                        synth_design -top {top} -part {PART} -mode out_of_context
                        """
                    )
                )
            rc, out = _run(
                [self.vivado or "vivado", "-mode", "batch", "-source", "synth.tcl",
                 "-nojournal", "-log", "synth.log"],
                work, timeout_s,
            )
            ok = rc == 0 and ("Synthesis finished" in out or "Finished Technology Mapping" in out)
            return (0 if ok else 1), summarize_log(out)
        finally:
            if os.environ.get("AGENT_KEEP_WORK") != "1":
                shutil.rmtree(work, ignore_errors=True)


# ------------------------------------------------------- Interface contract checking

_PROMPT_PORT_RE = re.compile(
    r"^\s*-\s*(input|output|inout)\s+([A-Za-z_]\w*)\s*,?"
    r"\s*(?:\(\s*(\d+)\s*(?:bits?|位)\s*\))?\s*$",
    re.MULTILINE
)


def ports_from_prompt(prompt: str) -> tuple[str, list[tuple[str, int, str]]]:
    """Extract top module name and port list (dir, width, name) from prompt text."""
    text = prompt or ""
    ports = [(d, int(w) if w else 1, n) for d, n, w in _PROMPT_PORT_RE.findall(text)]

    m = re.search(r"module\s+(?:named\s+)?([A-Za-z_]\w*)", text)
    top_name = m.group(1) if m else "TopModule"
    if top_name in ("with", "the", "named", "implement"):
        top_name = "TopModule"
    return top_name, ports


def _parse_ports_from_header(decl: str) -> list[tuple[str, int, str]]:
    """Parse ports from Verilog module header."""
    res = []
    # Strip comments
    decl = re.sub(r"//.*", "", decl)
    decl = re.sub(r"/\*.*?\*/", "", decl, flags=re.DOTALL)

    for item in decl.split(","):
        item = item.strip()
        if not item:
            continue
        m = re.search(r"\b(input|output|inout)\s+(?:reg\s+|wire\s+|logic\s+)?(?:signed\s+)?(?:\[\s*(\d+)\s*:\s*(\d+)\s*\]\s+)?([a-zA-Z_]\w*)", item)
        if m:
            direction = m.group(1)
            msb, lsb = m.group(2), m.group(3)
            name = m.group(4)
            width = (abs(int(msb) - int(lsb)) + 1) if (msb is not None and lsb is not None) else 1
            res.append((direction, width, name))
    return res


def check_and_patch_interface(source: str, interface: str, prompt: str = "") -> tuple[int, str, str]:
    """Check module interface contract and perform non-destructive header patching if needed.

    Returns: (rc, diagnosis_message, patched_or_original_source)
    """
    want_name = None
    want_ports = []

    if interface and interface.strip():
        m_mod = re.search(r"module\s+([A-Za-z_]\w*)\s*(?:#\s*\([^)]*\)\s*)?\((.*?)\)\s*;", interface, re.DOTALL)
        if m_mod:
            want_name = m_mod.group(1)
            want_ports = _parse_ports_from_header(m_mod.group(2))

    if not want_ports:
        want_name, want_ports = ports_from_prompt(prompt)

    if not want_name:
        want_name = "TopModule"

    m_got = re.search(r"module\s+([A-Za-z_]\w*)\s*(?:#\s*\([^)]*\)\s*)?\((.*?)\)\s*;", source, re.DOTALL)
    if not m_got:
        return 1, "ERROR: No module declaration found in generated Verilog code", source

    got_name = m_got.group(1)
    got_ports = _parse_ports_from_header(m_got.group(2))

    problems = []
    if got_name != want_name:
        problems.append(f"Module name mismatch: got '{got_name}', required '{want_name}'")

    want_map = {n: (d, w) for d, w, n in want_ports}
    got_map = {n: (d, w) for d, w, n in got_ports}

    for name in want_map:
        if name not in got_map:
            problems.append(f"Missing required port '{name}'")
    for name in got_map:
        if name not in want_map:
            problems.append(f"Extra undeclared port '{name}'")

    for name in want_map.keys() & got_map.keys():
        wd, ww = want_map[name]
        gd, gw = got_map[name]
        if wd != gd:
            problems.append(f"Port '{name}' direction mismatch: required {wd}, got {gd}")
        if ww != gw:
            problems.append(f"Port '{name}' width mismatch: required {ww}-bit, got {gw}-bit")

    # If minor naming or header issue, attempt in-place surgical header repair
    patched = source
    if problems and want_ports:
        # Construct compliant standard header
        port_lines = []
        for d, w, n in want_ports:
            w_str = f"[{w-1}:0] " if w > 1 else ""
            # if output, determine if reg is needed by grepping assignments in body
            is_output = (d == "output")
            type_str = "reg " if (is_output and re.search(rf"\b{n}\s*<=", source)) else ""
            port_lines.append(f"  {d} {type_str}{w_str}{n}")
        new_header = f"module {want_name} (\n" + ",\n".join(port_lines) + "\n);"

        # Replace existing header
        patched = re.sub(
            r"module\s+[A-Za-z_]\w*\s*(?:#\s*\([^)]*\)\s*)?\((.*?)\)\s*;",
            new_header,
            source,
            count=1,
            flags=re.DOTALL
        )
        return (0 if len(problems) <= 2 else 1), "Header auto-aligned to interface contract: " + "; ".join(problems), patched

    if problems:
        return 1, "Interface Contract Violation: " + "; ".join(problems), source

    return 0, "Interface contract fully satisfied.", source


def summarize_log(log: str, max_lines: int = 35) -> str:
    """Categorized summary filter for Vivado and Simulation diagnostic logs."""
    if not log:
        return ""

    lines = log.splitlines()
    critical_lines = []
    error_patterns = [
        re.compile(r"ERROR:\s*\[.*?\]"),
        re.compile(r"CRITICAL WARNING:\s*\[.*?\]"),
        re.compile(r"syntax error", re.IGNORECASE),
        re.compile(r"TB_FAILURE"),
        re.compile(r"ASSERTION FAILED"),
        re.compile(r"Mismatches:"),
        re.compile(r"cannot find port", re.IGNORECASE),
        re.compile(r"inferring latch", re.IGNORECASE),
        re.compile(r"multi-driven net", re.IGNORECASE),
    ]

    for line in lines:
        if any(pat.search(line) for pat in error_patterns):
            critical_lines.append(line.strip())

    if critical_lines:
        return "\n".join(critical_lines[:max_lines])

    # Fallback to tail of log
    return "\n".join(lines[-max_lines:])
