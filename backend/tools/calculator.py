import re
import ast
import math
import operator
from .base import BaseTool, ToolResult


class CalculatorTool(BaseTool):
    """Handles arithmetic and mathematical expressions."""

    OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.Mod: operator.mod,
        ast.FloorDiv: operator.floordiv,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    WORD_OPS = {
        " plus ": " + ",
        " minus ": " - ",
        " times ": " * ",
        " multiplied by ": " * ",
        " divided by ": " / ",
        " over ": " / ",
        " to the power of ": " ** ",
        " squared": " ** 2",
        " cubed": " ** 3",
        " mod ": " % ",
        " modulo ": " % ",
    }

    @property
    def name(self) -> str:
        return "CalculatorTool"

    @property
    def description(self) -> str:
        return "Evaluates arithmetic expressions: +, -, *, /, **, %, sqrt, and more"

    @property
    def keywords(self) -> list[str]:
        return [
            "calculate", "compute", "eval",
            "plus", "minus", "times", "divided by", "multiplied",
            "sum", "product", "difference", "quotient",
            "square root", "sqrt", "power", "squared", "cubed",
            "percent", "%", "modulo", "mod",
            "what is", "how much is", "solve",
            "+", "-", "*", "/",
        ]

    def execute(self, input_text: str) -> ToolResult:
        steps = [f'Received input: "{input_text}"']
        steps.append("Selected tool: CalculatorTool")

        # Handle sqrt specially
        sqrt_match = re.search(r'sqrt\s*\(?\s*(\d+(?:\.\d+)?)\s*\)?', input_text, re.IGNORECASE)
        square_root_match = re.search(r'square\s*root\s*of\s*(\d+(?:\.\d+)?)', input_text, re.IGNORECASE)

        if sqrt_match or square_root_match:
            m = sqrt_match or square_root_match
            val = float(m.group(1))
            result = math.sqrt(val)
            steps.append(f"Identified operation: square root of {val}")
            steps.append(f"Computed: √{val} = {self._format(result)}")
            steps.append("Returning result to user")
            return ToolResult(output=self._format(result), steps=steps)

        # Extract numeric expression
        expr = self._extract_expression(input_text)
        steps.append(f"Extracted expression: {expr}")

        try:
            tree = ast.parse(expr, mode='eval')
            result = self._eval_node(tree.body)
            steps.append(f"Parsed AST successfully")
            steps.append(f"Evaluated: {expr} = {self._format(result)}")
            steps.append("Returning result to user")
            return ToolResult(output=self._format(result), steps=steps)
        except ZeroDivisionError:
            steps.append("Error: division by zero detected")
            return ToolResult(output=None, steps=steps, error="Cannot divide by zero.")
        except Exception as e:
            steps.append(f"Error evaluating expression: {e}")
            return ToolResult(output=None, steps=steps, error=f"Could not parse expression: '{expr}'. Try something like '3 + 5' or 'sqrt(16)'.")

    def _extract_expression(self, text: str) -> str:
        """Convert natural language math to a parseable expression."""
        expr = text.lower()

        # Replace word operators
        for word, symbol in self.WORD_OPS.items():
            expr = expr.replace(word, symbol)

        # Strip non-math characters but keep operators and digits
        expr = re.sub(r'[^0-9+\-*/().\s%^]', '', expr)

        # Replace ^ with ** for power
        expr = expr.replace('^', '**')

        # Remove multiple spaces
        expr = re.sub(r'\s+', '', expr)
        return expr.strip()

    def _eval_node(self, node):
        """Safely evaluate an AST node."""
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value
            raise ValueError(f"Unsupported constant: {node.value}")
        elif isinstance(node, ast.BinOp):
            op_func = self.OPERATORS.get(type(node.op))
            if op_func is None:
                raise ValueError(f"Unsupported operator: {type(node.op).__name__}")
            left = self._eval_node(node.left)
            right = self._eval_node(node.right)
            return op_func(left, right)
        elif isinstance(node, ast.UnaryOp):
            op_func = self.OPERATORS.get(type(node.op))
            if op_func is None:
                raise ValueError(f"Unsupported unary operator")
            return op_func(self._eval_node(node.operand))
        else:
            raise ValueError(f"Unsupported node type: {type(node).__name__}")

    def _format(self, value: float) -> str:
        """Format result: show int if whole number, else up to 6 decimal places."""
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        return f"{value:.6g}"
