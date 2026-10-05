"""Prevents infinite repair oscillation and enforces solution quality monotonicity."""

from __future__ import annotations

import hashlib
from typing import List, Tuple


class QualityRollbackGuard:
    def __init__(self):
        self.history_hashes: List[str] = []
        self.best_level: int = -1  # 0: L0, 1: L1, 2: L2, 3: L3
        self.best_code: str = ""
        self.best_round: int = 0

    @staticmethod
    def _hash(code: str) -> str:
        # Strip all whitespace to prevent trivial formatting oscillation
        normalized = "".join(code.split())
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def record_attempt(self, code: str, current_level: int, round_num: int) -> Tuple[bool, str]:
        """Record candidate code.

        Returns: (is_oscillating, status_message)
        """
        h = self._hash(code)
        if h in self.history_hashes:
            # The same source can legitimately pass L1, then L2.  Preserve the
            # higher milestone instead of mistaking that promotion for a loop.
            if current_level > self.best_level:
                self.best_level = current_level
                self.best_code = code
                self.best_round = round_num
            return True, "DUPLICATE_SOURCE: milestone updated without another repair."

        self.history_hashes.append(h)

        if current_level >= self.best_level:
            self.best_level = current_level
            self.best_code = code
            self.best_round = round_num

        return False, "PROGRESS_NORMAL"

    def get_best_deliverable(self, final_code: str, final_level: int) -> Tuple[str, int]:
        """Ensure we never return a regressed version if a later repair failed."""
        if final_level < self.best_level and self.best_code:
            return self.best_code, self.best_level
        return final_code or self.best_code, max(final_level, self.best_level)
