"""
Import a case study's mock_lca.zip into a fresh Brightway project and check
it against its own expected.json, using the reference_product/method_name/
impact_category recorded in that expected.json.

Usage:
    python scripts/check_case_study.py <case_study_dir>
    python scripts/check_case_study.py case_studies/cotton_fiber
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from import_to_brightway import import_jsonld
from run_check import run_and_check


def _load_entities(folder):
    return [json.loads(path.read_text()) for path in Path(folder).glob("*.json")]


def check_source(case_dir, expected):
    """Check hand-derived scaling and inventory against expanded JSON-LD."""
    root = Path(case_dir) / "olca_ld"
    flows = {item["@id"]: item for item in _load_entities(root / "flows")}
    processes = _load_entities(root / "processes")
    process_by_id = {item["@id"]: item for item in processes}
    scaling = expected["scaling_vector"]
    ok = True

    for process in processes:
        actual = scaling[process["name"]]
        for exchange in process.get("exchanges", []):
            provider = exchange.get("defaultProvider")
            if not exchange.get("isInput") or not provider:
                continue
            required = actual * exchange["amount"]
            supplied = scaling[process_by_id[provider["@id"]]["name"]]
            matches = abs(required - supplied) < 1e-9
            ok = ok and matches
            print(
                f"Scaling link {provider['name']} -> {process['name']}: "
                f"{supplied} supplied, {required} required  "
                f"{'OK' if matches else 'MISMATCH'}"
            )

    inventory = {}
    resource_inputs = set()
    for process in processes:
        scale = scaling[process["name"]]
        for exchange in process.get("exchanges", []):
            flow = flows[exchange["flow"]["@id"]]
            if flow["flowType"] != "ELEMENTARY_FLOW":
                continue
            name = flow["name"]
            inventory[name] = inventory.get(name, 0.0) + scale * exchange["amount"]
            if exchange.get("isInput"):
                resource_inputs.add(name)

    for name, expected_amount in expected["inventory"].items():
        actual = inventory.get(name)
        matches = actual is not None and abs(actual - expected_amount) < 1e-9
        ok = ok and matches
        direction = "resource input" if name in resource_inputs else "emission output"
        print(
            f"Inventory {name} ({direction}): {actual}  Expected: {expected_amount}  "
            f"{'OK' if matches else 'MISMATCH'}"
        )

    unexpected = set(inventory) - set(expected["inventory"])
    if unexpected:
        ok = False
        print("Unexpected elementary flows:", ", ".join(sorted(unexpected)))
    return ok

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
    source_ok = check_source(case_dir, expected)
    db_name = f"{name} background"
    project_name = f"{name}_test"
    bw_dir = os.path.join(case_dir, ".bw_project")

    import_jsonld(zip_path, db_name, project_name, bw_dir=bw_dir)

    engine_ok = run_and_check(
        bw_dir, project_name, db_name,
        expected["method_name"], expected["impact_category"],
        expected["reference_product"], expected_path,
    )
    sys.exit(0 if source_ok and engine_ok else 1)
