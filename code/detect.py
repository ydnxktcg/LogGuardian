import os
import json
import sys
import argparse
from tqdm import tqdm

# Import function modules from src/
try:
    # Import the aggregator function
    from src.aggregator.aggregator import generate_candidates
    # Import the predictor class
    from src.inference.predictor import MLPredictor
except ImportError as e:
    print(f"❌ Fatal Error: Cannot import src modules: {e}", file=sys.stderr)
    print("   Make sure the folder structure is correct and all __init__.py files exist.", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Log Secret Detection Tool (supports file or directory)")
    parser.add_argument(
        "-p", "--path",
        required=True,
        type=str,
        help="Path to file or directory to scan"
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        type=str,
        help="Path to save final secrets as JSON (optional)"
    )
    args = parser.parse_args()

    # 1. Load ML model
    print("=" * 50)
    print("Loading ML Prediction Model")
    try:
        predictor = MLPredictor()
        print("✅ ML model loaded successfully!")
        print("=" * 50)
    except Exception as e:
        print(f"❌ Failed to load ML model: {e}", file=sys.stderr)
        sys.exit(1)

    # 2. Build file list to scan
    try:
        target_path = os.path.abspath(args.path)
        if not os.path.exists(target_path):
            raise FileNotFoundError(f"Path does not exist: {target_path}")

        files_to_scan = []
        if os.path.isfile(target_path):
            files_to_scan.append(target_path)

        elif os.path.isdir(target_path):
            for root, dirnames, filenames in os.walk(target_path, topdown=True):
                # No directory filtering
                for filename in filenames:
                    # No file extension filtering
                    files_to_scan.append(os.path.join(root, filename))

            print(f"  > Found {len(files_to_scan)} files.")

    except Exception as e:
        print(f"Error: Failed to parse path: {e}", file=sys.stderr)
        sys.exit(1)

    # 3. Aggregate candidates
    all_candidates = []

    for file_path in tqdm(files_to_scan, desc="Scanning Files", unit="file"):
        candidates_from_file = generate_candidates(
            file_path,
            context_window=predictor.CONTEXT_WINDOW
        )
        if candidates_from_file:
            all_candidates.extend(candidates_from_file)

    if not all_candidates:
        print("\nNo candidates found by aggregator. Exiting.")
        sys.exit(0)

    # 4. ML prediction
    final_secrets = []

    for item in tqdm(all_candidates, desc="ML Predicting"):
        if not item["context"] or "Context extraction failed" in item["context"]:
            continue

        prediction = predictor.predict_one(item["context"])

        if prediction == 1:
            # Remove context and keep only file, value, and line
            filtered_item = {
                "file": item["file"],
                "value": item["value"],
                "line": item.get("line", "")  # Add line if available
            }
            final_secrets.append(filtered_item)

    # 5. Save or print results
    print("=" * 50)
    print("✅ Scan Completed!")
    print(f"  Total files scanned: {len(files_to_scan)}")
    print(f"  Candidates found: {len(all_candidates)}")
    print(f"  ML confirmed secrets: {len(final_secrets)}")
    print("=" * 50)

    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(final_secrets, f, indent=2, ensure_ascii=False)
            print(f"✅ Final secrets saved to: {args.output}")
            print("=" * 50)
        except Exception as e:
            print(f"\n❌ Failed to write output JSON: {e}", file=sys.stderr)
    else:
        if final_secrets:
            print("\n✅ Confirmed Secrets (JSON):")
            print(json.dumps(final_secrets, indent=2, ensure_ascii=False))
        else:
            print("\n✅ No reportable secrets detected.")
