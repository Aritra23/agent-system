"""
MultiStepOrchestrator
=====================
Detects compound tasks, splits them into ordered sub-tasks, executes each
with the most appropriate tool, and optionally threads the output of one
step as the input of the next.

What counts as multi-step?
---------------------------
A task is treated as multi-step when it contains a chaining connector that
clearly separates two distinct operations. Recognised connectors:

  "then"          – "encode 'hello' then count the characters"
  "and then"      – "calculate 6*7 and then reverse the result"
  "followed by"   – "uppercase 'foo' followed by reverse the result"
  "after that"    – "decode 'aGVsbG8=' after that count the words"
  ", then"        – "get weather in Tokyo, then uppercase the condition"

Output injection
----------------
When the second (or later) sub-task contains a reference to the previous
step's output ("the result", "it", "that", "the output", "{result}"),
the orchestrator substitutes the actual previous output into the instruction
before passing it to the tool.  This enables genuine chaining:

  "base64 encode 'hello' then reverse the result"
  → encodes 'hello' → 'aGVsbG8='
  → reverses 'aGVsbG8=' → '=8olGVsGA'

Trace format
------------
Each sub-task produces its own numbered trace.  The orchestrator merges all
sub-traces into a single flat Step N list with clear STAGE headings, so the
frontend TraceViewer renders the full chain in one view.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from agent.controller import AgentController

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Patterns that split a compound task into sub-tasks.
# Ordered from most specific to least specific to avoid over-splitting.
_SPLIT_PATTERNS = [
    r'\s*,\s*and\s+then\s+',
    r'\s+and\s+then\s+',
    r'\s*,\s*then\s+',
    r'\s+then\s+',
    r'\s+followed\s+by\s+',
    r'\s+after\s+that\s+',
    r'\s+next\s+',
]
_SPLIT_RE = re.compile(
    "(" + "|".join(_SPLIT_PATTERNS) + ")",
    re.IGNORECASE,
)

# References to the previous step's output that trigger injection.
_RESULT_REFS = [
    r'\bthe\s+result\b',
    r'\bthe\s+output\b',
    r'\bthe\s+answer\b',
    r'\bit\b',
    r'\bthat\b',
    r'\{result\}',
]
_RESULT_REF_RE = re.compile(
    "(" + "|".join(_RESULT_REFS) + ")",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class SubTaskResult:
    stage: int
    task: str               # original sub-task text (possibly with injection)
    original_task: str      # text before injection
    tool_name: str
    output: Any
    steps: list[str] = field(default_factory=list)
    error: str | None = None


@dataclass
class OrchestrationResult:
    original_task: str
    sub_results: list[SubTaskResult]
    final_output: Any
    all_steps: list[str]            # merged, renumbered trace
    tools_used: list[str]           # deduplicated, in order of first use
    error: str | None = None


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class MultiStepOrchestrator:
    """
    Detects compound tasks and chains tool executions.

    Usage
    -----
    The AgentController instantiates this once and delegates to it:

        if self._orchestrator.is_multistep(task):
            result = self._orchestrator.run(task, controller=self)
    """

    # ------------------------------------------------------------------
    # Detection
    # ------------------------------------------------------------------

    def is_multistep(self, task: str) -> bool:
        """Return True if the task contains at least one chaining connector."""
        parts = self._split(task)
        return len(parts) >= 2

    # ------------------------------------------------------------------
    # Main entry
    # ------------------------------------------------------------------

    def run(
        self,
        task: str,
        controller: "AgentController",
    ) -> OrchestrationResult:
        """
        Split the task, execute each sub-task via the controller's single-tool
        logic, inject outputs where referenced, and return a merged result.
        """
        sub_tasks = self._split(task)
        sub_results: list[SubTaskResult] = []
        all_steps: list[str] = []
        tools_used_ordered: list[str] = []
        seen_tools: set[str] = set()

        step_counter = 1

        all_steps.append(
            f"Step {step_counter}: Received compound task — \"{task}\""
        )
        step_counter += 1
        all_steps.append(
            f"Step {step_counter}: Detected {len(sub_tasks)} sub-tasks "
            f"— orchestrating sequential execution"
        )
        step_counter += 1
        for i, st in enumerate(sub_tasks, start=1):
            all_steps.append(f"Step {step_counter}: Sub-task {i} → \"{st}\"")
            step_counter += 1

        prev_output: str | None = None

        for stage_idx, raw_sub_task in enumerate(sub_tasks, start=1):
            # ── Inject previous output if referenced ──────────────────
            injected_task = self._inject_output(raw_sub_task, prev_output)
            if injected_task != raw_sub_task:
                all_steps.append(
                    f"Step {step_counter}: "
                    f"[STAGE {stage_idx}] Injecting previous output into sub-task "
                    f"→ \"{injected_task}\""
                )
                step_counter += 1

            all_steps.append(
                f"Step {step_counter}: "
                f"[STAGE {stage_idx}] Executing: \"{injected_task}\""
            )
            step_counter += 1

            # ── Execute via controller's single-tool run ───────────────
            agent_resp = controller.run_single(injected_task)

            # ── Merge sub-trace ───────────────────────────────────────
            for sub_step in agent_resp.steps:
                # Re-number sub-steps, preserving their content after "Step N:"
                content = re.sub(r'^Step \d+:\s*', '', sub_step)
                all_steps.append(f"Step {step_counter}: [STAGE {stage_idx}] {content}")
                step_counter += 1

            # ── Record result ──────────────────────────────────────────
            sub_result = SubTaskResult(
                stage=stage_idx,
                task=injected_task,
                original_task=raw_sub_task,
                tool_name=agent_resp.tools_used[0] if agent_resp.tools_used else "unknown",
                output=agent_resp.output,
                steps=agent_resp.steps,
                error=agent_resp.error,
            )
            sub_results.append(sub_result)

            # Track tools used (deduplicated, insertion order)
            for t in agent_resp.tools_used:
                if t not in seen_tools:
                    tools_used_ordered.append(t)
                    seen_tools.add(t)

            if agent_resp.error:
                # Stop chain on first hard error
                all_steps.append(
                    f"Step {step_counter}: "
                    f"[STAGE {stage_idx}] Sub-task failed — stopping chain. "
                    f"Error: {agent_resp.error}"
                )
                step_counter += 1
                all_steps.append(
                    f"Step {step_counter}: Returning partial results to user"
                )
                return OrchestrationResult(
                    original_task=task,
                    sub_results=sub_results,
                    final_output=self._summarise(sub_results),
                    all_steps=all_steps,
                    tools_used=tools_used_ordered,
                    error=f"Chain stopped at stage {stage_idx}: {agent_resp.error}",
                )

            # Use this output as potential input to next step
            prev_output = str(agent_resp.output) if agent_resp.output is not None else ""

            all_steps.append(
                f"Step {step_counter}: "
                f"[STAGE {stage_idx}] Completed — output: \"{prev_output[:80]}"
                f"{'…' if len(prev_output) > 80 else ''}\""
            )
            step_counter += 1

        # ── All stages completed ──────────────────────────────────────
        final = sub_results[-1].output if sub_results else None
        all_steps.append(
            f"Step {step_counter}: All {len(sub_tasks)} stages completed — "
            f"returning final result to user"
        )

        return OrchestrationResult(
            original_task=task,
            sub_results=sub_results,
            final_output=final,
            all_steps=all_steps,
            tools_used=tools_used_ordered,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _split(self, task: str) -> list[str]:
        """Split a compound task on chaining connectors."""
        parts = _SPLIT_RE.split(task)
        # _SPLIT_RE uses a capturing group — odd-index items are the delimiters
        sub_tasks = [p.strip() for i, p in enumerate(parts) if i % 2 == 0]
        return [s for s in sub_tasks if s]

    def _inject_output(self, sub_task: str, prev_output: str | None) -> str:
        """
        Replace references like 'the result', 'it', '{result}' with the
        actual previous output — but only when the sub-task doesn't already
        contain a quoted target string (which would be unambiguous).
        """
        if prev_output is None:
            return sub_task
        if re.search(r'["\']', sub_task):
            # Already has a quoted target — leave it alone
            return sub_task
        if _RESULT_REF_RE.search(sub_task):
            return _RESULT_REF_RE.sub(f'"{prev_output}"', sub_task)
        return sub_task

    def _summarise(self, sub_results: list[SubTaskResult]) -> str:
        """Build a multi-stage summary for partial or completed chains."""
        lines = []
        for sr in sub_results:
            status = "✓" if not sr.error else "✗"
            out = sr.output if sr.output is not None else f"ERROR: {sr.error}"
            lines.append(f"Stage {sr.stage} [{sr.tool_name}] {status}  →  {out}")
        return "\n".join(lines)
