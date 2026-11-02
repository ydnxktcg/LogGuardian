import os
import subprocess
import json
import sys

# Resolve project paths and ensure TruffleHog executable exists
try:
    PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    TOOLS_DIR = os.path.join(PROJECT_ROOT, 'tool')
    TRUFFLEHOG_EXE = os.path.join(TOOLS_DIR, 'trufflehog.exe')
    if not os.path.exists(TRUFFLEHOG_EXE):
        raise FileNotFoundError
except FileNotFoundError:
    sys.exit(1)


# run_trufflehog_scanner
# Run TruffleHog on a file and return parsed {file, value, line}.
def run_trufflehog_scanner(filepath: str) -> list[dict]:

    if not os.path.exists(filepath):
        return []

    command = ["trufflehog", "filesystem", filepath, "--json", "--no-update"]
    parsed_results = []

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            encoding='utf-8'
        )

        raw_output = result.stdout.strip()
        if raw_output:
            for line in raw_output.splitlines():
                try:
                    item = json.loads(line)

                    file = item.get("SourceMetadata", {}) \
                               .get("Data", {}) \
                               .get("Filesystem", {}) \
                               .get("file", filepath)

                    value = item.get("Raw", "")
                    line_num = item.get("SourceMetadata", {}) \
                                   .get("Data", {}) \
                                   .get("Filesystem", {}) \
                                   .get("line", -1)

                    if value and line_num != -1:
                        parsed_results.append({
                            "file": os.path.abspath(file),
                            "value": value,
                            "line": line_num
                        })
                except json.JSONDecodeError:
                    pass

        return parsed_results

    except FileNotFoundError:
        return []         # trufflehog not found
    except subprocess.CalledProcessError:
        return []         # scan failed
    except Exception:
        return []         # unexpected error
