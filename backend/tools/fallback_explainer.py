import re
from .base import BaseTool, ToolResult
 
 
class FallbackExplainerTool(BaseTool):
    """
    Last-resort fallback tool. Never selected by the scoring system (empty
    keywords, zero score), but always available when a higher-priority tool
    fails. Analyses the original task + error context and returns a clear,
    actionable explanation of what went wrong.
    """
 
    def __init__(self) -> None:
        self._error_context: str | None = None
 
    def prepare(self, error: str) -> None:
        """Called by AgentController before execute() to inject failure context."""
        self._error_context = error
 
    # ------------------------------------------------------------------
    # BaseTool interface
    # ------------------------------------------------------------------
 
    @property
    def name(self) -> str:
        return "FallbackExplainerTool"
 
    @property
    def description(self) -> str:
        return "Activated when all other tools fail — explains what went wrong and suggests alternatives"
 
    @property
    def keywords(self) -> list[str]:
        # Empty on purpose: this tool is never selected by keyword scoring.
        # It is only injected by _fallback_tool() as a guaranteed last resort.
        return []
 
    def can_handle(self, input_text: str) -> bool:
        # Always true — this tool can respond to any failed task.
        return True
 
    def execute(self, input_text: str) -> ToolResult:
        steps = [f'Received input: "{input_text}"']
        steps.append("Selected tool: FallbackExplainerTool (activated as fallback)")
 
        error = self._error_context or "An unknown error occurred."
        steps.append(f"Injected error context: {error}")
 
        # Classify the failure and build a tailored explanation
        explanation = self._build_explanation(input_text, error)
        steps.append("Classified failure type and built explanation")
        steps.append("Returning explanation to user")
 
        return ToolResult(output=explanation, steps=steps)
 
    # ------------------------------------------------------------------
    # Explanation builder
    # ------------------------------------------------------------------
 
    def _build_explanation(self, task: str, error: str) -> str:
        lowered_error = error.lower()
        lowered_task = task.lower()
 
        # ── Division by zero ──────────────────────────────────────────
        if "zero" in lowered_error or "division" in lowered_error:
            return (
                f"⚠ Could not complete: {error}\n\n"
                f"What you asked: \"{task}\"\n"
                f"Why it failed: Division by zero is mathematically undefined — "
                f"no finite number exists as the result.\n\n"
                f"💡 Suggestions:\n"
                f"  • Replace the zero divisor with a non-zero number\n"
                f"  • Examples: 10 / 2, 100 / 4, 7 / 3\n"
                f"  • To check divisibility try: 10 % 3 (remainder operation)"
            )
 
        # ── Math domain error (e.g. sqrt of negative) ─────────────────
        if "domain" in lowered_error or "sqrt" in lowered_task or "square root" in lowered_task:
            neg_match = re.search(r'sqrt\s*\(?\s*-\s*(\d+)', lowered_task)
            num = neg_match.group(1) if neg_match else "a negative number"
            return (
                f"⚠ Could not complete: {error}\n\n"
                f"What you asked: \"{task}\"\n"
                f"Why it failed: The square root of a negative number is not a "
                f"real number. √(-{num}) = {num}i (imaginary), which this calculator "
                f"does not support.\n\n"
                f"💡 Suggestions:\n"
                f"  • Use a non-negative number: sqrt(4), sqrt(25), sqrt(144)\n"
                f"  • To find the result magnitude, use the absolute value first: sqrt({num})"
            )
 
        # ── Could not parse expression ─────────────────────────────────
        if "parse" in lowered_error or "expression" in lowered_error:
            return (
                f"⚠ Could not complete: {error}\n\n"
                f"What you asked: \"{task}\"\n"
                f"Why it failed: The calculator could not read a valid arithmetic "
                f"expression from your input.\n\n"
                f"💡 Suggestions:\n"
                f"  • Use standard operators: +  -  *  /  **  %\n"
                f"  • Examples: \"3 + 5\", \"(10 - 2) * 4\", \"2 ** 8\", \"sqrt(16)\"\n"
                f"  • Natural language also works: \"5 plus 3\", \"10 divided by 2\""
            )
 
        # ── Weather: no city found ─────────────────────────────────────
        if "city" in lowered_error or "weather" in lowered_task or "forecast" in lowered_task:
            return (
                f"⚠ Could not complete: {error}\n\n"
                f"What you asked: \"{task}\"\n"
                f"Why it failed: The weather tool needs a city name to look up conditions.\n\n"
                f"💡 Suggestions:\n"
                f"  • Include a city: \"weather in London\", \"forecast for Tokyo\"\n"
                f"  • Or ask for temperature: \"temperature in Paris\"\n"
                f"  • Supported cities include: London, New York, Tokyo, Sydney, Paris,\n"
                f"    Berlin, Dubai, Moscow, Toronto, Singapore, Los Angeles, and more"
            )
 
        # ── Unsupported text operation ─────────────────────────────────
        if "unsupported" in lowered_error or "operation" in lowered_error:
            return (
                f"⚠ Could not complete: {error}\n\n"
                f"What you asked: \"{task}\"\n"
                f"Why it failed: The text processor does not recognise that operation.\n\n"
                f"💡 Supported text operations:\n"
                f"  • uppercase \"text\"         → UPPERCASE\n"
                f"  • lowercase \"TEXT\"         → lowercase\n"
                f"  • title case \"text here\"   → Title Case\n"
                f"  • reverse \"hello\"          → olleh\n"
                f"  • word count of \"...\"      → N words\n"
                f"  • palindrome check \"...\"   → is/is not a palindrome\n"
                f"  • snake_case \"my text\"     → my_text\n"
                f"  • camelCase \"my text\"      → myText"
            )
 
        # ── Generic fallback ───────────────────────────────────────────
        return (
            f"⚠ Could not complete your task.\n\n"
            f"What you asked: \"{task}\"\n"
            f"Error details: {error}\n\n"
            f"💡 This agent supports three types of tasks:\n"
            f"  • Math:    \"3 + 5\", \"sqrt(16)\", \"(10 - 2) * 4\"\n"
            f"  • Text:    \"uppercase 'hello'\", \"word count of '...'\"\n"
            f"  • Weather: \"weather in London\", \"forecast for Tokyo\""
        )
 