import sys
from collections import defaultdict

# Import scanners
try:
    from src.scanner.trufflehog import run_trufflehog_scanner
    from src.scanner.gitleaks import run_gitleaks_scanner
    from src.scanner.regex import run_custom_regex_scanner
except ImportError as e:
    sys.exit(1)



# Internal helper function: extract context for findings
def _extract_missing_contexts(findings_to_process: dict, window: int = 3):

    tasks_by_file = defaultdict(list)
    for key in findings_to_process.keys():
        file_path, _, line = key
        tasks_by_file[file_path].append({"key": key, "line": line})

    for file_path, tasks in tasks_by_file.items():
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                all_lines = f.read().splitlines()

            for task in tasks:
                i = task["line"] - 1
                start = max(0, i - window)
                end = min(len(all_lines), i + window + 1)
                context = "\n".join(all_lines[start:end])
                findings_to_process[task["key"]]["context"] = context

        except Exception as e:
            for task in tasks:
                findings_to_process[task["key"]]["context"] = f"Context extraction failed: {e}"


# Main function: generate aggregated candidates
def generate_candidates(target_filepath_abs: str, context_window: int = 3) -> list:

    final_findings = {}

    # 1. Custom Regex scanner (already contains context)
    cr_results = run_custom_regex_scanner(target_filepath_abs, window=context_window)
    if cr_results:
        for item in cr_results:
            key = (item['file'], item['value'], item['line'])
            if key not in final_findings:
                final_findings[key] = {"context": item['context']}

    # 2. TruffleHog scanner (no context)
    th_results = run_trufflehog_scanner(target_filepath_abs)
    th_new_findings = {}
    if th_results:
        for item in th_results:
            key = (item['file'], item['value'], item['line'])
            if key not in final_findings:
                th_new_findings[key] = {"context": None}


    # 3. Gitleaks scanner (no context)
    gl_results = run_gitleaks_scanner(target_filepath_abs)
    gl_new_findings = {}
    if gl_results:
        for item in gl_results:
            key = (item['file'], item['value'], item['line'])
            if key not in final_findings and key not in th_new_findings:
                gl_new_findings[key] = {"context": None}


    # 4. Extract missing context
    findings_to_process = {**th_new_findings, **gl_new_findings}
    if findings_to_process:
        _extract_missing_contexts(findings_to_process, window=context_window)
    else:
        print("\n====== No missing context to extract ======")

    # 5. Merge all results
    final_findings.update(th_new_findings)
    final_findings.update(gl_new_findings)

    final_list_output = []
    for (file, value, line), data in final_findings.items():
        final_list_output.append({
            "file": file,
            "value": value,
            "line": line,
            "context": data.get("context", "Context extraction failed.")
        })


    return final_list_output
