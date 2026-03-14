"""
Full test suite: tools, agent controller, fallback logic,
Base64Tool, and MultiStepOrchestrator.
 
Run: cd backend && python -m pytest tests/ -v
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
 
import pytest
from tools.text_processor import TextProcessorTool
from tools.calculator import CalculatorTool
from tools.weather_mock import WeatherMockTool
from tools.base64_tool import Base64Tool
from tools.fallback_explainer import FallbackExplainerTool
from agent.controller import AgentController
from agent.orchestrator import MultiStepOrchestrator
 
 
# ===========================================================================
# TextProcessorTool
# ===========================================================================
class TestTextProcessorTool:
    def setup_method(self): self.tool = TextProcessorTool()
 
    def test_uppercase(self):
        assert self.tool.execute("uppercase 'hello world'").output == "HELLO WORLD"
 
    def test_lowercase(self):
        assert self.tool.execute("lowercase 'HELLO WORLD'").output == "hello world"
 
    def test_title_case(self):
        assert self.tool.execute("title case 'the quick brown fox'").output == "The Quick Brown Fox"
 
    def test_reverse(self):
        assert self.tool.execute("reverse 'hello'").output == "olleh"
 
    def test_word_count(self):
        assert "4 words" in self.tool.execute("word count of 'the quick brown fox'").output
 
    def test_palindrome_true(self):
        assert "palindrome ✓" in self.tool.execute("palindrome check 'racecar'").output
 
    def test_palindrome_false(self):
        assert "not a palindrome" in self.tool.execute("palindrome check 'hello'").output
 
    def test_steps_populated(self):
        assert len(self.tool.execute("uppercase 'test'").steps) >= 3
 
    def test_can_handle_positive(self):
        assert self.tool.can_handle("uppercase this text")
 
    def test_can_handle_negative(self):
        assert not self.tool.can_handle("what is 3 + 5")
 
 
# ===========================================================================
# CalculatorTool
# ===========================================================================
class TestCalculatorTool:
    def setup_method(self): self.tool = CalculatorTool()
 
    def test_addition(self):        assert self.tool.execute("3 + 5").output == "8"
    def test_subtraction(self):     assert self.tool.execute("10 - 4").output == "6"
    def test_multiplication(self):  assert self.tool.execute("6 * 7").output == "42"
    def test_division(self):        assert self.tool.execute("10 / 4").output == "2.5"
    def test_power(self):           assert self.tool.execute("2 ** 8").output == "256"
    def test_sqrt(self):            assert self.tool.execute("sqrt(16)").output == "4"
    def test_sqrt_natural(self):    assert self.tool.execute("square root of 25").output == "5"
    def test_word_ops(self):        assert self.tool.execute("5 plus 3").output == "8"
    def test_complex_expr(self):    assert self.tool.execute("(3 + 5) * 2").output == "16"
 
    def test_division_by_zero(self):
        r = self.tool.execute("10 / 0")
        assert r.output is None and r.error and "zero" in r.error.lower()
 
    def test_can_handle_positive(self):
        assert self.tool.can_handle("calculate 3 + 5")
 
    def test_can_handle_negative(self):
        assert not self.tool.can_handle("weather in London")
 
 
# ===========================================================================
# WeatherMockTool
# ===========================================================================
class TestWeatherMockTool:
    def setup_method(self): self.tool = WeatherMockTool()
 
    def test_known_city(self):
        r = self.tool.execute("weather in London")
        assert r.error is None and "London" in r.output and "°C" in r.output
 
    def test_unknown_city_fallback(self):
        r = self.tool.execute("weather in Atlantis")
        assert r.output is not None and r.error is None
 
    def test_has_humidity(self):    assert "Humidity" in self.tool.execute("weather in Tokyo").output
    def test_has_wind(self):        assert "Wind"     in self.tool.execute("weather in Paris").output
    def test_has_fahrenheit(self):  assert "°F"       in self.tool.execute("temperature in Sydney").output
 
    def test_no_city_error(self):
        r = self.tool.execute("weather")
        assert r.error and ("city" in r.error.lower())
 
    def test_bare_forecast_error(self):
        assert self.tool.execute("forecast").error is not None
 
    def test_can_handle_positive(self):
        assert self.tool.can_handle("weather in Berlin")
 
    def test_can_handle_negative(self):
        assert not self.tool.can_handle("3 + 5")
 
 
# ===========================================================================
# Base64Tool
# ===========================================================================
class TestBase64Tool:
    def setup_method(self): self.tool = Base64Tool()
 
    # ── Encode ──────────────────────────────────────────────────────────────
    def test_encode_hello_world(self):
        r = self.tool.execute("base64 encode 'hello world'")
        assert r.error is None
        assert r.output == "aGVsbG8gd29ybGQ="
 
    def test_encode_empty_string(self):
        r = self.tool.execute("encode ''")
        assert r.error is None
        assert r.output == ""
 
    def test_encode_special_chars(self):
        r = self.tool.execute("base64 encode 'user@example.com'")
        assert r.error is None
        assert r.output == "dXNlckBleGFtcGxlLmNvbQ=="
 
    def test_encode_numbers(self):
        r = self.tool.execute("base64 encode '12345'")
        assert r.error is None
        assert r.output == "MTIzNDU="
 
    # ── Decode ──────────────────────────────────────────────────────────────
    def test_decode_hello_world(self):
        r = self.tool.execute("base64 decode 'aGVsbG8gd29ybGQ='")
        assert r.error is None
        assert r.output == "hello world"
 
    def test_decode_without_padding(self):
        # aGVsbG8= without the trailing =
        r = self.tool.execute("decode 'aGVsbG8'")
        assert r.error is None
        assert r.output == "hello"
 
    def test_decode_invalid_raises_error(self):
        r = self.tool.execute("base64 decode 'this is not base64!!!'")
        assert r.output is None
        assert r.error is not None
 
    def test_decode_reverses_encode(self):
        import base64
        original = "the quick brown fox"
        encoded = base64.b64encode(original.encode()).decode()
        r = self.tool.execute(f"decode '{encoded}'")
        assert r.error is None
        assert r.output == original
 
    # ── URL-safe ─────────────────────────────────────────────────────────────
    def test_url_safe_encode(self):
        r = self.tool.execute("url-safe base64 encode 'hello+world/test'")
        assert r.error is None
        assert "+" not in r.output and "/" not in r.output
 
    def test_url_safe_decode(self):
        import base64
        enc = base64.urlsafe_b64encode(b"hello world").decode()
        r = self.tool.execute(f"url-safe base64 decode '{enc}'")
        assert r.error is None
        assert r.output == "hello world"
 
    # ── Validate ─────────────────────────────────────────────────────────────
    def test_validate_valid_string(self):
        r = self.tool.execute("validate 'aGVsbG8='")
        assert r.error is None
        assert "✓" in r.output
 
    def test_validate_invalid_string(self):
        r = self.tool.execute("validate 'not valid base64 !!!'")
        assert r.error is None
        assert "✗" in r.output
 
    # ── Info ──────────────────────────────────────────────────────────────────
    def test_info_returns_metadata(self):
        r = self.tool.execute("base64 info 'aGVsbG8gd29ybGQ='")
        assert r.error is None
        assert "Decoded bytes" in r.output
        assert "Encoded length" in r.output
 
    def test_info_invalid_string_errors(self):
        r = self.tool.execute("base64 info 'not!!valid'")
        assert r.output is None
        assert r.error is not None
 
    # ── Auto-detect ───────────────────────────────────────────────────────────
    def test_auto_detect_decodes_valid_b64(self):
        # aGVsbG8= is "hello" in base64; auto mode should decode it
        r = self.tool.execute("base64 'aGVsbG8='")
        assert r.error is None
        assert r.output == "hello"
 
    def test_auto_detect_encodes_plaintext(self):
        r = self.tool.execute("base64 'hello world'")
        assert r.error is None
        assert r.output == "aGVsbG8gd29ybGQ="
 
    # ── Steps trace ───────────────────────────────────────────────────────────
    def test_steps_populated(self):
        r = self.tool.execute("base64 encode 'test'")
        assert len(r.steps) >= 3
 
    def test_steps_include_operation(self):
        r = self.tool.execute("base64 encode 'test'")
        combined = " ".join(r.steps).lower()
        assert "encode" in combined
 
    # ── can_handle ────────────────────────────────────────────────────────────
    def test_can_handle_base64(self):
        assert self.tool.can_handle("base64 encode this")
        assert self.tool.can_handle("decode 'aGVsbG8='")
        assert self.tool.can_handle("b64 encode hello")
 
    def test_cannot_handle_weather(self):
        assert not self.tool.can_handle("weather in London")
 
 
# ===========================================================================
# FallbackExplainerTool
# ===========================================================================
class TestFallbackExplainerTool:
    def setup_method(self): self.tool = FallbackExplainerTool()
 
    def test_can_handle_always_true(self):
        for s in ["10 / 0", "weather", "gibberish", "", "base64 ???"]:
            assert self.tool.can_handle(s)
 
    def test_no_keywords(self):
        assert self.tool.keywords == []
 
    def test_div_by_zero_explanation(self):
        self.tool.prepare("Cannot divide by zero.")
        r = self.tool.execute("10 / 0")
        assert r.error is None and "zero" in r.output.lower() and "💡" in r.output
 
    def test_no_city_explanation(self):
        self.tool.prepare("No city name found in your request.")
        r = self.tool.execute("weather")
        assert r.error is None and "city" in r.output.lower()
 
    def test_generic_fallback(self):
        self.tool.prepare("Some unexpected error.")
        r = self.tool.execute("do something weird")
        assert r.error is None and "⚠" in r.output
 
    def test_steps_populated(self):
        self.tool.prepare("Cannot divide by zero.")
        assert len(self.tool.execute("10 / 0").steps) >= 3
 
 
# ===========================================================================
# AgentController — routing
# ===========================================================================
class TestAgentControllerRouting:
    def setup_method(self): self.agent = AgentController()
 
    def test_routes_to_calculator(self):
        r = self.agent.run("3 + 5")
        assert "CalculatorTool" in r.tools_used and r.output == "8"
 
    def test_routes_to_weather(self):
        r = self.agent.run("weather in London")
        assert "WeatherMockTool" in r.tools_used and r.error is None
 
    def test_routes_to_text(self):
        r = self.agent.run("uppercase 'hello world'")
        assert "TextProcessorTool" in r.tools_used and r.output == "HELLO WORLD"
 
    def test_routes_to_base64(self):
        r = self.agent.run("base64 encode 'hello'")
        assert "Base64Tool" in r.tools_used and r.error is None
        assert r.output == "aGVsbG8="
 
    def test_steps_numbered(self):
        r = self.agent.run("3 + 5")
        for s in r.steps:
            assert s.startswith("Step "), f"Not numbered: {s}"
 
    def test_timestamp_present(self):
        r = self.agent.run("2 * 3")
        assert r.timestamp and "T" in r.timestamp
 
    def test_unknown_task_error(self):
        r = self.agent.run("zzz gibberish xyz")
        assert r.error is not None
 
    def test_five_tools_listed(self):
        names = {t["name"] for t in self.agent.list_tools()}
        assert names == {
            "CalculatorTool", "WeatherMockTool",
            "Base64Tool", "TextProcessorTool", "FallbackExplainerTool",
        }
 
    def test_fallback_not_in_normal_run(self):
        r = self.agent.run("uppercase 'test'")
        assert "FallbackExplainerTool" not in r.tools_used
 
 
# ===========================================================================
# AgentController — fallback scenarios
# ===========================================================================
class TestAgentControllerFallback:
    def setup_method(self): self.agent = AgentController()
 
    def test_div_by_zero_activates_fallback(self):
        r = self.agent.run("10 / 0")
        assert "CalculatorTool" in r.tools_used
        assert "FallbackExplainerTool" in r.tools_used
        assert r.error is None
        assert "zero" in r.output.lower()
 
    def test_div_by_zero_has_suggestions(self):
        assert "💡" in self.agent.run("10 / 0").output
 
    def test_div_by_zero_trace_shows_chain(self):
        joined = " ".join(self.agent.run("10 / 0").steps).lower()
        assert "error" in joined and "fallback" in joined
 
    def test_no_city_activates_fallback(self):
        r = self.agent.run("weather")
        assert "WeatherMockTool" in r.tools_used
        assert "FallbackExplainerTool" in r.tools_used
        assert r.error is None and "city" in r.output.lower()
 
    def test_natural_language_div_zero(self):
        r = self.agent.run("100 divided by 0")
        assert "FallbackExplainerTool" in r.tools_used and r.error is None
 
    def test_fallback_response_no_error(self):
        assert self.agent.run("10 / 0").error is None
 
    def test_fallback_output_is_string(self):
        r = self.agent.run("10 / 0")
        assert isinstance(r.output, str) and len(r.output) > 10
 
 
# ===========================================================================
# MultiStepOrchestrator — detection
# ===========================================================================
class TestOrchestratorDetection:
    def setup_method(self): self.orch = MultiStepOrchestrator()
 
    def test_detects_then(self):
        assert self.orch.is_multistep("encode 'hello' then count the characters")
 
    def test_detects_and_then(self):
        assert self.orch.is_multistep("calculate 6*7 and then reverse the result")
 
    def test_detects_followed_by(self):
        assert self.orch.is_multistep("uppercase 'foo' followed by reverse the result")
 
    def test_detects_comma_then(self):
        assert self.orch.is_multistep("weather in Tokyo, then uppercase the condition")
 
    def test_single_task_not_multistep(self):
        assert not self.orch.is_multistep("base64 encode 'hello world'")
        assert not self.orch.is_multistep("3 + 5")
        assert not self.orch.is_multistep("weather in London")
 
    def test_splits_correctly(self):
        parts = self.orch._split("encode 'hi' then reverse the result")
        assert len(parts) == 2
        assert parts[0].strip() == "encode 'hi'"
        assert "reverse" in parts[1]
 
    def test_splits_three_parts(self):
        parts = self.orch._split("encode 'hi' then reverse the result then count the characters")
        assert len(parts) == 3
 
 
# ===========================================================================
# MultiStepOrchestrator — output injection
# ===========================================================================
class TestOrchestratorInjection:
    def setup_method(self): self.orch = MultiStepOrchestrator()
 
    def test_injects_the_result(self):
        injected = self.orch._inject_output("reverse the result", "hello")
        assert '"hello"' in injected
 
    def test_injects_it(self):
        injected = self.orch._inject_output("uppercase it", "world")
        assert '"world"' in injected
 
    def test_no_injection_when_quoted(self):
        # Already has a quoted target — should leave it alone
        injected = self.orch._inject_output("reverse 'foo'", "should_not_appear")
        assert "should_not_appear" not in injected
 
    def test_no_injection_without_ref(self):
        # No reference to previous result — leave unchanged
        injected = self.orch._inject_output("weather in Paris", "hello")
        assert injected == "weather in Paris"
 
 
# ===========================================================================
# MultiStepOrchestrator — end-to-end via AgentController
# ===========================================================================
class TestMultiStepEndToEnd:
    def setup_method(self): self.agent = AgentController()
 
    def test_encode_then_decode(self):
        """
        Scenario: encode 'hello' then decode the result
        Stage 1: Base64Tool encodes 'hello' → 'aGVsbG8='
        Stage 2: Base64Tool decodes 'aGVsbG8=' → 'hello'
        Final output should be 'hello'
        """
        r = self.agent.run("base64 encode 'hello' then decode the result")
        assert r.sub_results is not None
        assert len(r.sub_results) == 2
        assert r.error is None
        assert r.output == "hello"
 
    def test_encode_then_count_characters(self):
        """
        Scenario: encode 'hello' then count the characters of the result
        Stage 1: Base64Tool  → 'aGVsbG8='  (8 chars)
        Stage 2: TextProcessor → '8 characters'
        """
        r = self.agent.run("base64 encode 'hello' then count the characters of the result")
        assert r.sub_results is not None and r.error is None
        assert "8" in str(r.output)
 
    def test_calculate_then_reverse(self):
        """
        Scenario: calculate 6 * 7 then reverse the result
        Stage 1: CalculatorTool → '42'
        Stage 2: TextProcessor  → '24'
        """
        r = self.agent.run("calculate 6 * 7 then reverse the result")
        assert r.sub_results is not None and r.error is None
        assert r.output == "24"
 
    def test_uppercase_then_reverse(self):
        """
        Scenario: uppercase 'hello' then reverse the result
        Stage 1: TextProcessor → 'HELLO'
        Stage 2: TextProcessor → 'OLLEH'
        """
        r = self.agent.run("uppercase 'hello' then reverse the result")
        assert r.sub_results is not None and r.error is None
        assert r.output == "OLLEH"
 
    def test_three_stage_chain(self):
        """
        Scenario: encode 'hi' then reverse the result then count the characters
        Stage 1: Base64Tool   → 'aGk='
        Stage 2: TextProcessor → '=kGa'  (reversed)
        Stage 3: TextProcessor → '4 characters'
        """
        r = self.agent.run(
            "base64 encode 'hi' then reverse the result then count the characters"
        )
        assert r.sub_results is not None
        assert len(r.sub_results) == 3
        assert r.error is None
 
    def test_tools_used_contains_both(self):
        r = self.agent.run("base64 encode 'hello' then count the characters of the result")
        assert "Base64Tool" in r.tools_used
        assert "TextProcessorTool" in r.tools_used
 
    def test_steps_contain_stage_labels(self):
        r = self.agent.run("3 + 5 then reverse the result")
        assert any("[STAGE 1]" in s for s in r.steps)
        assert any("[STAGE 2]" in s for s in r.steps)
 
    def test_sub_results_structure(self):
        r = self.agent.run("uppercase 'hello' then reverse the result")
        assert r.sub_results is not None
        for sr in r.sub_results:
            assert "stage"  in sr
            assert "task"   in sr
            assert "tool"   in sr
            assert "output" in sr
 
    def test_single_step_not_treated_as_multistep(self):
        r = self.agent.run("base64 encode 'hello world'")
        assert r.sub_results is None   # no orchestration
        assert r.output == "aGVsbG8gd29ybGQ="
 