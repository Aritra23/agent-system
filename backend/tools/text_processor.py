import re
from .base import BaseTool, ToolResult
 
 
class TextProcessorTool(BaseTool):
    """Handles text transformation operations."""
 
    @property
    def name(self) -> str:
        return "TextProcessorTool"
 
    @property
    def description(self) -> str:
        return "Processes text: uppercase, lowercase, word count, reverse, title case, character count"
 
    @property
    def keywords(self) -> list[str]:
        return [
            "uppercase", "upper case", "upper",
            "lowercase", "lower case", "lower",
            "word count", "words",
            "reverse",
            "title case", "capitalize",
            "character count", "char count", "length",
            "characters", "count",          # broader — enables chained tasks like "count the characters"
            "palindrome",
            "trim", "strip",
            "snake_case", "camelcase", "camel case",
        ]
 
    def execute(self, input_text: str) -> ToolResult:
        steps = [f'Received input: "{input_text}"']
        steps.append("Selected tool: TextProcessorTool")
 
        lowered = input_text.lower()
        # Extract the quoted or trailing string to operate on, if any
        target = self._extract_target(input_text)
        steps.append(f'Extracted target text: "{target}"')
 
        result = None
 
        if "uppercase" in lowered or "upper" in lowered:
            result = target.upper()
            steps.append(f"Operation: convert to UPPERCASE → {result}")
 
        elif "lowercase" in lowered or "lower" in lowered:
            result = target.lower()
            steps.append(f"Operation: convert to lowercase → {result}")
 
        elif "title case" in lowered or "capitalize" in lowered:
            result = target.title()
            steps.append(f"Operation: convert to Title Case → {result}")
 
        elif "reverse" in lowered:
            result = target[::-1]
            steps.append(f"Operation: reverse string → {result}")
 
        elif "word count" in lowered or ("count" in lowered and "word" in lowered):
            words = target.split()
            result = f"{len(words)} words"
            steps.append(f"Operation: count words → {result}")
 
        elif (
            "character count" in lowered
            or "char count" in lowered
            or "length" in lowered
            or ("count" in lowered and "char" in lowered)   # "count the characters"
            or ("count" in lowered and "character" in lowered)
        ):
            result = f"{len(target)} characters"
            steps.append(f"Operation: count characters → {result}")
 
        elif "palindrome" in lowered:
            cleaned = re.sub(r'[^a-z0-9]', '', target.lower())
            is_palindrome = cleaned == cleaned[::-1]
            result = f'"{target}" is {"a palindrome ✓" if is_palindrome else "not a palindrome ✗"}'
            steps.append(f"Operation: palindrome check → {result}")
 
        elif "snake_case" in lowered or "snake case" in lowered:
            result = re.sub(r'\s+', '_', target.strip().lower())
            steps.append(f"Operation: convert to snake_case → {result}")
 
        elif "camelcase" in lowered or "camel case" in lowered:
            words_list = target.split()
            result = words_list[0].lower() + ''.join(w.title() for w in words_list[1:]) if words_list else ""
            steps.append(f"Operation: convert to camelCase → {result}")
 
        elif "trim" in lowered or "strip" in lowered:
            result = target.strip()
            steps.append(f"Operation: trim whitespace → \"{result}\"")
 
        else:
            # Default: return stats
            words = len(target.split())
            chars = len(target)
            result = f"Text stats — Words: {words}, Characters: {chars}, Characters (no spaces): {len(target.replace(' ', ''))}"
            steps.append(f"Operation: default text stats → {result}")
 
        steps.append(f"Returning result to user")
        return ToolResult(output=result, steps=steps)
 
    def _extract_target(self, input_text: str) -> str:
        """
        Try to extract the subject text from the user request.
        Handles patterns like:
          - "uppercase 'hello world'"
          - 'convert "foo bar" to lowercase'
          - "reverse: some text"
          - "word count of this sentence please"
        Falls back to stripping the command verbs.
        """
        # Quoted string extraction
        for pattern in [r'"([^"]+)"', r"'([^']+)'"]:
            m = re.search(pattern, input_text)
            if m:
                return m.group(1)
 
        # After a colon
        if ":" in input_text:
            return input_text.split(":", 1)[1].strip()
 
        # Strip common leading command words and return the rest
        strip_words = [
            "uppercase", "lowercase", "upper case", "lower case",
            "reverse", "capitalize", "title case",
            "word count of", "word count", "character count of", "character count",
            "char count of", "char count", "length of",
            "palindrome check", "is a palindrome", "check if",
            "convert to", "convert", "make", "please", "the", "a",
            "trim", "strip", "to",
        ]
        result = input_text
        for word in strip_words:
            result = re.sub(rf'\b{re.escape(word)}\b', '', result, flags=re.IGNORECASE)
        result = result.strip(" ,?!.")
        return result if result else input_text