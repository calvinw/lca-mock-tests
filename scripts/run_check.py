"""
Run an LCA against an imported mock case study and check it against
expected.json in the same case study folder.

Usage:
    python scripts/run_check.py <bw_dir> <project_name> <db_name> \\
        <method_name> <impact_category> <reference_product_name> \\
        <expected_json_path>
"""
import os
import sys
import json

def run_and_check(bw_dir, project_name, db_name, method_name, impact_category,
                   product_name, expected_path):
    os.environ["BRIGHTWAY2_DIR"] = bw_dir
    from lca_core import LCAEngine

    expected = json.load(open(expected_path))
    expected_scores = expected.get("impact_scores", {impact_category: expected["score"]})
    ok = True
    engine = LCAEngine()
    for category, expected_score in expected_scores.items():
        result = engine.calculate_imported_activity(
            db_name,
            method_name,
            category,
            project=project_name,
            product_name=product_name,
        )
        actual = result["score"]
        matches = abs(actual - expected_score) < 1e-6
        ok = ok and matches
        print(
            f"{category}: {actual}  Expected: {expected_score}  "
            f"{'OK' if matches else 'MISMATCH'}"
        )
    return ok


if __name__ == "__main__":
    ok = run_and_check(*sys.argv[1:])
    sys.exit(0 if ok else 1)
