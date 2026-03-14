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
 
# Named-field references — "the condition", "the temperature", "the humidity" etc.
# Matches "the <word>" where <word> is not one of the generic result pronouns.
_FIELD_REF_RE = re.compile(
    r"\bthe\s+(?!result\b|output\b|answer\b)([a-zA-Z_]\w*)\b",
    re.IGNORECASE,
)
 
 
# Transformation keywords — verbs that operate ON an input and need an operand.
# Mode 4 injection only fires when one of these is present in the sub-task.
# Sub-tasks that contain NONE of these are treated as self-contained queries
# (e.g. "weather in Paris", "calculate 3 + 5") and are left unchanged.
_TRANSFORMATION_KEYWORDS = [
    "reverse", "uppercase", "upper case", "upper",
    "lowercase", "lower case", "lower",
    "title case", "capitalize",
    "word count", "character count", "char count",
    "count",        # "count the characters"
    "palindrome", "trim", "strip",
    "snake_case", "camelcase", "camel case",
    "encode", "decode",
    "validate", "inspect",
]
 
 
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
            self._last_field_injection = None   # reset before each stage
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
 
            # If a field injection occurred this stage, reconstruct the full
            # structured output with the field value replaced by the tool result.
            # e.g. weather report with "Condition: Clear" → "Condition: CLEAR"
            # This means the next stage (or final output) sees the complete
            # report rather than just the isolated field value.
            if (
                self._last_field_injection is not None
                and agent_resp.output is not None
                and agent_resp.error is None
            ):
                ctx = self._last_field_injection
                reconstructed = self._replace_field_in_output(
                    text=ctx["full_prev_output"],
                    field_name=ctx["field_name"],
                    new_value=str(agent_resp.output),
                )
                # Patch sub_result output to be the full reconstructed report
                sub_results[-1] = SubTaskResult(
                    stage=sub_results[-1].stage,
                    task=sub_results[-1].task,
                    original_task=sub_results[-1].original_task,
                    tool_name=sub_results[-1].tool_name,
                    output=reconstructed,
                    steps=sub_results[-1].steps,
                    error=sub_results[-1].error,
                )
                agent_resp_output = reconstructed
                all_steps.append(
                    f"Step {step_counter}: "
                    f"[STAGE {stage_idx}] Patched field \"{ctx['field_name']}\" "
                    f"in full report → returning complete output"
                )
                step_counter += 1
            else:
                agent_resp_output = str(agent_resp.output) if agent_resp.output is not None else ""
 
            # Use this output as potential input to next step
            prev_output = agent_resp_output
 
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
        Thread the previous step's output into the next sub-task.
 
        Four injection modes (checked in priority order):
 
        1. Already has a quoted target  →  leave unchanged
           e.g. "reverse 'foo'"  — the user supplied an explicit target
 
        2. Named-field reference  →  extract just that field from structured output
           e.g. "uppercase the condition" with a weather report as prev_output
           → finds "Condition: Clear" in the report → injects "Clear" only
           This prevents the entire multi-line blob from being passed downstream,
           which would poison the tool scorer with stray numbers and keywords.
 
        3. Generic result pronoun  →  replace the pronoun with the full output
           e.g. "reverse the result"  →  "reverse \"<prev>\""
           Recognised pronouns: the result, the output, the answer, it, that, {result}
 
        4. Bare imperative with no target and no pronoun  →  append full output
           e.g. "count the characters"  →  "count the characters \"<prev>\""
           Implicit-chaining fallback.
        """
        if prev_output is None:
            return sub_task
 
        # Mode 1 — explicit quoted target already present
        if re.search(r'["\']', sub_task):
            return sub_task
 
        # Mode 2 — named field reference ("the condition", "the temperature", ...)
        field_match = _FIELD_REF_RE.search(sub_task)
        if field_match:
            field_name = field_match.group(1)          # e.g. "condition"
            extracted = self._extract_field(prev_output, field_name)
            if extracted is not None:
                # Store field context so run() can patch the full output later
                self._last_field_injection = {
                    "field_name": field_name,
                    "extracted_value": extracted,
                    "full_prev_output": prev_output,
                }
                # Replace "the <field>" with the extracted value
                return _FIELD_REF_RE.sub(f'"{extracted}"', sub_task, count=1)
            # Field not found in prev_output — fall through to Mode 3/4
 
        # Mode 3 — generic back-reference pronoun
        if _RESULT_REF_RE.search(sub_task):
            return _RESULT_REF_RE.sub(f'"{prev_output}"', sub_task)
 
        # Mode 4 — bare imperative fallback.
        #
        # Math continuation is checked FIRST — before the _needs_operand guard —
        # because math ops like "add 4", "+ 10", "subtract 2" are not in
        # _TRANSFORMATION_KEYWORDS but still need to fire when prev_output is
        # a plain number.  _build_math_continuation returns None for anything
        # that is not a numeric math follow-up, so it is safe to check early.
        if prev_output is not None:
            math_expr = self._build_math_continuation(sub_task, prev_output)
            if math_expr is not None:
                return math_expr
 
        # _needs_operand guard — only append the previous output when the
        # sub-task is a transformation command that genuinely needs an operand
        # (e.g. "reverse", "count the characters", "uppercase").
        # Self-contained queries ("weather in Paris", "calculate 6 * 7") are
        # left unchanged — they already carry their own subject.
        if not self._needs_operand(sub_task):
            return sub_task
 
        return f'{sub_task} "{prev_output}"' 
 
    def _needs_operand(self, sub_task: str) -> bool:
        """
        Return True if sub_task is a transformation command that requires an
        operand from the previous step, False if it is self-contained.
 
        Transformation commands (need an operand):
            "reverse", "uppercase", "count the characters", "encode", etc.
 
        Self-contained queries (do NOT need an operand):
            "weather in Paris"   — already has a location
            "calculate 6 * 7"   — already has a full expression
            "base64 encode 'x'" — Mode 1 catches it (has quotes) but also
                                   self-contained without quotes
        """
        lowered = sub_task.lower()
        return any(kw in lowered for kw in _TRANSFORMATION_KEYWORDS)
 
    def _build_math_continuation(
        self, sub_task: str, prev_output: str
    ) -> str | None:
        """
        If sub_task is a follow-up arithmetic operation and prev_output is a
        plain number, return a proper inline expression that CalculatorTool
        can evaluate directly.
 
        Examples
        --------
        sub_task="add 4",        prev_output="24"  →  "24 + 4"
        sub_task="subtract 2",   prev_output="42"  →  "42 - 2"
        sub_task="multiply by 3",prev_output="10"  →  "10 * 3"
        sub_task="divide by 2",  prev_output="100" →  "100 / 2"
        sub_task="+ 10",         prev_output="24"  →  "24 + 10"
        sub_task="* 5",          prev_output="7"   →  "7 * 5"
 
        Returns None if prev_output is not a plain number or sub_task does not
        look like a math continuation — caller falls through to Mode 4.
        """
        # prev_output must be a bare number (int or float, no letters/symbols)
        prev_stripped = prev_output.strip()
        try:
            float(prev_stripped)
        except ValueError:
            return None          # not a number — cannot build math expression
 
        lowered = sub_task.lower().strip()
 
        # Map natural-language / symbol prefixes to their operator symbols
        MATH_PATTERNS: list[tuple[str, str]] = [
            # word-based operators  (order: longer phrases first)
            (r'^add(?:ed)?\s+',                  '+ '),
            (r'^plus\s+',                        '+ '),
            (r'^subtract(?:ed)?\s+(?:from\s+)?', '- '),
            (r'^minus\s+',                       '- '),
            (r'^multiply(?:ied)?\s+(?:by\s+)?',  '* '),
            (r'^times\s+',                       '* '),
            (r'^divide(?:d)?\s+(?:by\s+)?',      '/ '),
            (r'^divided\s+by\s+',                '/ '),
            (r'^mod(?:ulo)?\s+',                 '% '),
            (r'^to\s+the\s+power\s+of\s+',       '** '),
            # symbol-based operators
            (r'^\+\s*',  '+ '),
            (r'^-\s*',   '- '),
            (r'^\*\s*',  '* '),
            (r'^/\s*',   '/ '),
            (r'^%\s*',   '% '),
        ]
 
        for pattern, op_symbol in MATH_PATTERNS:
            m = re.match(pattern, lowered)
            if m:
                remainder = sub_task[m.end():].strip()
                if remainder:                   # there must be an operand
                    return f"{prev_stripped} {op_symbol}{remainder}"
 
        return None                             # no math pattern matched
 
    def _extract_field(self, text: str, field_name: str) -> str | None:
        """
        Look for a "Key: Value" line in structured text where Key matches
        field_name (case-insensitive).  Returns the value string, or None
        if no matching line is found.
 
        Example:
            text      = "Condition: Clear\nTemperature: 24°C"
            field_name = "condition"
            returns   → "Clear"
        """
        for line in text.splitlines():
            m = re.match(r'^([\w\s]+?):\s*(.+)$', line.strip())
            if m:
                key = m.group(1).strip().lower()
                if key == field_name.lower():
                    # Strip leading emoji/whitespace from the value
                    return re.sub(r'^[^\w]+', '', m.group(2)).strip()
        return None
 
    def _replace_field_in_output(
        self, text: str, field_name: str, new_value: str
    ) -> str:
        """
        Replace the value of a named field in structured "Key: Value" text.
 
        Example:
            text       = "Condition: Clear\nTemperature: 24C"
            field_name = "condition"
            new_value  = "CLEAR"
            returns    = "Condition: CLEAR\nTemperature: 24C"
 
        Lines that do not match the field are left unchanged.
        The emoji prefix on the first line is preserved.
        """
        lines = text.splitlines()
        result_lines = []
        for line in lines:
            m = re.match(r'^([\w\s]+?):\s*(.+)$', line.strip())
            if m and m.group(1).strip().lower() == field_name.lower():
                # Rebuild the line with the new value, preserving the key
                result_lines.append(f"{m.group(1)}: {new_value}")
            else:
                result_lines.append(line)
        return "\n".join(result_lines)
 
    def _summarise(self, sub_results: list[SubTaskResult]) -> str:
        """Build a multi-stage summary for partial or completed chains."""
        lines = []
        for sr in sub_results:
            status = "✓" if not sr.error else "✗"
            out = sr.output if sr.output is not None else f"ERROR: {sr.error}"
            lines.append(f"Stage {sr.stage} [{sr.tool_name}] {status}  →  {out}")
        return "\n".join(lines)