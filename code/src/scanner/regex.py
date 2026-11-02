import os
import re
import json
import sys
from tqdm import tqdm


# Custom regex patterns for detecting various secret types
REGEXES = [
    r'(?i)\bjwt\b[\s:=]+([A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{6,})',
    r'(?i)\b(?:bearer|authorization)\b[\s:=]+([A-Za-z0-9_-]{8,256})',
    r'(?i)\bbasic\b[\s:=]+([A-Za-z0-9+/=]{8,256})',
    r'(?i)\b(?:pwd|passwd)\b\s*[:=]\s*([^\s\'"]{4,256})',
    r"(?i)(?:curl\b[^'\n\r]*)\s(?:-u|--user)\s+(['\"]?)([^:'\"\s]+):([^'\"\s]+)\1",
    r'(?i)(?:\bMISP-session-\w+=)(?:.|[\n\r]){0,40}\b([A-Za-z0-9\-\._~%]{4,128})\b',
    r'(?i)(?:\ba=)?ice-ufrag[:=\s]*([A-Za-z0-9\-\._~%]{4,128})',
    r"(?i)(?:mnemonic|seed(?:\s+phrase)?|recovery\s+phrase)\s*[:=]?\s*['\"]?([a-z'\-]+(?:\s+[a-z'\-]+){11,100})['\"]?"
]

# Scan file with regexes → return {file, value, line, context}
def run_custom_regex_scanner(filepath: str, window: int = 3) -> list[dict]:

    # Compile regex patterns
    COMPILED_PATTERNS = []
    for p_str in REGEXES:
        try:
            COMPILED_PATTERNS.append((p_str, re.compile(p_str)))
        except re.error as e:
            print(f"Skipped invalid regex: {p_str[:40]}... ({e})", file=sys.stderr)

    if not COMPILED_PATTERNS:
        return []

    # Read file
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            all_lines = f.read().splitlines()
    except Exception:
        return []

    results = []
    abs_filepath = os.path.abspath(filepath)

    # Line-by-line scanning
    for i, line in enumerate(tqdm(all_lines, desc="Scanning (Custom Regex)", leave=False)):
        for p_str, regex_obj in COMPILED_PATTERNS:

            # Multiple matches per line supported
            for match in regex_obj.finditer(line):

                # Extract surrounding context
                start = max(0, i - window)
                end = min(len(all_lines), i + window + 1)
                context = "\n".join(all_lines[start:end])

                results.append({
                    "file": abs_filepath,
                    "value": match.group(0),
                    "line": i + 1,
                    "context": context
                })

    return results
