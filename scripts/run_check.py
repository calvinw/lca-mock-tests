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
    import bw2data as bd
    bd.projects.set_current(project_name)
    import bw2calc as bc

    db = bd.Database(db_name)
    product = next(a for a in db if a["name"] == product_name and a.get("type") == "product")

    expected = json.load(open(expected_path))
    expected_scores = expected.get("impact_scores", {impact_category: expected["score"]})
    ok = True
    for category, expected_score in expected_scores.items():
        method = (method_name, category)
        lca = bc.LCA(demand={product: 1}, method=method)
        lca.lci()
        lca.lcia()
        matches = abs(lca.score - expected_score) < 1e-6
        ok = ok and matches
        print(
            f"{category}: {lca.score}  Expected: {expected_score}  "
            f"{'OK' if matches else 'MISMATCH'}"
        )
    return ok


if __name__ == "__main__":
    ok = run_and_check(*sys.argv[1:])
    sys.exit(0 if ok else 1)
