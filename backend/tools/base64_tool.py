import re
import base64
import binascii
from .base import BaseTool, ToolResult
 
 
# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
 
def _is_valid_base64(s: str) -> bool:
    """Return True if s is a well-formed standard base64 string."""
    s = s.strip()
    # Standard base64 alphabet: A-Z a-z 0-9 + / =
    if not re.match(r'^[A-Za-z0-9+/=]*$', s):
        return False
    padded = s + "=" * (-len(s) % 4)
    try:
        base64.b64decode(padded, validate=True)
        return True
    except Exception:
        return False
 
 
def _is_valid_urlsafe_base64(s: str) -> bool:
    """Return True if s is a well-formed URL-safe base64 string."""
    s = s.strip()
    # URL-safe base64 alphabet: A-Z a-z 0-9 - _ =
    if not re.match(r'^[A-Za-z0-9\-_=]*$', s):
        return False
    padded = s + "=" * (-len(s) % 4)
    try:
        base64.urlsafe_b64decode(padded)
        return True
    except Exception:
        return False
 
 
def _auto_detect_operation(text: str) -> str:
    """
    Guess the intended operation from the text.
    Returns one of: 'encode', 'decode', 'url_encode', 'url_decode',
                    'validate', 'info', 'auto'
 
    Order matters: url_decode must be checked before url_encode because
    both share the 'url-safe' / 'urlsafe' trigger.  The word 'decode'
    is the tiebreaker — if it is present alongside 'url-safe', the user
    clearly wants url_decode, not url_encode.
    """
    lower = text.lower()
 
    is_url_safe = bool(re.search(r'\burl[\s-]?safe\b|\burlsafe\b', lower))
 
    if is_url_safe:
        # Check decode first — "url-safe decode" must not match url_encode
        if re.search(r'\bdecode\b', lower):
            return 'url_decode'
        return 'url_encode'
 
    if re.search(r'\bdecode\b|\bfrom\s+base64\b|\bbase64\s+to\b', lower):
        return 'decode'
    if re.search(r'\bencode\b|\bto\s+base64\b|\bbase64\s+of\b|\bconvert.*base64\b', lower):
        return 'encode'
    if re.search(r'\bvalidate\b|\bcheck\b|\bverify\b|\bis\s+(valid|valid)\b', lower):
        return 'validate'
    if re.search(r'\binfo\b|\bdetails\b|\banalyse\b|\banalyze\b|\binspect\b', lower):
        return 'info'
    return 'auto'
 
 
def _extract_target(text: str) -> str:
    """
    Pull the subject string out of a natural language instruction.
    Tries quoted strings first, then strips common command words.
    """
    # Quoted strings (single or double quotes)
    for pattern in [r'"([^"]*)"', r"'([^']*)'"]:  # * allows empty strings
        m = re.search(pattern, text)
        if m:
            return m.group(1)
 
    # After a colon
    if ":" in text:
        return text.split(":", 1)[1].strip()
 
    # Strip command vocabulary
    strip_terms = [
        r'\bbase64\b', r'\bencode\b', r'\bdecode\b', r'\bconvert\b',
        r'\burl.safe\b', r'\burlsafe\b', r'\burl\b',
        r'\bvalidate\b', r'\bcheck\b', r'\bverify\b',
        r'\binfo\b', r'\bdetails\b', r'\banalyze\b', r'\binspect\b',
        r'\bof\b', r'\bthe\b', r'\bstring\b', r'\btext\b',
        r'\bfrom\b', r'\bto\b', r'\bplease\b', r'\bme\b',
    ]
    result = text
    for term in strip_terms:
        result = re.sub(term, '', result, flags=re.IGNORECASE)
    result = re.sub(r'\s+', ' ', result).strip(" ,?!.")
    return result  # may be "" for empty quoted input — that is correct
 
 
# ---------------------------------------------------------------------------
# Tool
# ---------------------------------------------------------------------------
 
class Base64Tool(BaseTool):
    """
    Handles Base64 encoding and decoding operations.
 
    Supported operations
    --------------------
    encode   – standard Base64 encode a plaintext string
    decode   – standard Base64 decode back to plaintext
    url_encode  – URL-safe Base64 encode (replaces +/ with -_)
    url_decode  – URL-safe Base64 decode
    info     – inspect an encoded string (length, padding, decoded preview)
    auto     – detect from context: if input looks like Base64, decode it;
               otherwise encode it
 
    Examples
    --------
    "base64 encode 'hello world'"
    "decode 'aGVsbG8gd29ybGQ='"
    "url-safe base64 encode 'user@example.com'"
    "base64 info 'SGVsbG8gV29ybGQ='"
    "base64 'auto detect me'"           → auto mode
    """
 
    @property
    def name(self) -> str:
        return "Base64Tool"
 
    @property
    def description(self) -> str:
        return (
            "Encode/decode Base64: standard, URL-safe, validate, inspect, "
            "and auto-detect mode"
        )
 
    @property
    def keywords(self) -> list[str]:
        return [
            "base64", "b64",
            "encode", "decode",
            "encoding", "decoding",
            "urlsafe", "url-safe",
        ]
 
    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------
 
    def execute(self, input_text: str) -> ToolResult:
        steps = [f'Received input: "{input_text}"']
        steps.append("Selected tool: Base64Tool")
 
        operation = _auto_detect_operation(input_text)
        steps.append(f"Detected operation: {operation}")
 
        target = _extract_target(input_text)
        steps.append(f'Extracted target: "{target}"')
 
        if operation == "encode":
            return self._encode(target, steps, url_safe=False)
        elif operation == "decode":
            return self._decode(target, steps, url_safe=False)
        elif operation == "url_encode":
            return self._encode(target, steps, url_safe=True)
        elif operation == "url_decode":
            return self._decode(target, steps, url_safe=True)
        elif operation == "info":
            return self._info(target, steps)
        else:  # auto
            return self._auto(target, steps)
 
    # ------------------------------------------------------------------
    # Operations
    # ------------------------------------------------------------------
 
    def _encode(self, target: str, steps: list[str], url_safe: bool) -> ToolResult:
        label = "URL-safe Base64" if url_safe else "standard Base64"
        steps.append(f"Operation: {label} encode")
        try:
            raw = target.encode("utf-8")
            if url_safe:
                encoded = base64.urlsafe_b64encode(raw).decode("ascii")
            else:
                encoded = base64.b64encode(raw).decode("ascii")
            steps.append(
                f"Encoded {len(raw)} bytes → {len(encoded)} Base64 characters"
            )
            steps.append(f"Result: {encoded}")
            steps.append("Returning result to user")
            return ToolResult(output=encoded, steps=steps)
        except Exception as e:
            steps.append(f"Encoding error: {e}")
            return ToolResult(
                output=None, steps=steps, error=f"Could not encode: {e}"
            )
 
    def _decode(self, target: str, steps: list[str], url_safe: bool) -> ToolResult:
        label = "URL-safe Base64" if url_safe else "standard Base64"
        steps.append(f"Operation: {label} decode")
        target = target.strip()
        # Add padding if missing
        padded = target + "=" * (-len(target) % 4)
        try:
            if url_safe:
                raw = base64.urlsafe_b64decode(padded)
            else:
                raw = base64.b64decode(padded, validate=True)
            decoded = raw.decode("utf-8")
            steps.append(
                f"Decoded {len(target)} Base64 characters → {len(raw)} bytes"
            )
            steps.append(f"Result: {decoded}")
            steps.append("Returning result to user")
            return ToolResult(output=decoded, steps=steps)
        except (binascii.Error, UnicodeDecodeError) as e:
            steps.append(f"Decode error: {e}")
            return ToolResult(
                output=None,
                steps=steps,
                error=(
                    f'Could not decode "{target}" as {label}. '
                    "Make sure the input is a valid Base64 string."
                ),
            )
 
    def _validate(self, target: str, steps: list[str]) -> ToolResult:
        steps.append("Operation: validate Base64 string")
        is_std = _is_valid_base64(target)
        is_url = _is_valid_urlsafe_base64(target)
 
        if is_std and is_url:
            verdict = "✓ Valid — compatible with both standard and URL-safe Base64"
        elif is_std:
            verdict = "✓ Valid standard Base64 (not URL-safe — contains + or /)"
        elif is_url:
            verdict = "✓ Valid URL-safe Base64 (uses - and _ instead of + and /)"
        else:
            verdict = "✗ Not valid Base64 — contains illegal characters or bad padding"
 
        steps.append(f"Validation result: {verdict}")
        steps.append("Returning result to user")
        return ToolResult(output=verdict, steps=steps)
 
    def _info(self, target: str, steps: list[str]) -> ToolResult:
        steps.append("Operation: inspect Base64 string")
        target = target.strip()
        padded = target + "=" * (-len(target) % 4)
 
        is_valid = _is_valid_base64(target)
        if not is_valid:
            steps.append("String is not valid Base64 — cannot inspect")
            return ToolResult(
                output=None,
                steps=steps,
                error=f'"{target}" is not a valid Base64 string.',
            )
 
        raw = base64.b64decode(padded)
        try:
            preview = raw.decode("utf-8")
            encoding_note = "UTF-8 text"
        except UnicodeDecodeError:
            preview = repr(raw[:16])
            encoding_note = "binary data"
 
        padding = len(padded) - len(target)
        info = (
            f"Encoded length : {len(target)} characters\n"
            f"Padding        : {'=' * padding if padding else 'none (already padded)'}\n"
            f"Decoded bytes  : {len(raw)}\n"
            f"Content type   : {encoding_note}\n"
            f"Decoded value  : {preview}\n"
            f"URL-safe       : {'yes' if _is_valid_urlsafe_base64(target) and '+' not in target and '/' not in target else 'no'}"
        )
        steps.append("Extracted metadata from encoded string")
        steps.append("Returning result to user")
        return ToolResult(output=info, steps=steps)
 
    def _auto(self, target: str, steps: list[str]) -> ToolResult:
        """
        Heuristic auto-mode: if the target looks like Base64, decode it;
        otherwise encode it.
        """
        steps.append("Operation: auto-detect (encode or decode?)")
        target_stripped = target.strip()
 
        if _is_valid_base64(target_stripped) and len(target_stripped) >= 4:
            # Looks like Base64 — try decoding
            steps.append("Target appears to be Base64 — attempting decode")
            result = self._decode(target_stripped, steps, url_safe=False)
            if not result.error:
                return result
            steps.append("Decode failed — falling back to encode mode")
 
        # Treat as plaintext to encode
        steps.append("Target is plaintext — encoding to Base64")
        return self._encode(target_stripped, steps, url_safe=False)