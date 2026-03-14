"""
AgentController
===============
Selects and executes the best tool for a task.
 
Single-step tasks
-----------------
  1. Score every registered tool (keyword matching + domain heuristics)
  2. Select the highest-scoring tool
  3. Execute; capture the internal step trace
  4. On error: activate the fallback chain (_fallback_tool always returns)
  5. Return a fully numbered AgentResponse
 
Multi-step / compound tasks
----------------------------
Tasks containing chaining connectors ("then", "and then", "followed by",
"after that") are handed to the MultiStepOrchestrator, which splits them,
executes each sub-task via run_single(), injects previous outputs where
referenced, and returns a merged trace.
 
  Example:
    "base64 encode 'hello world' then count the characters of the result"
    → Stage 1: Base64Tool   → 'aGVsbG8gd29ybGQ='
    → Stage 2: TextProcessor → '24 characters'
 
The controller exposes two public methods:
  run()        – entry point: dispatches to orchestrator or run_single()
  run_single() – always executes exactly one tool (used by the orchestrator)
"""
from __future__ import annotations
 
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
 
from tools.base import BaseTool, ToolResult
from tools.text_processor import TextProcessorTool
from tools.calculator import CalculatorTool
from tools.weather_mock import WeatherMockTool
from tools.base64_tool import Base64Tool
from tools.fallback_explainer import FallbackExplainerTool
from agent.orchestrator import MultiStepOrchestrator
 
 
# ---------------------------------------------------------------------------
# Response schema
# ---------------------------------------------------------------------------
 
@dataclass
class AgentResponse:
    task: str
    output: Any
    tools_used: list[str]
    steps: list[str]
    timestamp: str
    error: str | None = None
    # Populated only for multi-step tasks
    sub_results: list[dict] | None = None
 
 
# ---------------------------------------------------------------------------
# Controller
# ---------------------------------------------------------------------------
 
class AgentController:
 
    def __init__(self) -> None:
        self._fallback_explainer = FallbackExplainerTool()
        self._orchestrator = MultiStepOrchestrator()
 
        # Registration order determines tie-breaking priority.
        # FallbackExplainerTool is last — never scored, always available.
        self._tools: list[BaseTool] = [
            CalculatorTool(),
            WeatherMockTool(),
            Base64Tool(),
            TextProcessorTool(),
            self._fallback_explainer,
        ]
 
    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
 
    def run(self, task: str) -> AgentResponse:
        """
        Main entry point.  Detects compound tasks and delegates to the
        MultiStepOrchestrator; otherwise calls run_single().
        """
        timestamp = datetime.now(timezone.utc).isoformat()
 
        if self._orchestrator.is_multistep(task):
            orch = self._orchestrator.run(task, controller=self)
 
            sub_dicts = [
                {
                    "stage": sr.stage,
                    "task": sr.task,
                    "tool": sr.tool_name,
                    "output": sr.output,
                    "error": sr.error,
                }
                for sr in orch.sub_results
            ]
 
            return AgentResponse(
                task=task,
                output=orch.final_output,
                tools_used=orch.tools_used,
                steps=orch.all_steps,
                timestamp=timestamp,
                error=orch.error,
                sub_results=sub_dicts,
            )
 
        return self.run_single(task, timestamp=timestamp)
 
    def run_single(self, task: str, timestamp: str | None = None) -> AgentResponse:
        """
        Execute exactly one tool for the given task.
        Used directly for single-step tasks and internally by the orchestrator
        for each stage of a multi-step chain.
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc).isoformat()
 
        steps: list[str] = []
        steps.append(f'Step 1: Received task — "{task}"')
        steps.append("Step 2: Analysing task to select the best tool…")
 
        selected, confidence_note = self._select_tool(task)
 
        if selected is None:
            steps.append("Step 3: No matching tool found")
            steps.append("Step 4: Returning error to user")
            return AgentResponse(
                task=task,
                output=None,
                tools_used=[],
                steps=steps,
                timestamp=timestamp,
                error=(
                    "No suitable tool found. "
                    "Try: math ('3 + 5'), text ops ('uppercase \"hi\"'), "
                    "weather ('weather in London'), "
                    "or base64 ('encode \"hello\"')."
                ),
            )
 
        steps.append(f"Step 3: Selected tool — {selected.name} ({confidence_note})")
        steps.append(f"Step 4: Executing {selected.name}…")
 
        result: ToolResult = selected.execute(task)
 
        tool_step_offset = 5
        for i, ts in enumerate(result.steps, start=tool_step_offset):
            steps.append(f"Step {i}: {ts}")
        next_step = tool_step_offset + len(result.steps)
 
        if result.error:
            steps.append(
                f"Step {next_step}: Tool returned an error — {result.error}"
            )
            next_step += 1
 
            fallback = self._fallback_tool(task, exclude=selected, error=result.error)
            steps.append(
                f"Step {next_step}: Activating fallback — {fallback.name}"
            )
            next_step += 1
 
            fallback_result = fallback.execute(task)
            for i, ts in enumerate(fallback_result.steps, start=next_step):
                steps.append(f"Step {i}: {ts}")
            next_step += len(fallback_result.steps)
 
            tools_used = [selected.name, fallback.name]
 
            if fallback_result.error:
                steps.append(
                    f"Step {next_step}: Fallback also failed — {fallback_result.error}"
                )
                steps.append(f"Step {next_step + 1}: Returning combined error to user")
                return AgentResponse(
                    task=task,
                    output=None,
                    tools_used=tools_used,
                    steps=steps,
                    timestamp=timestamp,
                    error=(
                        f"{result.error} | "
                        f"Fallback also failed: {fallback_result.error}"
                    ),
                )
 
            steps.append(f"Step {next_step}: Returning fallback result to user")
            return AgentResponse(
                task=task,
                output=fallback_result.output,
                tools_used=tools_used,
                steps=steps,
                timestamp=timestamp,
            )
 
        tools_used = [selected.name]
        steps.append(f"Step {next_step}: Returning result to user")
        return AgentResponse(
            task=task,
            output=result.output,
            tools_used=tools_used,
            steps=steps,
            timestamp=timestamp,
        )
 
    # ------------------------------------------------------------------
    # Tool selection
    # ------------------------------------------------------------------
 
    def _select_tool(self, task: str) -> tuple[BaseTool | None, str]:
        scores: dict[str, tuple[BaseTool, int, str]] = {}
        for tool in self._tools:
            if isinstance(tool, FallbackExplainerTool):
                continue
            score, note = self._score_tool(tool, task)
            if score > 0:
                scores[tool.name] = (tool, score, note)
 
        if not scores:
            return None, "no tool matched"
 
        best_name = max(scores, key=lambda n: scores[n][1])
        best_tool, _, note = scores[best_name]
        return best_tool, note
 
    def _score_tool(self, tool: BaseTool, task: str) -> tuple[int, str]:
        # Strip quoted payload before scoring so that injected data from a
        # previous step (e.g. a full weather report embedded as a quoted
        # string) cannot skew tool selection with stray numbers or keywords.
        # Scoring is done on the COMMAND portion only; the tool still receives
        # the full task string (including the quoted target) for execution.
        command_only = re.sub(r'["\'].*?["\']|"[^"]*"\Z', '', task,
                              flags=re.DOTALL).strip()
        lowered_cmd = command_only.lower()
        # Keep the full string for can_handle (keyword list needs the target too)
        lowered = task.lower()
        score = 0
        note = ""
 
        if tool.can_handle(task):
            score += 10
            note = "keyword match"
 
        if isinstance(tool, CalculatorTool):
            # Only boost on the command portion — avoids "24°C / 75.2°F" in
            # an injected weather report triggering the numeric-op pattern.
            if re.search(r'\d+\s*[\+\-\*\/\%\^]\s*\d+', command_only):
                score += 20
                note = "numeric expression detected"
            if re.search(r'\b(sqrt|square root|calculate|compute|what is \d)', lowered_cmd):
                score += 15
                note = "math keyword + operator"
 
        if isinstance(tool, WeatherMockTool):
            # Only boost on the command portion — avoids "Weather in Tokyo"
            # inside an injected report re-triggering the weather scorer.
            if re.search(r'\bweather\b|\bforecast\b|\btemperature\b', lowered_cmd):
                score += 20
                note = "strong weather keyword"
 
        if isinstance(tool, Base64Tool):
            if re.search(r'\bbase64\b|\bb64\b', lowered_cmd):
                score += 25
                note = "explicit base64 keyword"
            elif re.search(r'\bencode\b|\bdecode\b', lowered_cmd):
                score += 10
                note = "encode/decode keyword"
 
        if isinstance(tool, TextProcessorTool):
            text_ops = [
                "uppercase", "lowercase", "word count", "reverse",
                "palindrome", "capitalize", "title case",
                "camelcase", "snake_case", "char count", "character count",
                "characters", "count the char",
            ]
            if any(op in lowered_cmd for op in text_ops):
                score += 15
                note = "text operation keyword"
 
        return score, note
 
    def _fallback_tool(self, task: str, exclude: BaseTool, error: str) -> BaseTool:
        for tool in self._tools:
            if tool is exclude:
                continue
            if isinstance(tool, FallbackExplainerTool):
                continue
            if tool.can_handle(task):
                return tool
        self._fallback_explainer.prepare(error)
        return self._fallback_explainer
 
    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------
 
    def list_tools(self) -> list[dict]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "keywords": t.keywords,
            }
            for t in self._tools
        ]
 