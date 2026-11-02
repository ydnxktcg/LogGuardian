import os
import subprocess
import json
import sys

# ------------------------------------------------------------
# Locate gitleaks executable inside your project structure.
# This block ensures:
#   1. PROJECT_ROOT is correctly detected
#   2. The gitleaks binary exists before running any scan
# ------------------------------------------------------------
try:
    PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    TOOLS_DIR = os.path.join(PROJECT_ROOT, 'tool')
    GITLEAKS_EXE = os.path.join(TOOLS_DIR, 'gitleaks.exe')

    if not os.path.exists(GITLEAKS_EXE):
        raise FileNotFoundError
except FileNotFoundError:
    # If gitleaks binary is not found, exit the program immediately
    sys.exit(1)


# Run gitleaks on a file and return secrets in a simple dict list:
# [{"file": path, "value": secret, "line": n}, ...]
def run_gitleaks_scanner(filepath: str) -> list[dict]:

    REPORT_TEMP_FILE = "gitleaks_temp_report.json"
    parsed_results = []

    # Ensure the target file exists before scanning
    if not os.path.exists(filepath):
        return []

    # ------------------------------------------------------------
    # Build gitleaks command:
    #   - detect: run detection mode
    #   - --source: target file or directory
    #   - --no-git: treat folder as raw files, not a git repo
    #   - --report-format json: output results as JSON
    #   - --report-path: where to save the JSON file
    #   - --exit-code 0: never fail even if secrets are found
    # ------------------------------------------------------------
    command = [
        GITLEAKS_EXE, "detect",
        "--source", filepath,
        "--no-git",
        "--report-format", "json",
        "--report-path", REPORT_TEMP_FILE,
        "--exit-code", "0"
    ]

    try:
        # Remove last report file (if exists)
        if os.path.exists(REPORT_TEMP_FILE):
            os.remove(REPORT_TEMP_FILE)

        # Execute gitleaks command
        subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding='utf-8'
        )

        # Ensure gitleaks actually generated a report
        if not os.path.exists(REPORT_TEMP_FILE):
            return []

        # Load gitleaks results
        with open(REPORT_TEMP_FILE, 'r', encoding='utf-8') as f:
            candidates = json.load(f)

        # ------------------------------------------------------------
        # Parse each detected secret:
        #   - File: path to file
        #   - Secret: the string classified by gitleaks
        #   - StartLine: line number in file
        #
        # Normalize into a minimal internal representation for ML model
        # ------------------------------------------------------------
        for item in candidates:
            file = item.get("File", filepath)
            value = item.get("Secret", "")
            line_num = item.get("StartLine", -1)

            # Only keep valid secret entries
            if value and line_num != -1:
                parsed_results.append({
                    "file": os.path.abspath(file),
                    "value": value,
                    "line": line_num
                })

        return parsed_results

    except FileNotFoundError:
        # gitleaks not found or filepath missing
        return []

    except json.JSONDecodeError:
        # gitleaks returned invalid JSON
        return []

    except Exception:
        # any unexpected error during scanning
        return []

    finally:
        # Clean up temporary report file
        if os.path.exists(REPORT_TEMP_FILE):
            try:
                os.remove(REPORT_TEMP_FILE)
            except Exception:
                pass
