"""
Import a case study's mock_lca.zip into a fresh Brightway project and check
it against its own expected.json, using the reference_product/method_name/
impact_category recorded in that expected.json.

Usage:
    python scripts/check_case_study.py <case_study_dir>
    python scripts/check_case_study.py case_studies/mock_widget
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from import_to_brightway import import_jsonld
from run_check import run_and_check

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)

    case_dir = sys.argv[1]
    name = os.path.basename(os.path.normpath(case_dir))
    zip_path = os.path.join(case_dir, "mock_lca.zip")
    expected_path = os.path.join(case_dir, "expected.json")

    if not os.path.exists(zip_path):
        print(f"No mock_lca.zip at {zip_path} -- run scripts/make_release.py first.")
        sys.exit(1)

    expected = json.load(open(expected_path))
    db_name = f"{name} background"
    project_name = f"{name}_test"
    bw_dir = os.path.join(case_dir, ".bw_project")

    import_jsonld(zip_path, db_name, project_name, bw_dir=bw_dir)

    ok = run_and_check(
        bw_dir, project_name, db_name,
        expected["method_name"], expected["impact_category"],
        expected["reference_product"], expected_path,
    )
    sys.exit(0 if ok else 1)
